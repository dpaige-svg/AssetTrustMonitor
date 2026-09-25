#!/bin/bash

set -u

pause_and_exit() {
    local code="$1"
    read -r -n 1 -s -p "Press any key to continue . . ."
    echo
    exit "$code"
}

find_python() {
    local cmd
    for cmd in python3 python; do
        if command -v "$cmd" >/dev/null 2>&1; then
            if "$cmd" -c "import sys; raise SystemExit(0 if sys.version_info[:2] >= (3, 10) else 1)" >/dev/null 2>&1; then
                PYTHON_CMD="$cmd"
                return 0
            fi
        fi
    done

    return 1
}

configure_tcl_tk_env() {
    local tcl_tk_paths
    tcl_tk_paths="$($PYTHON_CMD -c "import os,sys; bp=getattr(sys,'base_prefix',sys.prefix); pairs=[(os.path.join(bp,'tcl','tcl8.6'),os.path.join(bp,'tcl','tk8.6')),(os.path.join(bp,'lib','tcl8.6'),os.path.join(bp,'lib','tk8.6')),(os.path.join(bp,'Frameworks','Tcl.framework','Versions','8.6','Resources','Scripts'),os.path.join(bp,'Frameworks','Tk.framework','Versions','8.6','Resources','Scripts'))]; tcl,tk=next(((a,b) for a,b in pairs if os.path.isdir(a) and os.path.isdir(b)), ('','')); print(f'{tcl}|{tk}')" 2>/dev/null)"

    if [ -n "$tcl_tk_paths" ]; then
        TCL_LIBRARY="${tcl_tk_paths%%|*}"
        TK_LIBRARY="${tcl_tk_paths##*|}"

        if [ -n "$TCL_LIBRARY" ] && [ -d "$TCL_LIBRARY" ]; then
            export TCL_LIBRARY
        fi
        if [ -n "$TK_LIBRARY" ] && [ -d "$TK_LIBRARY" ]; then
            export TK_LIBRARY
        fi
    fi
}

echo "========================================"
echo "  Asset Trust Monitor Launcher"
echo "========================================"
echo

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.." || exit 1

if [ ! -f "main.py" ]; then
    echo "ERROR: main.py not found!"
    pause_and_exit 1
fi

echo "[1/5] Checking Python..."

PYTHON_CMD=""
if ! find_python; then
    echo "ERROR: Python 3.10+ was not found."
    echo "Install Python 3.14 (recommended) from https://www.python.org/downloads/"
    pause_and_exit 1
fi

echo "      Found: $($PYTHON_CMD --version 2>&1)"

echo
echo "[2/5] Setting up virtual environment..."

VENV_PATH="app/venv"
VENV_PYTHON="$VENV_PATH/bin/python3"

if [ -x "$VENV_PYTHON" ]; then
    echo "      Virtual environment already exists"
else
    echo "      Creating virtual environment in $VENV_PATH..."
    if ! "$PYTHON_CMD" -m venv "$VENV_PATH"; then
        echo "      ERROR: Failed to create virtual environment"
        echo "      Make sure Python venv module is installed"
        pause_and_exit 1
    fi
    echo "      Virtual environment created successfully"
fi

PYTHON_CMD="$VENV_PYTHON"

echo
echo "[3/5] Installing dependencies..."

if ! "$PYTHON_CMD" -m pip --version >/dev/null 2>&1; then
    echo "      Bootstrapping pip in virtual environment..."
    if ! "$PYTHON_CMD" -m ensurepip --default-pip >/dev/null 2>&1; then
        echo "      ERROR: pip bootstrap failed"
        pause_and_exit 1
    fi
fi

REQUIREMENTS_FILE="app/App_Build/requirements.txt"

if [ ! -f "$REQUIREMENTS_FILE" ]; then
    echo "      ERROR: requirements.txt not found at $REQUIREMENTS_FILE"
    pause_and_exit 1
fi

if ! "$PYTHON_CMD" -m pip install --upgrade pip --quiet; then
    echo "      ERROR: Failed to upgrade pip"
    pause_and_exit 1
fi

if ! "$PYTHON_CMD" -m pip install -r "$REQUIREMENTS_FILE" --quiet; then
    echo "      ERROR: Failed to install dependencies"
    pause_and_exit 1
fi

echo
echo "[4/5] Verifying bundled plugin payload..."
LOCAL_PLUGIN_FILE="app/App_Build/plugins/AssetTrustMirrorPlugin.lua"
if [ ! -f "$LOCAL_PLUGIN_FILE" ]; then
    echo "      ERROR: Local plugin payload missing at $LOCAL_PLUGIN_FILE"
    pause_and_exit 1
fi

echo
echo "[5/5] Starting application..."
echo "========================================"
echo

configure_tcl_tk_env

if ! "$PYTHON_CMD" -c "import os,sys; bp=getattr(sys,'base_prefix',sys.prefix); pairs=[(os.path.join(bp,'tcl','tcl8.6'),os.path.join(bp,'tcl','tk8.6')),(os.path.join(bp,'lib','tcl8.6'),os.path.join(bp,'lib','tk8.6')),(os.path.join(bp,'Frameworks','Tcl.framework','Versions','8.6','Resources','Scripts'),os.path.join(bp,'Frameworks','Tk.framework','Versions','8.6','Resources','Scripts'))]; tcl,tk=next(((a,b) for a,b in pairs if os.path.isdir(a) and os.path.isdir(b)), ('','')); os.environ.setdefault('TCL_LIBRARY', tcl); os.environ.setdefault('TK_LIBRARY', tk); import tkinter as tkmod; r=tkmod.Tk(); r.withdraw(); r.destroy()" >/dev/null 2>&1; then
    echo "ERROR: Tkinter failed to initialize."
    if [ -n "${TCL_LIBRARY:-}" ]; then
        echo "       Detected Tcl path: ${TCL_LIBRARY}"
    fi
    if [ -n "${TK_LIBRARY:-}" ]; then
        echo "       Detected Tk path:  ${TK_LIBRARY}"
    fi
    echo "       Reinstall Python with Tcl/Tk enabled and try again."
    pause_and_exit 1
fi

"$PYTHON_CMD" main.py
EXIT_CODE=$?

if [ "$EXIT_CODE" -ne 0 ]; then
    echo
    echo "ERROR: Application exited with code $EXIT_CODE"
    pause_and_exit "$EXIT_CODE"
fi

exit 0