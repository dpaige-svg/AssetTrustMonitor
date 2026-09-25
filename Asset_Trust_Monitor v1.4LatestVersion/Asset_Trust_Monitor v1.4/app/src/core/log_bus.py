"""Lightweight shared log capture for stdout/stderr and UI subscribers."""

from __future__ import annotations

import io
import sys
import threading
from datetime import datetime
from pathlib import Path
from collections import deque
from typing import Callable, Deque, List, Tuple


LogEntry = Tuple[str, str]
LogListener = Callable[[str, str], None]


class LogBus:
    """Thread-safe in-memory log bus with listener fanout."""

    def __init__(self, max_entries: int = 5000, log_file_path: str | None = None):
        self._entries: Deque[LogEntry] = deque(maxlen=max_entries)
        self._listeners: List[LogListener] = []
        self._lock = threading.Lock()
        self._file_lock = threading.Lock()
        self._log_file_path = str(log_file_path) if log_file_path else self._resolve_default_log_path()
        self._ensure_log_directory()

    def _resolve_default_log_path(self) -> str:
        app_folder = Path(__file__).resolve().parents[2]
        return str(app_folder / "processing" / "DataStore" / "runtime.log")

    def _ensure_log_directory(self) -> None:
        try:
            Path(self._log_file_path).parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    def _append_to_file(self, message: str, stream_name: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        payload = f"[{timestamp}] [{stream_name}] {message}"
        if not payload.endswith("\n"):
            payload += "\n"

        with self._file_lock:
            try:
                with open(self._log_file_path, "a", encoding="utf-8", newline="") as f:
                    f.write(payload)
            except Exception:
                pass

    def append(self, message: str, stream_name: str = "stdout") -> None:
        if not message:
            return

        self._append_to_file(message, stream_name)

        with self._lock:
            self._entries.append((stream_name, message))
            listeners = list(self._listeners)

        for listener in listeners:
            try:
                listener(stream_name, message)
            except Exception:
                pass

    def get_entries(self) -> List[LogEntry]:
        with self._lock:
            return list(self._entries)

    def subscribe(self, listener: LogListener) -> None:
        with self._lock:
            if listener not in self._listeners:
                self._listeners.append(listener)

    def unsubscribe(self, listener: LogListener) -> None:
        with self._lock:
            if listener in self._listeners:
                self._listeners.remove(listener)

    def get_log_file_path(self) -> str:
        return self._log_file_path


class TeeStream(io.TextIOBase):
    """Stream wrapper that tees writes to original stream and log bus."""

    def __init__(self, original_stream, bus: LogBus, stream_name: str):
        self._original_stream = original_stream
        self._bus = bus
        self._stream_name = stream_name

    def write(self, s: str) -> int:
        text = "" if s is None else str(s)

        if self._original_stream is not None:
            self._original_stream.write(text)

        self._bus.append(text, self._stream_name)
        return len(text)

    def flush(self) -> None:
        if self._original_stream is not None:
            self._original_stream.flush()

    def isatty(self) -> bool:
        if self._original_stream is None:
            return False
        return bool(getattr(self._original_stream, "isatty", lambda: False)())

    @property
    def encoding(self):
        if self._original_stream is None:
            return "utf-8"
        return getattr(self._original_stream, "encoding", "utf-8")


_LOG_BUS = LogBus()
_CAPTURE_INSTALLED = False


def get_log_bus() -> LogBus:
    return _LOG_BUS


def get_log_file_path() -> str:
    return _LOG_BUS.get_log_file_path()


def install_stdio_capture() -> None:
    """Install stdout/stderr capture once for the current process."""
    global _CAPTURE_INSTALLED

    if _CAPTURE_INSTALLED:
        return

    sys.stdout = TeeStream(sys.stdout, _LOG_BUS, "stdout")
    sys.stderr = TeeStream(sys.stderr, _LOG_BUS, "stderr")
    _CAPTURE_INSTALLED = True
