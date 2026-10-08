"""Development-only Phase 3 stage API demonstration."""

from __future__ import annotations

import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from .splash_window import SplashWindow


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    splash = SplashWindow(auto_finish=False)
    splash.intro_finished.connect(app.quit)
    splash.show_intro()

    steps = [
        (300, lambda: splash.set_stage(1, 4, "Checking Python...")),
        (600, lambda: splash.set_detail("Python 3.13.0 detected")),
        (900, splash.complete_stage),
        (1050, lambda: splash.set_stage(2, 4, "Setting up environment...")),
        (1350, lambda: splash.set_detail("Existing virtual environment validated")),
        (1650, splash.complete_stage),
        (1800, lambda: splash.set_stage(3, 4, "Installing dependencies...")),
        (2100, lambda: splash.set_detail("Checking requirements...")),
        (2400, splash.complete_stage),
        (2550, lambda: splash.set_stage(4, 4, "Starting AssetTrustMonitor...")),
        (2850, lambda: splash.set_detail("Launching application...")),
        (3150, splash.complete_stage),
        (3300, splash.set_ready),
    ]
    for delay, callback in steps:
        QTimer.singleShot(delay, callback)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
