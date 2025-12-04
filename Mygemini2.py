import sys
from PyQt6 import QtWidgets, uic
from google import genai
from google.genai.errors import APIError
# 🌟 수정: GenerateContentConfig를 types 모듈에서 명시적으로 가져옵니다. 🌟
from google.genai import types

# =================================================================
# 1. 설정 및 초기화
# =================================================================

# 1. UI 파일 이름 설정
UI_FILE_NAME = "Mygemini.ui"

# 🌟 중요: 실제 API 키를 입력했습니다. 이 키를 실제 사용하는 키로 교체하세요. 🌟
GEMINI_API_KEY = "GEMINI_API_KEY"

# 2. Gemini 클라이언트 초기화
try:
    # API 키를 genai.Client()에 직접 전달합니다.
    client = genai.Client(api_key=GEMINI_API_KEY)
    MODEL_NAME = "gemini-2.5-flash" # 사용할 모델 지정
except ValueError as e:
    print(f"클라이언트 초기화 오류: API 키가 잘못되었거나 누락되었습니다. {e}")
    sys.exit(1)


# =================================================================
# 2. 메인 애플리케이션 클래스
# =================================================================

class GeminiApp(QtWidgets.QDialog):
    def __init__(self):
        # QDialog를 기본 클래스로 사용
        super().__init__()
        
        # UI 파일 로드
        try:
            uic.loadUi(UI_FILE_NAME, self)
        except FileNotFoundError:
            print(f"오류: {UI_FILE_NAME} 파일을 찾을 수 없습니다. 경로를 확인해 주세요.")
            sys.exit(1)
            
        self.setWindowTitle(f"Gemini Q&A - 모델: {MODEL_NAME}")
        
        # 3. 위젯을 명시적으로 찾습니다 (findChild 사용으로 UI 바인딩 오류 방지)
        
        # QPushButton 및 QLineEdit는 유형을 지정합니다.
        self.btnSend = self.findChild(QtWidgets.QPushButton, 'btnSend')
        self.lineEditMyQuestion = self.findChild(QtWidgets.QLineEdit, 'lineEditMyQuestion')
        
        # lblAnswer는 QTextEdit을 먼저 찾고, 실패하면 QPlainTextEdit을 시도합니다.
        self.lblAnswer = self.findChild(QtWidgets.QTextEdit, 'lblAnswer') 
        if not self.lblAnswer:
            self.lblAnswer = self.findChild(QtWidgets.QPlainTextEdit, 'lblAnswer')
        
        # 최종적으로 위젯이 모두 성공적으로 로드되었는지 확인
        if not self.btnSend or not self.lblAnswer or not self.lineEditMyQuestion:
            missing = []
            if not self.btnSend: missing.append("'btnSend' (QPushButton)")
            # lblAnswer의 경우, TextEdit 또는 PlainTextEdit인지 다시 한번 사용자에게 안내합니다.
            if not self.lblAnswer: missing.append("'lblAnswer' (QTextEdit 또는 QPlainTextEdit 이어야 합니다!)")
            if not self.lineEditMyQuestion: missing.append("'lineEditMyQuestion' (QLineEdit)")
            
            print(f"치명적 오류: UI 파일 ({UI_FILE_NAME})에서 다음 필수 위젯을 찾을 수 없습니다: {', '.join(missing)}")
            sys.exit(1)

        # 4. 위젯 이벤트 연결 및 설정
        self.btnSend.clicked.connect(self.generate_response)
        
        # QTextEdit/QPlainTextEdit은 setReadOnly를 지원합니다.
        self.lblAnswer.setReadOnly(True)

        self.show()

    def generate_response(self):
        """
        lineEditMyQuestion의 내용을 가져와 Gemini API를 호출하고
        lblAnswer에 결과를 지정된 형식으로 표시합니다.
        """
        
        # 5. QLineEdit에서 사용자 질문 가져오기
        user_question = self.lineEditMyQuestion.text().strip()
        
        if not user_question:
            self.lblAnswer.setText("질문을 입력해 주세요.")
            return
        
        # 응답 생성 중임을 사용자에게 표시하고 UI 업데이트
        # 🌟 수정: 질문을 표시하는 텍스트에서 볼드체 마크다운(**)을 제거했습니다.
        self.lblAnswer.setText(f"[질문] {user_question}\n\n[Mygemini] 응답을 생성하는 중입니다...")
        QtWidgets.QApplication.processEvents() 

        # 6. Gemini API 호출
        try:
            # 🌟 수정: types.GenerateContentConfig를 사용하여 설정 객체를 생성합니다.
            # 이 설정은 한국어 답변을 유도합니다.
            config = types.GenerateContentConfig(
                system_instruction="You are a helpful assistant. Please answer all questions in Korean."
            )

            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=user_question,
                config=config # 설정 적용
            )
            
            # 응답 텍스트 추출
            gemini_response = response.text
            
        except APIError as e:
            gemini_response = f"API 오류 발생: Gemini 서버에 연결할 수 없습니다. (오류: {e})"
        except Exception as e:
            # API 관련 오류 외의 모든 오류를 여기서 처리합니다.
            gemini_response = f"예기치 않은 오류 발생: {e}"
            
        # 7. 지정된 형식으로 출력 텍스트 포맷팅
        # 🌟 수정: 질문과 답변 텍스트에서 볼드체 마크다운(**)을 모두 제거했습니다.
        formatted_output = (
            f"[질문] {user_question}\n\n"
            f"[Mygemini] {gemini_response}"
        )
        
        # 8. QTextEdit/QPlainTextEdit에 텍스트 설정 (스크롤 지원)
        self.lblAnswer.setText(formatted_output)
        
        # 9. QLineEdit 내용 지우기
        self.lineEditMyQuestion.clear()


# =================================================================
# 3. 프로그램 실행
# =================================================================

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = GeminiApp()

    sys.exit(app.exec())
