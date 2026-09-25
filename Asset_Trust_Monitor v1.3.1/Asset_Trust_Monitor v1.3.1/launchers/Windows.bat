@echo off
setlocal enabledelayedexpansion

title Asset Trust Monitor

echo ========================================
echo   Asset Trust Monitor Launcher
echo ========================================
echo.

REM Change to parent directory (project root)
cd /d "%~dp0\.."

if not exist "main.py" (
    echo ERROR: main.py not found!
    pause
    exit /b 1
)

echo [1/3] Checking Python...

set PYTHON_CMD=
for %%i in (python py python3) do (
    %%i --version >nul 2>&1
    if !errorlevel! equ 0 (
        %%i -c "import sys; exit(0 if sys.version_info[0] >= 3 else 1)" >nul 2>&1
        if !errorlevel! equ 0 (
            set PYTHON_CMD=%%i
            goto :found_python
        )
    )
)

for %%p in ("%LOCALAPPDATA%\Programs\Python\Python*\python.exe" "C:\Python3*\python.exe") do (
    if exist "%%~p" (
        "%%~p" -c "import sys; exit(0 if sys.version_info[0] >= 3 else 1)" >nul 2>&1
        if !errorlevel! equ 0 (
            set PYTHON_CMD=%%~p
            goto :found_python
        )
    )
)

echo Python not found. Installing...
call :install_python
if errorlevel 1 (
    echo ERROR: Failed to install Python
    echo Please install from https://www.python.org/
    pause
    exit /b 1
)
goto :retry_detection

:found_python
for /f "tokens=*" %%v in ('!PYTHON_CMD! --version 2^>^&1') do echo       Found: %%v

echo.
echo [2/3] Checking dependencies...

!PYTHON_CMD! -m pip --version >nul 2>&1
if !errorlevel! equ 0 (
    REM Check if dependencies are already installed
    !PYTHON_CMD! -c "import PIL, pystray, send2trash" >nul 2>&1
    if !errorlevel! equ 0 (
        echo       Dependencies already installed
    ) else (
        echo       Installing missing dependencies...
        if exist "App_Build\requirements.txt" (
            !PYTHON_CMD! -m pip install -r App_Build\requirements.txt --quiet
        ) else (
            !PYTHON_CMD! -m pip install pillow pystray send2trash --quiet
        )
        echo       Dependencies installed
    )
) else (
    echo       WARNING: pip not available
)

echo.
echo [3/3] Starting application...
echo ========================================
echo.

!PYTHON_CMD! main.py

if !errorlevel! neq 0 (
    echo.
    echo ERROR: Application exited with code !errorlevel!
    pause
)
exit /b 0

:install_python
set "ARCH=amd64"
if /i "%PROCESSOR_ARCHITECTURE%"=="ARM64" set "ARCH=arm64"
if /i "%PROCESSOR_ARCHITECTURE%"=="x86" set "ARCH="

set "VER=3.13.0"
if defined ARCH (
    set "URL=https://www.python.org/ftp/python/!VER!/python-!VER!-!ARCH!.exe"
) else (
    set "URL=https://www.python.org/ftp/python/!VER!/python-!VER!.exe"
)

set "INSTALLER=%TEMP%\python-installer.exe"
powershell -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '!URL!' -OutFile '!INSTALLER!'" >nul 2>&1
if errorlevel 1 exit /b 1

start /wait "" "!INSTALLER!" /quiet PrependPath=1 Include_pip=1
del /q "!INSTALLER!" >nul 2>&1
exit /b 0

:retry_detection
set "PYTHON_CMD="
for %%i in (python py python3) do (
    %%i --version >nul 2>&1
    if !errorlevel! equ 0 (
        %%i -c "import sys; exit(0 if sys.version_info[0] >= 3 else 1)" >nul 2>&1
        if !errorlevel! equ 0 (
            set PYTHON_CMD=%%i
            goto :found_python
        )
    )
)
exit /b 1