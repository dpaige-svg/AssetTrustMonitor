#!/bin/bash

echo "========================================"
echo "   Asset Trust Monitor Launcher"
echo "========================================"
echo ""

cd "$(dirname "${BASH_SOURCE[0]}")"

if [ ! -f "main.py" ]; then
    echo "ERROR: main.py not found!"
    read -p "Press Enter to exit..."
    exit 1
fi

echo "[1/3] Checking Python..."

PYTHON_CMD=""
for cmd in python python3 py; do
    if command -v "$cmd" >/dev/null 2>&1; then
        if "$cmd" -c "import sys; exit(0 if sys.version_info[0] >= 3 else 1)" 2>/dev/null; then
            PYTHON_CMD="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "ERROR: Python 3.x not found!"
    echo ""
    echo "Please install Python 3:"
    echo "  - Download from: https://www.python.org/"
    echo "  - Or via Homebrew: brew install python3"
    read -p "Press Enter to exit..."
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
echo "      Found: $PYTHON_VERSION"

echo ""
echo "[2/3] Checking dependencies..."

if "$PYTHON_CMD" -m pip --version >/dev/null 2>&1; then
    # Check if dependencies are already installed
    "$PYTHON_CMD" -c "import PIL, pystray, send2trash" >/dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "      Dependencies already installed"
    else
        echo "      Installing missing dependencies..."
        if [ -f "App_Build/requirements.txt" ]; then
            "$PYTHON_CMD" -m pip install -r App_Build/requirements.txt --quiet
        else
            "$PYTHON_CMD" -m pip install pillow pystray send2trash --quiet
        fi
        echo "      Dependencies installed"
    fi
else
    echo "      WARNING: pip not available"
fi

echo ""
echo "[3/3] Starting application..."
echo "========================================"
echo ""

"$PYTHON_CMD" main.py

if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Application exited with code $?"
    read -p "Press Enter to close..."
fi
exit 0