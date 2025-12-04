# MyGemini Q&A Application (PyQt6 기반)

이 프로젝트는 Google의 Gemini API와 Python의 PyQt6 프레임워크를 결합하여 만든 데스크톱 기반 Q&A 챗봇 애플리케이션입니다. 사용자 친화적인 GUI를 통해 Gemini 모델과 실시간으로 대화를 나눌 수 있으며, 대화 기록이 유지되어 맥락을 이해하는 연속적인 질문이 가능합니다.

✨ 주요 특징
* 데스크톱 GUI 환경: PyQt6를 사용하여 네이티브 데스크톱 애플리케이션 환경을 제공합니다.
* 실시간 대화: Google gemini-2.5-flash 모델을 백엔드로 사용하여 빠르고 정확한 응답을 제공합니다.
* 대화 기록 유지 (Chat History): 이전 질문과 답변을 기억하여 맥락을 유지하는 연속적인 대화가 가능합니다.
* 다국어 지원 (한국어): 시스템 프롬프트에 한국어 답변을 요청하는 지침이 포함되어, 모든 응답이 한국어로 제공됩니다.
* 오류 처리: API 연결 오류나 예기치 않은 예외 발생 시 사용자에게 친절한 오류 메시지를 표시합니다.
* 유연한 UI 로딩: QTextEdit 또는 QPlainTextEdit 등 다양한 텍스트 위젯 유형에 유연하게 대응하도록 설계되었습니다.

---

## 🚀 시작하기

### 전제 조건

이 프로젝트를 실행하기 위해서는 다음 환경이 필요합니다.

* Python 3.9+
* Google Gemini API Key

### 🚨 Windows 환경 필수 요구 사항 (C++ 컴파일러)

Windows 운영체제에서 오디오 재생 라이브러리인 `simpleaudio` 또는 일부 `playsound` 버전을 설치하거나 빌드하려면 **C/C++ 컴파일러 도구**가 필요합니다.

* **설치 이유:** Python의 일부 핵심 라이브러리(C 확장 모듈)는 순수 Python 코드가 아닌 C 또는 C++로 작성되어 있습니다. 이 코드를 사용자의 Windows 환경에서 실행 가능한 파일로 변환(컴파일)하는 과정이 필요합니다.
* **해결 방법:** 다음 도구를 설치해야 합니다.
    * **Microsoft Visual C++ 14.0 이상 (Visual Studio Build Tools):**
        * [Microsoft C++ Build Tools 다운로드](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
        * 설치 시 **"C++를 사용한 데스크톱 개발"** 워크로드를 반드시 선택해야 합니다.

### 필수 라이브러리 설치

터미널이나 명령 프롬프트에서 다음 명령을 실행하여 필수 라이브러리를 설치하세요.

```bash
pip install -r requirements.txt
