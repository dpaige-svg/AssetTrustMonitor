"""Threaded real startup checks feeding the Phase 3 splash event API."""

from __future__ import annotations

import importlib.metadata
import logging
import os
import subprocess
import sys
import threading
from collections.abc import Callable
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path

from pip._vendor.packaging.requirements import Requirement
from PySide6.QtCore import (
    QEventLoop,
    QLockFile,
    QObject,
    QStandardPaths,
    QThread,
    Signal,
    Slot,
)
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from ..ui.splash import SplashWindow

PROJECT_ROOT = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parents[3]
)
REQUIREMENTS_PATH = PROJECT_ROOT / "app" / "App_Build" / "requirements.txt"
STARTUP_LOG_PATH = PROJECT_ROOT / "app" / "processing" / "DataStore" / "startup.log"
MINIMUM_PYTHON = (3, 10)
APP_ICON_PATH = PROJECT_ROOT / "app" / "App_Build" / "assets" / "ApplicationIcon.png"
_INSTANCE_LOCK_NAME = "assettrustmonitor-1.4.4.lock"


class StartupCancelled(RuntimeError):
    pass


def _hidden_subprocess_kwargs() -> dict:
    if os.name != "nt":
        return {}
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 0
    return {
        "startupinfo": startupinfo,
        "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
    }


def _startup_logger(debug: bool) -> logging.Logger:
    STARTUP_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("assettrustmonitor.startup")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    file_handler = RotatingFileHandler(
        STARTUP_LOG_PATH,
        maxBytes=3 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


@dataclass
class StartupResult:
    success: bool = False
    error: str = ""


class StartupWorker(QObject):
    stage_started = Signal(int, int, str)
    detail_changed = Signal(str)
    stage_completed = Signal(str)
    progress_changed = Signal(int)
    preflight_finished = Signal()
    startup_error = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, *, debug: bool = False, failure_stage: int | None = None) -> None:
        super().__init__()
        self.debug = debug
        self.failure_stage = failure_stage
        self.logger = _startup_logger(debug)
        self._cancel_requested = threading.Event()
        self._process_lock = threading.Lock()
        self._owned_process: subprocess.Popen | None = None

    def request_cancel(self) -> None:
        """Request cancellation and terminate only the subprocess we own."""
        self._cancel_requested.set()
        with self._process_lock:
            process = self._owned_process
        if process is not None and process.poll() is None:
            process.terminate()

    def _check_cancelled(self) -> None:
        if self._cancel_requested.is_set():
            raise StartupCancelled("Startup cancelled")

    def _run_process(self, arguments: list[str]) -> subprocess.CompletedProcess:
        self._check_cancelled()
        process = subprocess.Popen(
            arguments,
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            **_hidden_subprocess_kwargs(),
        )
        with self._process_lock:
            self._owned_process = process
        try:
            while True:
                try:
                    stdout, stderr = process.communicate(timeout=0.15)
                    break
                except subprocess.TimeoutExpired:
                    self._check_cancelled()
        finally:
            with self._process_lock:
                self._owned_process = None
        self._check_cancelled()
        return subprocess.CompletedProcess(arguments, process.returncode, stdout, stderr)

    def _stage(self, current: int, title: str, detail: str) -> None:
        self._check_cancelled()
        self.logger.info("Stage %s/4: %s", current, title)
        self.stage_started.emit(current, 4, title)
        self.detail_changed.emit(detail)
        if self.failure_stage == current:
            raise RuntimeError(f"Intentional startup test failure at stage {current}")

    def _complete(self, current: int, summary: str) -> None:
        self.logger.info("Stage %s complete: %s", current, summary)
        self.detail_changed.emit(summary)
        self.stage_completed.emit(summary)
        self.progress_changed.emit(current * 25)

    @Slot()
    def run(self) -> None:
        self.logger.info("Startup session beginning")
        self.logger.info("Python executable: %s", sys.executable)
        self.logger.info("Python version: %s", sys.version.replace("\n", " "))
        try:
            self._check_python()
            self._check_environment()
            self._check_dependencies()
            self._check_application_entry()
        except StartupCancelled as error:
            self.logger.info("Startup cancelled by user")
            self.finished.emit(False, str(error))
            return
        except Exception as error:
            message = str(error) or error.__class__.__name__
            self.logger.exception("Startup failed: %s", message)
            self.startup_error.emit(message)
            self.finished.emit(False, message)
            return

        self.logger.info("Startup preflight completed successfully")
        self.preflight_finished.emit()

    def _check_python(self) -> None:
        self._stage(1, "Checking Python...", "Validating Python runtime...")
        if sys.version_info[:2] < MINIMUM_PYTHON:
            required = ".".join(map(str, MINIMUM_PYTHON))
            raise RuntimeError(f"Python {required}+ is required")
        version = f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} detected"
        self._complete(1, version)

    def _check_environment(self) -> None:
        self._stage(2, "Setting up environment...", "Validating virtual environment...")
        if getattr(sys, "frozen", False):
            self.logger.info("Using bundled AssetTrustMonitor runtime")
            self._complete(2, "Bundled application runtime validated")
            return
        in_virtual_environment = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
        if not in_virtual_environment and not self.debug:
            raise RuntimeError("AssetTrustMonitor virtual environment is not active")
        if in_virtual_environment:
            summary = "Existing virtual environment validated"
            self.logger.info("Virtual environment: %s", sys.prefix)
        else:
            summary = "System interpreter accepted for developer mode"
            self.logger.warning("Developer mode is running outside a virtual environment")
        self._complete(2, summary)

    def _unsatisfied_requirements(self) -> list[str]:
        missing: list[str] = []
        for raw_line in REQUIREMENTS_PATH.read_text(encoding="utf-8-sig").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            requirement = Requirement(line)
            if requirement.marker and not requirement.marker.evaluate():
                continue
            try:
                installed = importlib.metadata.version(requirement.name)
            except importlib.metadata.PackageNotFoundError:
                missing.append(requirement.name)
                continue
            if requirement.specifier and installed not in requirement.specifier:
                missing.append(requirement.name)
        return missing

    def _check_dependencies(self) -> None:
        self._stage(3, "Checking dependencies...", "Checking requirements...")
        if getattr(sys, "frozen", False):
            # PyInstaller resolves these imports during the build. Importing the
            # runtime modules here is a useful packaged-app health check without
            # attempting to run pip on the destination computer.
            import PIL  # noqa: F401
            import PySide6  # noqa: F401
            import requests  # noqa: F401
            import send2trash  # noqa: F401

            self._complete(3, "Bundled dependencies validated")
            return
        if not REQUIREMENTS_PATH.is_file():
            raise RuntimeError(f"Requirements file is missing: {REQUIREMENTS_PATH}")

        missing = self._unsatisfied_requirements()
        if not missing:
            self._complete(3, "Dependencies already satisfied")
            return

        shown = ", ".join(missing[:3])
        if len(missing) > 3:
            shown += f" and {len(missing) - 3} more"
        self.detail_changed.emit(f"Installing dependencies: {shown}")
        self.logger.info("Unsatisfied dependencies: %s", ", ".join(missing))

        result = self._run_process(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "-r",
                str(REQUIREMENTS_PATH),
                "--disable-pip-version-check",
            ],
        )
        if result.stdout:
            self.logger.info("pip stdout:\n%s", result.stdout.rstrip())
        if result.stderr:
            self.logger.warning("pip stderr:\n%s", result.stderr.rstrip())
        if result.returncode != 0:
            raise RuntimeError("Dependency installation failed")

        still_missing = self._unsatisfied_requirements()
        if still_missing:
            raise RuntimeError("Dependency validation failed after installation")
        self._complete(3, "Dependencies installed and validated")

    def _check_application_entry(self) -> None:
        self._stage(4, "Starting AssetTrustMonitor...", "Validating application entry point...")
        if getattr(sys, "frozen", False):
            import src.core
            import src.managers
            import src.services
            import src.ui  # noqa: F401

            self.detail_changed.emit("Bundled application modules validated")
            self._complete(4, "AssetTrustMonitor is ready")
            return
        entry_point = PROJECT_ROOT / "main.py"
        if not entry_point.is_file():
            raise RuntimeError("AssetTrustMonitor entry point is missing")
        compile(entry_point.read_text(encoding="utf-8-sig"), str(entry_point), "exec")
        validation = self._run_process(
            [
                sys.executable,
                "-c",
                (
                    "import sys; "
                    f"sys.path.insert(0, {str(PROJECT_ROOT / 'app')!r}); "
                    "import src.core, src.managers, src.services, src.ui"
                ),
            ],
        )
        if validation.stdout:
            self.logger.info("Application validation stdout:\n%s", validation.stdout.rstrip())
        if validation.stderr:
            self.logger.warning("Application validation stderr:\n%s", validation.stderr.rstrip())
        if validation.returncode != 0:
            raise RuntimeError("AssetTrustMonitor application imports failed; view the startup log")
        self.detail_changed.emit("Application modules validated")


class StartupController(QObject):
    stage_started = Signal(int, int, str)
    detail_changed = Signal(str)
    stage_completed = Signal(str)
    progress_changed = Signal(int)
    startup_ready = Signal()
    startup_error = Signal(str)

    def __init__(
        self,
        *,
        debug: bool = False,
        failure_stage: int | None = None,
        application_factory: Callable[[], object] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.result = StartupResult()
        self.application_instance = None
        self._application_factory = application_factory
        self._state = "STARTING"
        self._thread = QThread(self)
        self._worker = StartupWorker(debug=debug, failure_stage=failure_stage)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.stage_started.connect(self.stage_started)
        self._worker.detail_changed.connect(self.detail_changed)
        self._worker.stage_completed.connect(self.stage_completed)
        self._worker.progress_changed.connect(self.progress_changed)
        self._worker.startup_error.connect(self.startup_error)
        self._worker.preflight_finished.connect(self._initialize_application)
        self._worker.finished.connect(self._on_finished)
        self._worker.finished.connect(self._thread.quit)

    def start(self) -> None:
        if self._state != "STARTING" or self._thread.isRunning():
            return
        self._state = "RUNNING"
        self._thread.start()

    @Slot(bool, str)
    def _on_finished(self, success: bool, error: str) -> None:
        if self._state in {"READY", "FAILED", "FINISHED"}:
            return
        self.result.success = success
        self.result.error = error
        self._state = "FAILED" if error != "Startup cancelled" else "FINISHED"

    @Slot()
    def _initialize_application(self) -> None:
        if self._state != "RUNNING":
            return
        try:
            if self._application_factory is not None:
                self.application_instance = self._application_factory()
            self._worker.logger.info("Real application initialization succeeded")
        except Exception as error:
            message = str(error) or error.__class__.__name__
            self._worker.logger.exception("Application initialization failed: %s", message)
            self.result.success = False
            self.result.error = message
            self.startup_error.emit(message)
            self._state = "FAILED"
            self._thread.quit()
            return

        self.detail_changed.emit("AssetTrustMonitor initialized")
        self.stage_completed.emit("Application initialized")
        self.progress_changed.emit(100)
        self.result.success = True
        self.result.error = ""
        self._state = "READY"
        self.startup_ready.emit()
        self._thread.quit()

    def cancel(self) -> None:
        if self._state in {"FAILED", "FINISHED"}:
            return
        self._state = "FINISHED"
        self.result.success = False
        self.result.error = "Startup cancelled"
        self._worker.request_cancel()

    def shutdown(self) -> None:
        if self._thread.isRunning():
            self._worker.request_cancel()
        self._thread.quit()
        self._thread.wait(10000)


def _acquire_single_instance(application: QApplication) -> bool:
    existing = getattr(application, "_assettrustmonitor_instance_lock", None)
    if existing is not None:
        return True
    lock_directory = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.TempLocation))
    lock = QLockFile(str(lock_directory / _INSTANCE_LOCK_NAME))
    lock.setStaleLockTime(0)
    if not lock.tryLock(0):
        return False
    application._assettrustmonitor_instance_lock = lock  # type: ignore[attr-defined]
    return True


def run_startup_sequence(
    *,
    debug: bool = False,
    failure_stage: int | None = None,
    application_factory: Callable[[], object] | None = None,
    enforce_single_instance: bool = False,
) -> tuple[QApplication, StartupResult, object | None]:
    """Run real checks with a responsive splash, returning after ready/error dismissal."""
    application = QApplication.instance() or QApplication(sys.argv)
    application.setQuitOnLastWindowClosed(False)
    if APP_ICON_PATH.is_file():
        application.setWindowIcon(QIcon(str(APP_ICON_PATH)))
    if enforce_single_instance and not _acquire_single_instance(application):
        QMessageBox.information(None, "AssetTrustMonitor", "AssetTrustMonitor is already running.")
        return application, StartupResult(False, "AssetTrustMonitor is already running"), None
    splash = SplashWindow(auto_finish=False)
    controller = StartupController(
        debug=debug,
        failure_stage=failure_stage,
        application_factory=application_factory,
    )
    loop = QEventLoop()

    controller.stage_started.connect(splash.set_stage)
    controller.detail_changed.connect(splash.set_detail)
    controller.stage_completed.connect(splash.complete_stage)
    controller.progress_changed.connect(splash.set_progress)
    controller.startup_ready.connect(splash.set_ready)
    controller.startup_error.connect(splash.set_error)
    splash.cancel_requested.connect(controller.cancel)
    splash.intro_finished.connect(loop.quit)
    splash.view_log_requested.connect(lambda: splash.open_log(STARTUP_LOG_PATH))

    splash.show_intro()
    controller.start()
    loop.exec()
    controller.shutdown()
    splash.deleteLater()
    return application, controller.result, controller.application_instance
