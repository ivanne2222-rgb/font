# 글결 · Windows TTF 편집기

Windows에서 별도 창으로 실행하는 TTF 편집 프로그램입니다. Tkinter와 FontTools를 사용하며 브라우저나 웹 서버가 필요하지 않습니다.

## 다운로드

[Windows 실행 패키지 ZIP 다운로드](https://github.com/ivanne2222-rgb/font/raw/refs/heads/main/downloads/TTF-Studio-Windows.zip)

GitHub 로그인이 필요한 저장소라면 먼저 로그인하세요. 다운로드한 ZIP을 모두 압축 해제하고 `TTF-Studio/start.bat`를 실행하세요. 이 패키지는 Python이 필요한 소스 배포본입니다.

## Windows 실행

1. Python 3.12 또는 3.13을 설치합니다. **Add python.exe to PATH**와 **Tcl/Tk**를 포함하세요.
2. `desktop` 폴더의 `start.bat`를 더블클릭합니다. 처음 실행할 때 FontTools를 설치하므로 인터넷이 필요합니다.
3. **TTF 열기 → 글자 선택 → 편집 → 다른 이름으로 저장** 순서로 사용합니다.

자세한 사용법은 [desktop/사용방법.txt](desktop/사용방법.txt)를 확인하세요.

## 기능

- 글꼴 이름과 스타일 변경
- 글리프 전체 탐색 및 문자·이름·유니코드 검색
- 글자 폭과 왼쪽 여백(LSB) 편집
- 윤곽점·곡선 제어점 드래그와 X/Y 좌표 입력
- 최근 50회 실행 취소, 글리프 원본 복원
- 문장 윤곽선 미리보기, 확대
- TTF 저장 전 재로드 검증과 원자적 파일 교체

좌표와 간격 입력 후 **간격 / 좌표 적용**을 눌러야 저장에 반영됩니다. 정적 glyf TTF를 지원합니다. 가변 폰트와 CFF OTF, TTC는 지원하지 않습니다. 복합 글리프는 간격만 직접 수정하며 구성 글리프를 수정하면 그 윤곽이 반영됩니다. 점·글자 추가/삭제는 지원하지 않습니다. 수정한 글리프의 힌팅과 디지털 서명은 제거합니다. 편집 화면과 미리보기는 윤곽선으로 표시합니다.

## EXE 빌드

Windows에서 `desktop/build_exe.bat`를 실행하면 `desktop/dist/TTFStudio.exe`를 생성합니다. 생성된 EXE에는 Python이 포함되므로 다른 PC에 Python을 따로 설치할 필요가 없습니다. 코드 서명은 포함하지 않습니다.

GitHub Actions에서 `Build Windows TTF Studio` 워크플로를 수동 실행하는 방법도 있습니다. Windows 테스트 후 EXE를 빌드하여 다운로드 가능한 아티팩트로 남깁니다. 이 워크플로는 아직 실행하지 않았습니다.

현재 제공 패키지는 Python 소스와 Windows 실행기입니다. 실제 Windows에서의 GUI 실행과 EXE 빌드는 이 Linux 작업 환경에서 검증하지 않았습니다.

## 개발·검증

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r desktop/requirements.txt
.venv/bin/python -m unittest discover -s desktop/tests -v
```

GUI 개발 실행은 Tk 디스플레이가 있는 환경에서 `python desktop/ttf_studio.pyw`를 사용합니다. Windows에서는 `python` 명령과 가상환경의 `Scripts` 디렉터리를 사용하세요.

이전 웹 앱 소스는 루트 `app.py`, `static` 폴더에 보존되어 있으나 새 데스크톱 패키지에는 포함하지 않습니다.
