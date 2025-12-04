import sys
# 🌟 변경: QtGui 모듈을 추가하여 QTextCursor 상수 접근 문제를 해결합니다.
from PyQt6 import QtWidgets, uic, QtCore, QtGui 
from google import genai
from google.genai.errors import APIError
from google.genai import types
# 🌟 추가: 환경 변수에서 API 키를 불러오기 위해 os 모듈을 가져옵니다.
import os

# =================================================================
# 1. 설정 및 초기화
# =================================================================

# 1. UI 파일 이름 설정
UI_FILE_NAME = "Mygemini.ui"

# 🌟 중요: 사용자 요청에 따라 새로운 API 키를 임시로 하드코딩합니다. 🌟
# 이 키는 채팅에 노출되어 보안 위험이 있으며, Google에 의해 곧 차단될 수 있습니다. 
# 새로운 키를 발급받으신 후, 아래 값을 새로운 키로 교체해 주세요.
GEMINI_API_KEY = "AIzaSyBViPGxOy1juy8dSEAJDJsuf-nPfwEir3o"

# 2. Gemini 클라이언트 초기화
if not GEMINI_API_KEY:
    # 키가 없으면 실행을 중단합니다.
    print("치명적 오류: GEMINI_API_KEY가 설정되지 않았습니다. 유효한 키를 코드에 입력해주세요.")
    sys.exit(1)
    
try:
    # API 키를 genai.Client()에 직접 전달합니다.
    client = genai.Client(api_key=GEMINI_API_KEY)
    MODEL_NAME = "gemini-2.5-flash" # 사용할 모델 지정
except ValueError as e:
    # 이 부분은 보통 API 키 형식이 잘못되었을 때 발생합니다.
    print(f"클라이언트 초기화 오류: API 키가 잘못되었거나 누락되었습니다. {e}")
    sys.exit(1)


# =================================================================
# 2. Gemini API 호출을 위한 워커 스레드 (QThread)
# =================================================================

class GeminiWorker(QtCore.QThread):
    # 결과 및 오류를 메인 스레드로 전달하기 위한 시그널 정의
    # response_ready(user_question, gemini_response)
    response_ready = QtCore.pyqtSignal(str, str) 
    # error_occurred(error_type, error_message)
    error_occurred = QtCore.pyqtSignal(str, str) 

    def __init__(self, client, model_name, chat_history, user_question):
        super().__init__()
        self.client = client
        self.model_name = model_name
        # 대화 기록은 참조로 전달되어, 스레드 내에서 업데이트됩니다.
        self.chat_history = chat_history 
        self.user_question = user_question
        
        # types.GenerateContentConfig 객체 생성
        self.config = types.GenerateContentConfig(
            system_instruction="You are a helpful assistant. Please answer all questions in Korean."
        )

    def run(self):
        """API 호출을 별도의 스레드에서 실행하여 GUI 멈춤을 방지합니다."""
        try:
            # API 호출: 전체 대화 기록을 전달합니다. (네트워크 블로킹 발생 지점)
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=self.chat_history,
                config=self.config
            )
            
            gemini_response = response.text
            
            # 🌟 대화 기록 업데이트: API 응답 성공 시에만 모델 메시지를 chat_history에 추가합니다.
            self.chat_history.append({"role": "model", "parts": [{"text": gemini_response}]})

            # 응답 성공 시 메인 스레드로 결과 신호 발생
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
        
        # 3. 위젯 찾기 (이전 코드와 동일)
        self.btnSend = self.findChild(QtWidgets.QPushButton, 'btnSend')
        self.lineEditMyQuestion = self.findChild(QtWidgets.QLineEdit, 'lineEditMyQuestion')
        
        self.lblAnswer = self.findChild(QtWidgets.QTextEdit, 'lblAnswer') 
        if not self.lblAnswer:
            self.lblAnswer = self.findChild(QtWidgets.QPlainTextEdit, 'lblAnswer')
        
        if not self.btnSend or not self.lblAnswer or not self.lineEditMyQuestion:
            missing = []
            if not self.btnSend: missing.append("'btnSend' (QPushButton)")
            if not self.lblAnswer: missing.append("'lblAnswer' (QTextEdit 또는 QPlainTextEdit 이어야 합니다!)")
            if not self.lineEditMyQuestion: missing.append("'lineEditMyQuestion' (QLineEdit)")
            
            print(f"치명적 오류: UI 파일 ({UI_FILE_NAME})에서 다음 필수 위젯을 찾을 수 없습니다: {', '.join(missing)}")
            sys.exit(1)

        # 4. 위젯 이벤트 연결 및 설정
        self.btnSend.clicked.connect(self.generate_response)
        self.lblAnswer.setReadOnly(True)

        # 🌟 대화 기록을 저장할 리스트를 초기화합니다.
        self.chat_history = []
        # 🌟 워커 스레드 인스턴스를 저장할 변수를 초기화합니다.
        self.gemini_worker = None 
        
        self.lblAnswer.setText("[Mygemini] 무엇을 도와드릴까요?")

        self.show()

    def generate_response(self):
        """사용자 질문을 처리하고 워커 스레드를 시작하여 API를 호출합니다."""
        
        user_question = self.lineEditMyQuestion.text().strip()
        
        if not user_question:
            return
        
        # 5a. 사용자 질문을 화면에 표시
        user_message = f"[질문] {user_question}\n"
        self.lblAnswer.append(user_message)
        
        # 5b. 응답 생성 중임을 사용자에게 표시하고 UI 업데이트
        loading_message = "[Mygemini] 응답을 생성하는 중입니다..."
        self.lblAnswer.append(loading_message)
        QtWidgets.QApplication.processEvents() 
        
        # 5c. 대화 기록에 사용자 메시지를 추가합니다 (API 호출을 위해)
        self.chat_history.append({"role": "user", "parts": [{"text": user_question}]})

        # 6. Gemini API 호출 (QThread 사용)
        self.gemini_worker = GeminiWorker(
            client=client,
            model_name=MODEL_NAME,
            chat_history=self.chat_history,
            user_question=user_question
        )
        
        # 워커 스레드의 시그널을 메인 스레드의 슬롯(메서드)에 연결
        self.gemini_worker.response_ready.connect(self.handle_response)
        self.gemini_worker.error_occurred.connect(self.handle_error)
        
        # 스레드 시작 (GUI 멈춤 방지)
        self.gemini_worker.start()
        
        # 9. QLineEdit 내용 지우기
        self.lineEditMyQuestion.clear()
        
    def handle_response(self, user_question, gemini_response):
        """API 응답을 받아 UI에 최종적으로 표시하고 로딩 메시지를 제거합니다."""
        
        # 7. 지정된 형식으로 출력 텍스트 포맷팅
        formatted_output = f"[Mygemini] {gemini_response}\n"
        
        # 8. QTextEdit/QPlainTextEdit에 텍스트 설정 (스크롤 지원)
        # 로딩 메시지를 제거하고 최종 응답을 추가하는 과정:
        
        # 8a. 마지막 줄 (로딩 메시지)을 제거합니다.
        cursor = self.lblAnswer.textCursor()
        # 🌟 수정: QTextCursor는 QtGui 모듈에 있습니다.
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.StartOfLine, QtGui.QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        
        # 8b. 최종 응답을 추가합니다.
        self.lblAnswer.append(formatted_output)

        # 스레드 종료 및 정리
        self.gemini_worker.quit()
        self.gemini_worker.wait()
        
    def handle_error(self, error_type, error_message):
        """API 오류 발생 시 UI에 오류 메시지를 표시하고 로딩 메시지를 제거합니다."""
        
        # 오류 발생 시 대화 기록에서 마지막 사용자 질문 항목을 제거합니다. 
        # (오류로 인해 API 호출이 실패했으므로 응답이 없었기 때문)
        if self.chat_history and self.chat_history[-1].get("role") == "user":
             self.chat_history.pop()

        # 7. 오류 메시지 포맷팅
        formatted_output = f"[Mygemini] {error_type} 발생: {error_message}\n"
        
        # 8. 로딩 메시지를 제거하고 오류 메시지를 추가하는 과정:
        cursor = self.lblAnswer.textCursor()
        # 🌟 수정: QTextCursor는 QtGui 모듈에 있습니다.
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.StartOfLine, QtGui.QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        
        # 최종 오류 메시지를 추가합니다.
        self.lblAnswer.append(formatted_output)

        # 스레드 종료 및 정리
        self.gemini_worker.quit()
        self.gemini_worker.wait()


# =================================================================
# 4. 프로그램 실행
# =================================================================

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = GeminiApp()
    sys.exit(app.exec())