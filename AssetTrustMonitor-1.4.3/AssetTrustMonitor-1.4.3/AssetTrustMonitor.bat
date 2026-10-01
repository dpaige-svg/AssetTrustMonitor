@echo off
setlocal
cd /d "%~dp0"

if exist "app\venv\Scripts\pythonw.exe" (
    start "" "app\venv\Scripts\pythonw.exe" "main.py"
    exit /b 0
)

where pyw >nul 2>&1
if %errorlevel% equ 0 (
    start "" pyw -3 "launchers\bootstrap.pyw"
    exit /b 0
)

where pythonw >nul 2>&1
if %errorlevel% equ 0 (
    start "" pythonw "launchers\bootstrap.pyw"
    exit /b 0
)

echo AssetTrustMonitor requires Python 3.10 or newer.
echo Install Python from https://www.python.org/downloads/ and try again.
pause
