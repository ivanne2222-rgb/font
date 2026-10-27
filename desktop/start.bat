@echo off
setlocal
cd /d "%~dp0"
if exist ".venv-desktop\Scripts\python.exe" goto dependencies
py -3 -c "import sys, tkinter; sys.exit(sys.version_info < (3,12))" >nul 2>&1
if not errorlevel 1 (
    py -3 -m venv .venv-desktop
    goto checkvenv
)
python -c "import sys, tkinter; sys.exit(sys.version_info < (3,12))" >nul 2>&1
if errorlevel 1 (
    echo Python 3.12 or newer with Tcl/Tk is required.
    echo Download Python from https://www.python.org/downloads/windows/
    echo Enable "Add python.exe to PATH" and "tcl/tk and IDLE" during setup.
    pause
    exit /b 1
)
python -m venv .venv-desktop
:checkvenv
if not exist ".venv-desktop\Scripts\python.exe" goto failed
:dependencies
".venv-desktop\Scripts\python.exe" -c "import tkinter, fontTools; assert fontTools.__version__ == '4.60.1'" >nul 2>&1
if not errorlevel 1 goto run
".venv-desktop\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
:run
".venv-desktop\Scripts\python.exe" ttf_studio.pyw
if errorlevel 1 goto failed
exit /b 0
:failed
echo Could not start TTF Studio. Please check the error above.
pause
exit /b 1
