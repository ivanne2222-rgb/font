# 글결 · Windows TTF 편집기

Windows에서 별도 창으로 실행하는 TTF 편집 프로그램입니다. Tkinter와 FontTools를 사용하며 브라우저나 웹 서버가 필요하지 않습니다.

## Windows 무설치 버전 다운로드

[EXE 포함 무설치 ZIP 다운로드](https://github.com/ivanne2222-rgb/font/raw/refs/heads/main/downloads/TTF-Studio-Windows-Portable.zip)

1. ZIP을 폴더에 **모두 압축 해제**합니다.
2. `TTF-Studio/TTFStudio.exe`를 더블클릭합니다.
3. **TTF 열기 → 글자 선택 → 편집 → 다른 이름으로 저장** 순서로 사용합니다.

Windows 10/11 **64비트**용입니다. Python 설치와 인터넷 연결이 필요하지 않습니다. 첫 실행 때는 포함된 런타임을 임시 폴더에 푸는 시간이 걸릴 수 있습니다. EXE에는 코드 서명이 포함되어 있지 않습니다.

[SHA256 체크섬](https://github.com/ivanne2222-rgb/font/raw/refs/heads/main/downloads/TTF-Studio-Windows-Portable.zip.sha256)

## 소스로 실행 (선택 사항)

[Python 소스 실행 패키지](https://github.com/ivanne2222-rgb/font/raw/refs/heads/main/downloads/TTF-Studio-Windows.zip)

소스 버전은 Python 3.12 또는 3.13과 Tcl/Tk가 필요합니다. 압축 해제 후 `start.bat`를 실행하세요. 첫 실행 때 FontTools를 설치하므로 인터넷이 필요합니다. 자세한 편집 방법은 [desktop/사용방법.txt](desktop/사용방법.txt)를 확인하세요.

## 기능

- 글꼴 이름과 스타일 변경
- **글꼴 전체 획 얇게 만들기**: 강도 조절, 동일 거리 적용, 글자 폭 유지, 전체 실행 취소
- 글리프 전체 탐색 및 문자·이름·유니코드 검색
- 글자 폭과 왼쪽 여백(LSB) 편집
- 윤곽점·곡선 제어점 드래그와 X/Y 좌표 입력
- 최근 50회 실행 취소, 글리프 원본 복원
- 문장 윤곽선 미리보기, 확대
- TTF 저장 전 재로드 검증과 원자적 파일 교체

좌표와 간격 입력 후 **간격 / 좌표 적용**을 눌러야 저장에 반영됩니다. 정적 glyf TTF를 지원합니다. 가변 폰트와 CFF OTF, TTC는 지원하지 않습니다. 복합 글리프는 간격만 직접 수정하며 구성 글리프를 수정하면 그 윤곽이 반영됩니다. 점·글자 추가/삭제는 지원하지 않습니다. 수정한 글리프의 힌팅과 디지털 서명은 제거합니다. 편집 화면과 미리보기는 윤곽선으로 표시합니다.

## 글꼴 전체를 얇게 만들기

TTF를 열고 왼쪽 **글꼴 전체 · 획 얇게 만들기**에서 강도를 정한 뒤 **전체 글자에 얇게 적용**을 누르세요. 처음에는 0.5~1.0% EM을 권장합니다. 1000 UPM에서 1%는 윤곽 양쪽을 5씩 줄여 획폭을 약 10 줄입니다. 글자 폭과 문자 매핑을 유지하고, 복합 글리프는 실제 표시 크기의 단순 윤곽으로 바꿔 모든 글리프에 동일한 거리로 처리합니다. 이름/스타일과 OS/2 weightClass는 자동으로 바꾸지 않습니다.

**실행 취소** 한 번으로 전체 작업을 되돌립니다. 반복 적용은 누적되므로 다른 강도를 비교하려면 먼저 취소하세요. 취소·오류·글자 전체 소멸 시에는 부분 적용하지 않습니다. 일부 가는 획·장식은 줄어들거나 사라질 수 있으므로 결과를 확인한 뒤 다른 이름으로 저장하세요. 기하학적 변환이므로 디자이너가 만든 전용 Thin 웨이트와 동일한 결과를 보장하지 않습니다. 곡선·구멍 처리, 확대된 복합 글리프의 균일한 감소량, 가로/세로 메트릭, 저장과 실행 취소를 자동 테스트합니다.

## EXE 빌드

Windows에서 `desktop/build_exe.bat`를 실행하면 `desktop/dist/TTFStudio.exe`를 생성합니다. 생성된 EXE에는 Python이 포함되므로 다른 PC에 Python을 따로 설치할 필요가 없습니다. 코드 서명은 포함하지 않습니다.

GitHub Actions의 `Build Windows TTF Studio` 워크플로는 데스크톱 코드가 main에 올라오면 자동으로 Windows EXE를 빌드합니다. 모델 테스트와 패키징된 EXE 실행 검사를 통과한 경우 무설치 ZIP과 SHA256을 저장소에 게시합니다. 수동 실행도 지원합니다.

[Windows 빌드·검증 기록](https://github.com/ivanne2222-rgb/font/actions/runs/40450026346): 테스트 16개, EXE의 GUI 시작·윤곽 렌더링·점 선택과 드래그·이름/간격/좌표 수정·TTF 저장과 재로드·전체 획 얇게 만들기·전체 실행 취소를 통과했습니다. ZIP 안의 `build-verification.json`에도 실행 검사 결과를 포함합니다. 실제 Windows 10/11 사용자 PC별 호환성 전체를 검증한 것은 아닙니다.

## 개발·검증

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r desktop/requirements.txt
.venv/bin/python -m unittest discover -s desktop/tests -v
```

GUI 개발 실행은 Tk 디스플레이가 있는 환경에서 `python desktop/ttf_studio.pyw`를 사용합니다. Windows에서는 `python` 명령과 가상환경의 `Scripts` 디렉터리를 사용하세요.

이전 웹 앱 소스는 루트 `app.py`, `static` 폴더에 보존되어 있으나 새 데스크톱 패키지에는 포함하지 않습니다.
