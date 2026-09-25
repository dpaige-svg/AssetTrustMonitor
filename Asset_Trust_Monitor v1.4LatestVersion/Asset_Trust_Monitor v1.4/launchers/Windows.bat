@echo off
setlocal enabledelayedexpansion

title Asset Trust Monitor

echo ========================================
echo   Asset Trust Monitor Launcher
echo ========================================
echo.

cd /d "%~dp0\.."

if not exist "main.py" (
    echo ERROR: main.py not found!
    pause
    exit /b 1
)

echo [1/4] Checking Python...

set "PYTHON_CMD="
set "PYTHON_ARGS="

where py >nul 2>&1
if !errorlevel! equ 0 (
    py -3.14 -c "import sys; raise SystemExit(0 if sys.version_info[:2] >= (3, 10) else 1)" >nul 2>&1
    if !errorlevel! equ 0 (
        set "PYTHON_CMD=py"
        set "PYTHON_ARGS=-3.14"
    )
)

if not defined PYTHON_CMD (
    where py >nul 2>&1
    if !errorlevel! equ 0 (
        py -3 -c "import sys; raise SystemExit(0 if sys.version_info[:2] >= (3, 10) else 1)" >nul 2>&1
        if !errorlevel! equ 0 (
            set "PYTHON_CMD=py"
            set "PYTHON_ARGS=-3"
        )
    )
)

if not defined PYTHON_CMD (
    for %%i in (python python3) do (
        %%i -c "import sys; raise SystemExit(0 if sys.version_info[:2] >= (3, 10) else 1)" >nul 2>&1
        if !errorlevel! equ 0 (
            set "PYTHON_CMD=%%i"
            set "PYTHON_ARGS="
            goto :python_found
        )
    )
) else (
    goto :python_found
)

echo ERROR: Python 3.10+ was not found.
echo Install Python 3.14 (recommended) from https://www.python.org/downloads/
pause
exit /b 1

:python_found
for /f "tokens=*" %%v in ('!PYTHON_CMD! !PYTHON_ARGS! --version 2^>^&1') do echo       Found: %%v

echo.
echo [2/4] Setting up virtual environment...

set VENV_PATH=app\venv
set VENV_PYTHON=!VENV_PATH!\Scripts\python.exe

if exist "!VENV_PYTHON!" (
    echo       Virtual environment already exists
) else (
    echo       Creating virtual environment in !VENV_PATH!...
    !PYTHON_CMD! !PYTHON_ARGS! -m venv "!VENV_PATH!"
    if !errorlevel! neq 0 (
        echo       ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo       Virtual environment created successfully
)

set PYTHON_CMD=!VENV_PYTHON!
set "PYTHON_ARGS="

echo.
echo [3/4] Installing dependencies...

"!PYTHON_CMD!" -m pip --version >nul 2>&1
if !errorlevel! neq 0 (
    echo       Bootstrapping pip in virtual environment...
    "!PYTHON_CMD!" -m ensurepip --default-pip >nul 2>&1
    if !errorlevel! neq 0 (
        echo       ERROR: pip bootstrap failed
        pause
        exit /b 1
    )
)

set REQUIREMENTS_FILE=app\App_Build\requirements.txt
if not exist "!REQUIREMENTS_FILE!" (
    echo       ERROR: requirements.txt not found at !REQUIREMENTS_FILE!
    pause
    exit /b 1
)

"!PYTHON_CMD!" -m pip install --upgrade pip --quiet
if !errorlevel! neq 0 (
    echo       ERROR: Failed to upgrade pip
    pause
    exit /b 1
)

"!PYTHON_CMD!" -m pip install -r "!REQUIREMENTS_FILE!" --quiet
if !errorlevel! neq 0 (
    echo       ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo [4/5] Verifying bundled plugin payload...
set "LOCAL_PLUGIN_FILE=app\App_Build\plugins\AssetTrustMirrorPlugin.lua"
if not exist "!LOCAL_PLUGIN_FILE!" (
    echo       ERROR: Local plugin payload missing at !LOCAL_PLUGIN_FILE!
    pause
    exit /b 1
)

echo.
echo [5/5] Starting application...
echo ========================================
echo.

set "TCL_LIBRARY="
set "TK_LIBRARY="

set "TK_PATH_FILE=%TEMP%\atm_tcltk_%RANDOM%.txt"
"!PYTHON_CMD!" -c "import os,sys; bp=getattr(sys,'base_prefix',sys.prefix); pairs=[(os.path.join(bp,'tcl','tcl8.6'),os.path.join(bp,'tcl','tk8.6')),(os.path.join(bp,'Library','lib','tcl8.6'),os.path.join(bp,'Library','lib','tk8.6')),(os.path.join(bp,'lib','tcl8.6'),os.path.join(bp,'lib','tk8.6'))]; tcl,tk=next(((a,b) for a,b in pairs if os.path.isdir(a) and os.path.isdir(b)), ('','')); print(tcl); print(tk)" > "!TK_PATH_FILE!" 2>nul

if exist "!TK_PATH_FILE!" (
    set /p TCL_LIBRARY=<"!TK_PATH_FILE!"
    for /f "usebackq skip=1 delims=" %%B in ("!TK_PATH_FILE!") do (
        if not defined TK_LIBRARY set "TK_LIBRARY=%%B"
    )
    del /q "!TK_PATH_FILE!" >nul 2>&1
)

"!PYTHON_CMD!" -c "import os,sys; bp=getattr(sys,'base_prefix',sys.prefix); pairs=[(os.path.join(bp,'tcl','tcl8.6'),os.path.join(bp,'tcl','tk8.6')),(os.path.join(bp,'Library','lib','tcl8.6'),os.path.join(bp,'Library','lib','tk8.6')),(os.path.join(bp,'lib','tcl8.6'),os.path.join(bp,'lib','tk8.6'))]; tcl,tk=next(((a,b) for a,b in pairs if os.path.isdir(a) and os.path.isdir(b)), ('','')); os.environ.setdefault('TCL_LIBRARY', tcl); os.environ.setdefault('TK_LIBRARY', tk); import tkinter as tkmod; r=tkmod.Tk(); r.withdraw(); r.destroy()" >nul 2>&1
if !errorlevel! neq 0 (
    echo ERROR: Tkinter failed to initialize.
    if defined TCL_LIBRARY echo        Detected Tcl path: !TCL_LIBRARY!
    if defined TK_LIBRARY echo        Detected Tk path:  !TK_LIBRARY!
    echo        Reinstall Python with Tcl/Tk enabled and try again.
    pause
    exit /b 1
)

"!PYTHON_CMD!" main.py
set "EXIT_CODE=!errorlevel!"
if not "!EXIT_CODE!"=="0" (
    echo.
    echo ERROR: Application exited with code !EXIT_CODE!
    pause
    exit /b !EXIT_CODE!
)

exit /b 0
