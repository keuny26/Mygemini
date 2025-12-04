import sys
from PyQt6 import QtWidgets, uic, QtCore, QtGui 
from google import genai
from google.genai.errors import APIError
from google.genai import types
import os
# playsound, gTTS, 임시 파일 처리를 위한 모듈을 가져옵니다.
from gtts import gTTS
from playsound import playsound
import uuid # 고유한 임시 파일 이름을 위해 필요

# =================================================================
# 1. 설정 및 초기화
# =================================================================

# 1. UI 파일 이름 설정
UI_FILE_NAME = "Mygemini.ui"

# 🌟 중요: API 키를 여기에 입력하세요. 🌟
GEMINI_API_KEY = "GEMINI_API_KEY"

# 2. Gemini 클라이언트 초기화
if not GEMINI_API_KEY:
    print("치명적 오류: GEMINI_API_KEY가 설정되지 않았습니다.")
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
        
        # 위젯 찾기 (이전 코드와 동일)
        self.btnSend = self.findChild(QtWidgets.QPushButton, 'btnSend')
        self.lineEditMyQuestion = self.findChild(QtWidgets.QLineEdit, 'lineEditMyQuestion')
        
        self.lblAnswer = self.findChild(QtWidgets.QTextEdit, 'lblAnswer') 
        if not self.lblAnswer:
            self.lblAnswer = self.findChild(QtWidgets.QPlainTextEdit, 'lblAnswer')
        
        if not self.btnSend or not self.lblAnswer or not self.lineEditMyQuestion:
            print("치명적 오류: UI 파일에서 필수 위젯을 찾을 수 없습니다.")
            sys.exit(1)

        # 위젯 이벤트 연결 및 설정
        self.btnSend.clicked.connect(self.generate_response)
        self.lblAnswer.setReadOnly(True)

        self.chat_history = []
        self.gemini_worker = None 
        
        self.lblAnswer.setText("[Mygemini] 무엇을 도와드릴까요?")

        self.show()

    def generate_response(self):
        user_question = self.lineEditMyQuestion.text().strip()
        
        if not user_question:
            return
        
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
        """API 응답을 받아 UI에 최종적으로 표시하고 로딩 메시지를 제거하며 음성 출력합니다."""
        
        formatted_output = f"[Mygemini] {gemini_response}\n"
        
        # 로딩 메시지를 제거합니다.
        cursor = self.lblAnswer.textCursor()
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.StartOfLine, QtGui.QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        
        # 최종 응답을 추가합니다.
        self.lblAnswer.append(formatted_output)
        
        # 🌟 응답을 음성으로 출력합니다.
        self.text_to_speech(gemini_response)

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
        
        # 🌟 오류 메시지를 음성으로 출력합니다.
        self.text_to_speech(f"{error_type} 발생: {error_message}")


        # 스레드 종료 및 정리
        self.gemini_worker.quit()
        self.gemini_worker.wait()

    # =================================================================
    # 🌟 수정된 음성 출력 메서드 (gTTS + playsound 사용, 임시 파일 사용)
    # =================================================================
    def text_to_speech(self, text):
        """gTTS를 사용하여 텍스트를 음성으로 변환하고 playsound로 재생합니다."""
        
        try:
            print("음성 생성 및 재생 시작...")
            # 임시 파일 이름 생성 (중복 방지)
            filename = f"temp_speech_{uuid.uuid4().hex}.mp3"
            
            # 1. gTTS 객체 생성 (한국어 'ko' 설정) 및 파일로 저장
            tts = gTTS(text=text, lang='ko')
            tts.save(filename)
            
            # 2. playsound로 재생 (이 부분이 블로킹됩니다)
            playsound(filename)
            
            # 3. 재생 후 파일 삭제 (클린업)
            os.remove(filename)
            print("음성 재생 완료 및 파일 삭제.")
            
        except Exception as e:
            # 음성 출력 중 오류가 발생해도 프로그램은 계속 실행되도록 예외 처리
            print(f"음성 출력 오류 (gTTS/playsound): {e}")


# =================================================================
# 4. 프로그램 실행
# =================================================================

if __name__ == '__main__':
    # 🌟 프로그램 시작 시 남아있는 temp_speech_*.mp3 파일을 삭제합니다.
    for f in os.listdir('.'):
        if f.startswith('temp_speech_') and f.endswith('.mp3'):
            try:
                os.remove(f)
            except OSError as e:
                print(f"임시 파일 삭제 오류 {f}: {e}")
                
    app = QtWidgets.QApplication(sys.argv)
    window = GeminiApp()

    sys.exit(app.exec())
