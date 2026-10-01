"""Lightweight shared log capture for stdout/stderr and UI subscribers."""

from __future__ import annotations

import atexit
import io
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from collections import deque
from typing import Callable, Deque, List, Tuple


LogEntry = Tuple[str, str]
LogListener = Callable[[str, str], None]


class LogBus:
    """Thread-safe in-memory log bus with listener fanout."""

    def __init__(
        self,
        max_entries: int = 2000,
        log_file_path: str | None = None,
        max_history_chars: int = 1_000_000,
        max_message_chars: int = 65_536,
    ):
        self._entries: Deque[LogEntry] = deque()
        self._max_entries = max_entries
        self._max_history_chars = max_history_chars
        self._max_message_chars = max_message_chars
        self._history_chars = 0
        self._listeners: List[LogListener] = []
        self._lock = threading.Lock()
        self._file_lock = threading.Lock()
        self._log_file_path = str(log_file_path) if log_file_path else self._resolve_default_log_path()
        self._log_file = None
        self._last_file_flush = time.monotonic()
        self._ensure_log_directory()

    def _resolve_default_log_path(self) -> str:
        app_folder = Path(__file__).resolve().parents[2]
        return str(app_folder / "processing" / "DataStore" / "runtime.log")

    def _ensure_log_directory(self) -> None:
        try:
            Path(self._log_file_path).parent.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            sys.__stderr__.write(f"Could not create runtime log directory: {error}\n")

    def _append_to_file(self, message: str, stream_name: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        payload = f"[{timestamp}] [{stream_name}] {message}"
        if not payload.endswith("\n"):
            payload += "\n"

        with self._file_lock:
            try:
                if self._log_file is None or self._log_file.closed:
                    self._log_file = open(
                        self._log_file_path,
                        "a",
                        encoding="utf-8",
                        newline="",
                        buffering=8192,
                    )
                self._log_file.write(payload)
                now = time.monotonic()
                if stream_name == "stderr" or now - self._last_file_flush >= 1.0:
                    self._log_file.flush()
                    self._last_file_flush = now
            except (OSError, ValueError) as error:
                sys.__stderr__.write(f"Could not append to runtime log: {error}\n")

    def flush(self) -> None:
        """Flush buffered runtime log data to disk."""
        with self._file_lock:
            try:
                if self._log_file and not self._log_file.closed:
                    self._log_file.flush()
                    self._last_file_flush = time.monotonic()
            except (OSError, ValueError) as error:
                sys.__stderr__.write(f"Could not flush runtime log: {error}\n")

    def close(self) -> None:
        """Flush and close the persistent runtime log handle."""
        with self._file_lock:
            try:
                if self._log_file and not self._log_file.closed:
                    self._log_file.flush()
                    self._log_file.close()
            except (OSError, ValueError) as error:
                sys.__stderr__.write(f"Could not close runtime log: {error}\n")
            finally:
                self._log_file = None

    def append(self, message: str, stream_name: str = "stdout") -> None:
        if not message:
            return

        self._append_to_file(message, stream_name)

        display_message = message
        if len(display_message) > self._max_message_chars:
            omitted = len(display_message) - self._max_message_chars
            display_message = (
                display_message[:self._max_message_chars]
                + f"\n... [{omitted} characters omitted from UI history; full output is in runtime.log]\n"
            )

        with self._lock:
            self._entries.append((stream_name, display_message))
            self._history_chars += len(display_message)
            while self._entries and (
                len(self._entries) > self._max_entries
                or self._history_chars > self._max_history_chars
            ):
                _, removed_message = self._entries.popleft()
                self._history_chars -= len(removed_message)
            listeners = list(self._listeners)

        for listener in listeners:
            try:
                listener(stream_name, display_message)
            except Exception as error:
                # Listeners are third-party/UI callback boundaries; isolate a
                # broken listener without hiding the reason or recursing into
                # the captured stderr stream.
                sys.__stderr__.write(f"Log listener failed: {error}\n")

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
        self._pending = ""
        self._lock = threading.Lock()

    def write(self, s: str) -> int:
        text = "" if s is None else str(s)

        if self._original_stream is not None:
            try:
                self._original_stream.write(text)
            except UnicodeEncodeError:
                # Windows launchers may leave stdout attached to a legacy
                # cp1252 console. Logging must never crash the application
                # merely because a status message contains Unicode.
                encoding = getattr(self._original_stream, "encoding", None) or "ascii"
                safe_text = text.encode(encoding, errors="backslashreplace").decode(encoding)
                self._original_stream.write(safe_text)

        if text:
            with self._lock:
                self._pending += text
                while "\n" in self._pending:
                    line, self._pending = self._pending.split("\n", 1)
                    self._bus.append(line + "\n", self._stream_name)
        return len(text)

    def flush(self) -> None:
        with self._lock:
            if self._pending:
                self._bus.append(self._pending, self._stream_name)
                self._pending = ""
        self._bus.flush()
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
atexit.register(_LOG_BUS.close)
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
