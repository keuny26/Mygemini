import sys
from PyQt6 import QtWidgets, uic, QtCore, QtGui 
from google import genai
from google.genai.errors import APIError
from google.genai import types
import os
from gtts import gTTS
from playsound import playsound
import uuid 
from dotenv import load_dotenv 

# =================================================================
# 🌟 데이터베이스 관련 모듈 추가
# =================================================================
import pymysql
from datetime import datetime

# =================================================================
# 1. 설정 및 초기화
# =================================================================

load_dotenv() 
UI_FILE_NAME = "Mygemini.ui"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") 

# 2. Gemini 클라이언트 초기화
if not GEMINI_API_KEY:
    print("치명적 오류: GEMINI_API_KEY가 환경 변수나 .env 파일로 설정되지 않았습니다.")
    sys.exit(1)
    
try:
    client = genai.Client(api_key=GEMINI_API_KEY)
    MODEL_NAME = "gemini-2.5-flash"
except ValueError as e:
    print(f"클라이언트 초기화 오류: API 키가 잘못되었거나 누락되었습니다. {e}")
    sys.exit(1)


# =================================================================
# 2. Gemini API 호출을 위한 워커 스레드 (QThread)
# =================================================================

class GeminiWorker(QtCore.QThread):
    response_ready = QtCore.pyqtSignal(str, str) 
    error_occurred = QtCore.pyqtSignal(str, str) 

    def __init__(self, client, model_name, chat_history, user_question):
        super().__init__()
        self.client = client
        self.model_name = model_name
        self.chat_history = chat_history 
        self.user_question = user_question
        
        self.config = types.GenerateContentConfig(
            system_instruction="You are a helpful assistant. Please answer all questions in Korean."
        )

    def run(self):
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=self.chat_history,
                config=self.config
            )
            
            gemini_response = response.text
            
            self.chat_history.append({"role": "model", "parts": [{"text": gemini_response}]})

            self.response_ready.emit(self.user_question, gemini_response)

        except APIError as e:
            self.error_occurred.emit("API 오류", f"Gemini 서버에 연결할 수 없습니다. (오류: {e})")
        except Exception as e:
            self.error_occurred.emit("예기치 않은 오류", str(e))

# =================================================================
# 🌟 2-2. TTS/Playsound 처리를 위한 워커 스레드 (QThread) - 블로킹 문제 해결
# =================================================================

class SpeechWorker(QtCore.QThread):
    """
    gTTS/playsound는 블로킹 작업이므로 별도 스레드에서 실행하여 UI 멈춤을 방지합니다.
    """
    def __init__(self, text):
        super().__init__()
        self.text = text

    def run(self):
        try:
            print("음성 생성 및 재생 시작 (SpeechWorker 스레드)...")
            filename = f"temp_speech_{uuid.uuid4().hex}.mp3"
            
            tts = gTTS(text=self.text, lang='ko')
            tts.save(filename)
            playsound(filename)
            os.remove(filename)
            print("음성 재생 완료 및 파일 삭제.")
            
        except Exception as e:
            print(f"음성 출력 오류 (gTTS/playsound) (스레드): {e}")


# =================================================================
# 3. 메인 애플리케이션 클래스
# =================================================================

class GeminiApp(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        
        try:
            uic.loadUi(UI_FILE_NAME, self)
        except FileNotFoundError:
            print(f"오류: {UI_FILE_NAME} 파일을 찾을 수 없습니다. 경로를 확인해 주세요.")
            sys.exit(1)
            
        self.setWindowTitle(f"Gemini Q&A - 모델: {MODEL_NAME}")
        
        self.btnSend = self.findChild(QtWidgets.QPushButton, 'btnSend')
        self.lineEditMyQuestion = self.findChild(QtWidgets.QLineEdit, 'lineEditMyQuestion')
        self.lblAnswer = self.findChild(QtWidgets.QTextEdit, 'lblAnswer') 
        
        if not self.lblAnswer:
            self.lblAnswer = self.findChild(QtWidgets.QPlainTextEdit, 'lblAnswer')
        
        if not self.btnSend or not self.lblAnswer or not self.lineEditMyQuestion:
            print("치명적 오류: UI 파일에서 필수 위젯을 찾을 수 없습니다.")
            sys.exit(1)

        # 🌟 UI에 검색 기능을 연결하기 위한 임시 버튼 생성 및 연결 (UI 파일에 버튼 추가가 필요합니다.)
        # self.btnSearch = self.findChild(QtWidgets.QPushButton, 'btnSearch') 
        # if self.btnSearch:
        #     self.btnSearch.clicked.connect(self.prompt_and_search_history)
        
        # 위젯 이벤트 연결 및 설정
        self.btnSend.clicked.connect(self.generate_response)
        self.lblAnswer.setReadOnly(True)

        self.chat_history = []
        self.gemini_worker = None 
        self.speech_worker = None
        
        self.lblAnswer.setText("[Mygemini] 무엇을 도와드릴까요?")
        self.lblAnswer.append("\n[DB] 대화 내용이 자동으로 기록됩니다. 질문 시 먼저 DB에서 검색합니다.")

        self.show()

    def generate_response(self):
        user_question = self.lineEditMyQuestion.text().strip()
        
        if not user_question:
            return
        
        # 🌟 사용자가 특정 명령어를 입력하면 검색 기능 실행 (이전 로직 제거)
        # if user_question.lower().startswith("검색:"):
        #     search_term = user_question[3:].strip()
        #     self.search_history(search_term)
        #     self.lineEditMyQuestion.clear()
        #     return
        
        # 1. DB에서 먼저 검색 시도. 기록이 있으면 True 반환 및 UI에 표시 후 종료.
        if self.search_history(user_question):
            self.lineEditMyQuestion.clear()
            return
            
        # 2. DB에 기록이 없으면 Gemini API 호출 시작
        user_message = f"[질문] {user_question}\n"
        self.lblAnswer.append(user_message)
        
        loading_message = "[Mygemini] 응답을 생성하는 중입니다..."
        self.lblAnswer.append(loading_message)
        QtWidgets.QApplication.processEvents() 
        
        self.chat_history.append({"role": "user", "parts": [{"text": user_question}]})

        # Gemini API 호출 (QThread 사용)
        self.gemini_worker = GeminiWorker(
            client=client,
            model_name=MODEL_NAME,
            chat_history=self.chat_history,
            user_question=user_question
        )
        
        self.gemini_worker.response_ready.connect(self.handle_response)
        self.gemini_worker.error_occurred.connect(self.handle_error)
        
        self.gemini_worker.start()
        
        self.lineEditMyQuestion.clear()
        
    def handle_response(self, user_question, gemini_response):
        """API 응답을 받아 UI에 표시하고, DB에 저장하며, 음성 출력합니다."""
        
        formatted_output = f"[Mygemini] {gemini_response}\n"
        
        # 로딩 메시지를 제거합니다.
        cursor = self.lblAnswer.textCursor()
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.StartOfLine, QtGui.QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        
        # 최종 응답을 추가합니다.
        self.lblAnswer.append(formatted_output)
        
        # 🌟 DB에 질문과 답변을 저장합니다.
        self.save_to_mysql(user_question, gemini_response)

        # 음성 출력을 새 스레드에서 시작합니다.
        self.start_speech_worker(gemini_response)

        # 스레드 종료 및 정리
        self.gemini_worker.quit()
        self.gemini_worker.wait()
        
    def handle_error(self, error_type, error_message):
        """API 오류 발생 시 UI에 오류 메시지를 표시하고 로딩 메시지를 제거합니다."""
        
        if self.chat_history and self.chat_history[-1].get("role") == "user":
             self.chat_history.pop()

        formatted_output = f"[Mygemini] {error_type} 발생: {error_message}\n"
        
        # 로딩 메시지를 제거하고 오류 메시지를 추가합니다.
        cursor = self.lblAnswer.textCursor()
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.StartOfLine, QtGui.QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        
        self.lblAnswer.append(formatted_output)
        
        # 오류 메시지 음성 출력을 새 스레드에서 시작합니다.
        self.start_speech_worker(f"{error_type} 발생: {error_message}")

        # 스레드 종료 및 정리
        self.gemini_worker.quit()
        self.gemini_worker.wait()

    def start_speech_worker(self, text):
        """블로킹될 수 있는 playsound를 별도의 SpeechWorker 스레드에서 실행합니다."""
        if self.speech_worker and self.speech_worker.isRunning():
            self.speech_worker.wait() 
            
        self.speech_worker = SpeechWorker(text)
        self.speech_worker.start()

    # =================================================================
    # 🌟 추가 기능 1: MySQL에 데이터 저장 (DB 완성)
    # =================================================================
    def save_to_mysql(self, question, answer):
        """질문과 답변을 MySQL 데이터베이스에 저장합니다."""
        try:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # 🚨 DB 연결 정보: 실제 정보로 교체해야 합니다!
            conn = pymysql.connect(
                host='bitnmeta2.synology.me',
                user='iyrc',
                passwd='Dodan1004!',
                db='gemini_ai',
                charset='utf8',
                port=3307,
                cursorclass=pymysql.cursors.DictCursor
            )
            with conn.cursor() as cursor:
                # 🚨 테이블 이름 확인: 실제 MySQL 테이블 이름으로 바꿔주세요!
                sql = "INSERT INTO chat_history (question, answer, create_at) VALUES (%s, %s, %s)"
                
                # 쿼리 실행
                cursor.execute(sql, (question, answer, current_time))
            
            conn.commit()
            print(f"✅ MySQL 저장 성공: {current_time}")

        except Exception as e:
            print(f"❌ MySQL 저장 실패: {e}")
            # UI에 오류 메시지 추가
            self.lblAnswer.append(f"[DB 오류] 기록 저장 실패: {e}")
        
        finally:
            if 'conn' in locals() and conn.open:
                conn.close()

    # =================================================================
    # 🌟 추가 기능 2: MySQL에서 히스토리 검색 (저장된 답 찾기)
    # =================================================================
    def search_history(self, search_term):
        """MySQL 데이터베이스에서 특정 단어를 포함하는 질문과 답변 기록을 검색합니다.
           검색된 기록이 있으면 True, 없으면 False를 반환합니다."""
        
        # 검색 시작 메시지를 UI에 추가 (DB 검색 중임을 알림)
        self.lblAnswer.append(f"\n[DB 검색] '{search_term}'으로 과거 기록 검색 시작...")
        QtWidgets.QApplication.processEvents()
        
        search_success = False # 검색 성공 여부를 저장할 플래그
        
        try:
            # 🚨 DB 연결 정보: save_to_mysql과 동일한 정보 사용
            conn = pymysql.connect(
                host='bitnmeta2.synology.me',
                user='iyrc',
                passwd='Dodan1004!',
                db='gemini_ai',
                charset='utf8',
                port=3307,
                cursorclass=pymysql.cursors.DictCursor
            )

            with conn.cursor() as cursor:
                # 🚨 테이블 이름 확인: 실제 MySQL 테이블 이름으로 바꿔주세요!
                # question과 answer 필드에서 검색어와 일치하는 것을 찾습니다.
                sql = "SELECT create_at, question, answer FROM chat_history WHERE question LIKE %s OR answer LIKE %s ORDER BY create_at DESC"
                search_pattern = f"%{search_term}%" # LIKE 검색을 위한 패턴
                
                cursor.execute(sql, (search_pattern, search_pattern))
                results = cursor.fetchall()
            
            # 검색 결과를 UI에 표시
            if results:
                search_success = True # 검색 성공 플래그 설정
                
                self.lblAnswer.append(f"[DB 결과] 총 {len(results)}건의 관련 기록을 찾았습니다:")
                for i, row in enumerate(results):
                    self.lblAnswer.append(f"--- [기록 {i+1}] {row['create_at']} ---")
                    self.lblAnswer.append(f"  Q: {row['question'][:50]}...") # 질문은 50자만 미리보기
                    self.lblAnswer.append(f"  A: {row['answer'][:50]}...") # 답변도 50자만 미리보기
                self.lblAnswer.append("--------------------------------------------------")
            else:
                self.lblAnswer.append("[DB 결과] 해당 검색어와 일치하는 과거 기록이 없습니다. Gemini에 질문합니다.")
            
            print(f"✅ MySQL 검색 성공: {len(results)}건")
            
            return search_success # 최종 결과 반환

        except Exception as e:
            print(f"❌ MySQL 검색 실패: {e}")
            self.lblAnswer.append(f"[DB 오류] 기록 검색 실패: {e}")
            # 오류 발생 시에도 Gemini 호출을 위해 False 반환 (DB 문제가 있다면 AI가 응답해야 함)
            return False 
        
        finally:
            if 'conn' in locals() and conn.open:
                conn.close()


# =================================================================
# 4. 프로그램 실행
# =================================================================

if __name__ == '__main__':
    # 프로그램 시작 시 남아있는 temp_speech_*.mp3 파일을 삭제합니다.
    for f in os.listdir('.'):
        if f.startswith('temp_speech_') and f.endswith('.mp3'):
            try:
                os.remove(f)
            except OSError as e:
                print(f"임시 파일 삭제 오류 {f}: {e}")
                
    app = QtWidgets.QApplication(sys.argv)
    window = GeminiApp()
    sys.exit(app.exec())