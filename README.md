💬 MyGemini Q&A 챗봇 (PyQt6 기반)

이 프로젝트는 Google의 Gemini API와 Python의 PyQt6 프레임워크를 결합하여 만든 데스크톱 기반 Q&A 챗봇 애플리케이션입니다. 사용자 친화적인 GUI를 통해 Gemini 모델과 실시간으로 대화를 나눌 수 있으며, 대화 기록이 유지되어 맥락을 이해하는 연속적인 질문이 가능합니다.

✨ 주요 특징

데스크톱 GUI 환경: PyQt6를 사용하여 네이티브 데스크톱 애플리케이션 환경을 제공합니다.

실시간 대화: Google gemini-2.5-flash 모델을 백엔드로 사용하여 빠르고 정확한 응답을 제공합니다.

대화 기록 유지 (Chat History): 이전 질문과 답변을 기억하여 맥락을 유지하는 연속적인 대화가 가능합니다.

다국어 지원 (한국어): 시스템 프롬프트에 한국어 답변을 요청하는 지침이 포함되어, 모든 응답이 한국어로 제공됩니다.

오류 처리: API 연결 오류나 예기치 않은 예외 발생 시 사용자에게 친절한 오류 메시지를 표시합니다.

유연한 UI 로딩: QTextEdit 또는 QPlainTextEdit 등 다양한 텍스트 위젯 유형에 유연하게 대응하도록 설계되었습니다.

🚀 시작하기

1. 전제 조건

이 프로젝트를 실행하기 위해서는 다음 환경이 필요합니다.

Python 3.9+

Google Gemini API Key

2. 필수 라이브러리 설치

터미널이나 명령 프롬프트에서 다음 명령을 실행하여 필수 라이브러리를 설치하세요.

pip install PyQt6 google-genai


3. API Key 설정

Mygemini.py 파일을 열고, 아래 줄의 GEMINI_API_KEY 변수를 실제 발급받은 Gemini API 키로 교체해야 합니다.

GEMINI_API_KEY = "YOUR_ACTUAL_GEMINI_API_KEY_HERE"


4. UI 파일 준비

이 프로젝트는 Mygemini.ui라는 이름의 PyQt .ui 파일을 사용합니다. 이 파일은 Qt Designer를 사용하여 만들어야 하며, 다음 objectName을 가진 위젯이 포함되어야 합니다.

위젯 목적

Object Name

위젯 유형

결과 표시 창

lblAnswer

QTextEdit 또는 QPlainTextEdit

질문 입력 창

lineEditMyQuestion

QLineEdit

전송 버튼

btnSend

QPushButton

5. 애플리케이션 실행

Mygemini.py와 Mygemini.ui 파일이 같은 디렉토리에 있는지 확인한 후, 다음 명령을 실행하세요.

python Mygemini.py


⚙️ 코드 구조

주요 로직은 GeminiApp 클래스에 포함되어 있습니다.

__init__: UI 파일을 로드하고, 필요한 위젯을 명시적으로 찾아 연결하며, 초기 대화 기록을 설정합니다.

generate_response:

사용자의 질문을 가져와 대화 기록(self.chat_history)에 추가합니다.

로딩 메시지를 출력합니다.

전체 대화 기록을 client.models.generate_content로 전달하여 맥락을 유지하며 API를 호출합니다.

응답을 받은 후 로딩 메시지를 제거하고 최종 답변을 화면에 추가합니다.
