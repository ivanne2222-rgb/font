"""Package a Windows-built, verified PyInstaller executable for portable use."""
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

root = Path(__file__).resolve().parent
exe = root/'dist'/'TTFStudio.exe'
result = json.loads((root/'portable-smoke-result.json').read_text(encoding='utf-8'))
if result.get('status') != 'passed' or 'whole-font thinning' not in result.get('checks',[]):
    raise SystemExit('Executable smoke test did not pass')
if exe.read_bytes()[:2] != b'MZ':
    raise SystemExit('Not a Windows executable')
downloads = root.parent/'downloads'
downloads.mkdir(exist_ok=True)
archive = downloads/'TTF-Studio-Windows-Portable.zip'
readme = '''글결 · Windows 무설치 TTF 편집기

1. ZIP을 모두 압축 해제합니다.
2. TTFStudio.exe를 더블클릭합니다.
3. TTF 열기 → 글자 선택 → 편집 → 다른 이름으로 저장 순서로 사용합니다.

Python 설치, 패키지 설치, 인터넷 연결이 필요하지 않습니다.
Windows 10/11 64비트용입니다. 첫 실행에는 임시 폴더에 런타임을 푸는 시간이 걸릴 수 있습니다.
간격과 좌표는 '간격 / 좌표 적용'을 누른 뒤 저장하세요.
[글꼴 전체를 얇게 만들기]
왼쪽 '글꼴 전체 · 획 얇게 만들기'에서 강도를 입력하고 '전체 글자에 얇게 적용'을 누르세요.
처음에는 0.5~1.0%를 권장합니다. 1%는 1000 UPM 기준 획 두께를 약 10 줄입니다.
모든 글리프에 동일한 거리로 적용하며 글자 폭과 문자 매핑을 유지합니다.
복합 글리프는 실제 표시 크기의 단순 윤곽으로 변환해 균일하게 처리합니다.
전체 변환은 실행 취소 한 번으로 되돌립니다. 여러 번 적용하면 누적됩니다.
강도가 높아 글자 전체가 사라지는 경우 아무 변경도 적용하지 않고 중단합니다.
가는 장식이나 일부 획은 사라질 수 있으므로 결과를 확인한 뒤 새 파일로 저장하세요.
기하학적 변환이므로 디자이너가 만든 전용 Thin 웨이트와 결과가 다를 수 있습니다.

정적 TrueType TTF를 지원합니다. 가변 폰트와 CFF OTF는 지원하지 않습니다.
복합 글리프는 간격만 직접 수정할 수 있습니다. 윤곽은 구성 글리프에서 편집하세요.
수정한 글리프의 힌팅과 디지털 서명은 제거됩니다.
이 프로그램의 EXE는 코드 서명되지 않았습니다.
'''
with ZipFile(archive,'w',ZIP_DEFLATED) as package:
    package.write(exe,'TTF-Studio/TTFStudio.exe')
    package.writestr('TTF-Studio/사용방법.txt',readme.encode('utf-8-sig'))
    package.write(root/'portable-smoke-result.json','TTF-Studio/build-verification.json')
with ZipFile(archive) as package:
    assert package.testzip() is None
checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
(downloads/(archive.name+'.sha256')).write_text(f'{checksum}  {archive.name}\n',encoding='ascii')
print('Portable ZIP:',archive,'bytes:',archive.stat().st_size)
print('SHA256:',checksum)
