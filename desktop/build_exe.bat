@echo off
setlocal
cd /d "%~dp0"
py -3 -m venv .venv-build
if errorlevel 1 goto failed
".venv-build\Scripts\python.exe" -m pip install -r requirements.txt pyinstaller==6.16.0
if errorlevel 1 goto failed
".venv-build\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed --name TTFStudio ttf_studio.pyw
if errorlevel 1 goto failed
echo Build complete: dist\TTFStudio.exe
pause
exit /b 0
:failed
echo EXE build failed. Check the error above.
pause
exit /b 1
