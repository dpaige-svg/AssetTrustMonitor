"""Windowed first-run bootstrap for AssetTrustMonitor.

This file intentionally uses only the Python standard library: it must be able
to create the first visible window before PySide6 and Pillow are installed.
"""

from __future__ import annotations

import ctypes
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENV_DIR = ROOT / "app" / "venv"
VENV_PYTHON = VENV_DIR / "Scripts" / "python.exe"
VENV_PYTHONW = VENV_DIR / "Scripts" / "pythonw.exe"
REQUIREMENTS = ROOT / "app" / "App_Build" / "requirements.txt"
PLUGIN = ROOT / "app" / "App_Build" / "plugins" / "AssetTrustMirrorPlugin.lua"
LOG_PATH = ROOT / "app" / "processing" / "DataStore" / "bootstrap.log"
BANNER = ROOT / "app" / "App_Build" / "assets" / "Banner.png"
_BOOTSTRAP_MUTEX_HANDLE = None


def _acquire_bootstrap_lock() -> bool:
    """Prevent concurrent first-run installers before the main app lock exists."""
    global _BOOTSTRAP_MUTEX_HANDLE
    if os.name != "nt":
        return True

    kernel32 = ctypes.windll.kernel32
    handle = kernel32.CreateMutexW(None, False, "Local\\AssetTrustMonitor-1.4.4-Bootstrap")
    if not handle:
        return False
    if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        kernel32.CloseHandle(handle)
        return False
    _BOOTSTRAP_MUTEX_HANDLE = handle
    return True


def _hidden_process_kwargs() -> dict:
    if os.name != "nt":
        return {}
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 0
    return {
        "startupinfo": startupinfo,
        "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
    }


def _hide_attached_console() -> None:
    if os.name == "nt":
        try:
            window = ctypes.windll.kernel32.GetConsoleWindow()
            if window:
                ctypes.windll.user32.ShowWindow(window, 0)
        except OSError:
            pass


class BootstrapFailure(RuntimeError):
    pass


class BootstrapWindow:
    def __init__(self) -> None:
        import tkinter as tk

        self.tk = tk
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.root = tk.Tk()
        self.root.title("AssetTrustMonitor")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#071017")
        self.root.geometry(self._centered_geometry(900, 300))
        self.root.protocol("WM_DELETE_WINDOW", lambda: None)

        self.canvas = tk.Canvas(
            self.root, width=900, height=300, bg="#071017", highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True)
        self.banner_image = None
        try:
            source = tk.PhotoImage(file=str(BANNER))
            factor = max(1, round(source.width() / 900))
            self.banner_image = source.subsample(factor, factor)
            self.canvas.create_image(450, 150, image=self.banner_image)
        except (tk.TclError, OSError):
            self.canvas.create_text(
                450, 105, text="AssetTrustMonitor", fill="#F1F5F7",
                font=("Segoe UI", 30, "bold"),
            )

        self.canvas.create_rectangle(25, 180, 875, 282, fill="#030a0f", outline="#263842")
        self.stage_text = self.canvas.create_text(
            48, 202, anchor="w", text="Preparing first-time setup...",
            fill="#F1F5F7", font=("Segoe UI", 12, "bold"),
        )
        self.detail_text = self.canvas.create_text(
            48, 235, anchor="w", text="Checking local environment",
            fill="#B6C3CA", font=("Segoe UI", 9), width=795,
        )
        self.canvas.create_rectangle(48, 265, 852, 270, fill="#25333A", outline="")
        self.progress_bar = self.canvas.create_rectangle(48, 265, 48, 270, fill="#53D9B0", outline="")
        self.root.after(60, self._drain_events)

    def _centered_geometry(self, width: int, height: int) -> str:
        x = max(0, (self.root.winfo_screenwidth() - width) // 2)
        y = max(0, (self.root.winfo_screenheight() - height) // 2)
        return f"{width}x{height}+{x}+{y}"

    def post(self, kind: str, value: object) -> None:
        self.events.put((kind, value))

    def _drain_events(self) -> None:
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "stage":
                    title, detail, progress = value
                    self.canvas.itemconfigure(self.stage_text, text=title, fill="#F1F5F7")
                    self.canvas.itemconfigure(self.detail_text, text=detail)
                    self.canvas.coords(self.progress_bar, 48, 265, 48 + (804 * progress / 100), 270)
                elif kind == "detail":
                    self.canvas.itemconfigure(self.detail_text, text=str(value))
                elif kind == "error":
                    self.canvas.itemconfigure(self.stage_text, text="Setup could not complete", fill="#FF8B86")
                    self.canvas.itemconfigure(self.detail_text, text=str(value))
                    self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)
                elif kind == "done":
                    self.root.destroy()
                    return
        except queue.Empty:
            pass
        self.root.after(60, self._drain_events)

    def run(self) -> None:
        threading.Thread(target=self._bootstrap, daemon=True).start()
        self.root.mainloop()

    def _run_command(self, arguments: list[str], label: str) -> None:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as log:
            log.write(f"\n> {' '.join(arguments)}\n")
            process = subprocess.Popen(
                arguments,
                cwd=str(ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                errors="replace",
                bufsize=1,
                **_hidden_process_kwargs(),
            )
            if process.stdout is None:
                process.terminate()
                raise BootstrapFailure(f"{label} did not provide an output stream.")
            for raw_line in process.stdout:
                line = " ".join(raw_line.strip().split())
                log.write(raw_line)
                log.flush()
                if line:
                    self.post("detail", f"{label}: {line[:120]}")
            return_code = process.wait()
        if return_code:
            raise BootstrapFailure(f"{label} failed (exit code {return_code}). See bootstrap.log.")

    def _bootstrap(self) -> None:
        try:
            if sys.version_info[:2] < (3, 10):
                raise BootstrapFailure("Python 3.10 or newer is required.")
            if not REQUIREMENTS.is_file():
                raise BootstrapFailure("The requirements file is missing.")

            self.post("stage", ("1/4  Checking Python", sys.version.split()[0], 10))

            valid_venv = False
            if VENV_PYTHON.is_file():
                check = subprocess.run(
                    [str(VENV_PYTHON), "-c", "import sys; raise SystemExit(sys.version_info[:2] < (3, 10))"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    check=False,
                    **_hidden_process_kwargs(),
                )
                valid_venv = check.returncode == 0

            self.post("stage", ("2/4  Preparing environment", "Validating private Python environment...", 25))
            if not valid_venv:
                arguments = [sys.executable, "-m", "venv"]
                if VENV_DIR.exists():
                    arguments.append("--clear")
                arguments.append(str(VENV_DIR))
                self._run_command(arguments, "Creating environment")

            if not VENV_PYTHON.is_file() or not VENV_PYTHONW.is_file():
                raise BootstrapFailure("The private Python environment was not created correctly.")

            self.post("stage", ("3/4  Installing components", "Checking required application components...", 50))
            dependency_check = subprocess.run(
                [str(VENV_PYTHON), "-c", "import PySide6, PIL, requests, send2trash"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                check=False,
                **_hidden_process_kwargs(),
            )
            if dependency_check.returncode:
                self._run_command(
                    [str(VENV_PYTHON), "-m", "pip", "install", "-r", str(REQUIREMENTS), "--disable-pip-version-check"],
                    "Installing components",
                )

            self.post("stage", ("4/4  Starting AssetTrustMonitor", "Verifying application files...", 85))
            if not PLUGIN.is_file():
                raise BootstrapFailure("The bundled Roblox plugin is missing.")

            self.post("stage", ("Setup complete", "Opening AssetTrustMonitor...", 100))
            subprocess.Popen(
                [str(VENV_PYTHONW), str(ROOT / "main.py"), "--bootstrap-complete"],
                cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                **_hidden_process_kwargs(),
            )
            self.post("done", None)
        except Exception as error:
            self.post("error", str(error) or error.__class__.__name__)


def main() -> int:
    _hide_attached_console()
    if not _acquire_bootstrap_lock():
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as log:
            log.write("\nDuplicate first-run installer ignored.\n")
        return 0
    try:
        BootstrapWindow().run()
        return 0
    except Exception as error:
        if os.name == "nt":
            ctypes.windll.user32.MessageBoxW(None, str(error), "AssetTrustMonitor Setup", 0x10)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
