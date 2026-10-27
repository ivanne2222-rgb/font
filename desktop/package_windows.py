"""Package a Windows-built, verified PyInstaller executable for portable use."""
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

root = Path(__file__).resolve().parent
exe = root/'dist'/'TTFStudio.exe'
result = json.loads((root/'portable-smoke-result.json').read_text(encoding='utf-8'))
if result.get('status') != 'passed':
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
