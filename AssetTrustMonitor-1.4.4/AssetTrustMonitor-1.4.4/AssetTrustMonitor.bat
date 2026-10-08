@echo off
setlocal
cd /d "%~dp0"
set "LOG_DIR=app\processing\DataStore"
set "LAUNCH_LOG=%LOG_DIR%\launcher.log"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1
echo [%date% %time%] Launcher started in %CD%>>"%LAUNCH_LOG%"

if exist "app\venv\Scripts\python.exe" if exist "app\venv\Scripts\pythonw.exe" (
    "app\venv\Scripts\python.exe" -c "import sys, tkinter, PySide6; tkinter.Tcl(); raise SystemExit(sys.version_info < (3, 10))" >>"%LAUNCH_LOG%" 2>&1
    if errorlevel 1 goto bootstrap
    echo [%date% %time%] Starting with validated private environment.>>"%LAUNCH_LOG%"
    start "" "app\venv\Scripts\pythonw.exe" "main.py"
    exit /b 0
)

:bootstrap
set "BOOTSTRAP_PATH=app\bootstrap.pyw"
if not exist "%BOOTSTRAP_PATH%" goto missing_bootstrap

where py >nul 2>&1
if not errorlevel 1 (
    py -3 -c "import sys, tkinter; tkinter.Tcl(); raise SystemExit(sys.version_info < (3, 10))" >>"%LAUNCH_LOG%" 2>&1
    if not errorlevel 1 (
        echo [%date% %time%] Starting bootstrap through Python launcher.>>"%LAUNCH_LOG%"
        start "" py -3 "%BOOTSTRAP_PATH%"
        exit /b 0
    )
)

where python >nul 2>&1
if not errorlevel 1 (
    python -c "import sys, tkinter; tkinter.Tcl(); raise SystemExit(sys.version_info < (3, 10))" >>"%LAUNCH_LOG%" 2>&1
    if errorlevel 1 goto missing_python
    echo [%date% %time%] Starting bootstrap through Python.>>"%LAUNCH_LOG%"
    start "" python "%BOOTSTRAP_PATH%"
    exit /b 0
)

:missing_python
echo [%date% %time%] No usable Python 3.10+ installation with Tkinter was found.>>"%LAUNCH_LOG%"
echo AssetTrustMonitor requires Python 3.10 or newer.
echo Install 64-bit Python from https://www.python.org/downloads/windows/
echo During setup, keep Tcl/Tk and the Python launcher enabled, then try again.
echo Details: %LAUNCH_LOG%
pause
exit /b 1

:missing_bootstrap
echo [%date% %time%] Bootstrap file is missing: %BOOTSTRAP_PATH%>>"%LAUNCH_LOG%"
echo AssetTrustMonitor is incomplete because %BOOTSTRAP_PATH% is missing.
echo Extract the complete ZIP again. Details: %LAUNCH_LOG%
pause
exit /b 1
