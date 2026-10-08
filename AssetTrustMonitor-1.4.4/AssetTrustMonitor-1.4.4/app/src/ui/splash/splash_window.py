"""Small, reusable PySide6 startup intro for Asset Trust Monitor."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import (
    QEasingCurve,
    QEventLoop,
    QPropertyAnimation,
    QRectF,
    Qt,
    QTimer,
    QUrl,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QCursor,
    QDesktopServices,
    QFont,
    QPainter,
    QPainterPath,
    QPixmap,
)
from PySide6.QtWidgets import QApplication, QPushButton, QWidget

from .effects import SplashEffectController, draw_background_motion
from .startup_state import StartupDisplayState


def _default_banner_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "app" / "App_Build" / "assets" / "Banner.png"
    return Path(__file__).resolve().parents[3] / "App_Build" / "assets" / "Banner.png"


class SplashWindow(QWidget):
    """Frameless banner with a simple fade-in, hold, and fade-out sequence."""

    intro_finished = Signal()
    cancel_requested = Signal()
    view_log_requested = Signal()

    def __init__(
        self,
        banner_path: str | os.PathLike[str] | None = None,
        *,
        fade_in_ms: int = 450,
        hold_ms: int = 1800,
        fade_out_ms: int = 450,
        auto_finish: bool = True,
    ) -> None:
        super().__init__()
        self.setObjectName("assetTrustStartupSplash")
        self.setAccessibleName("AssetTrustMonitor startup")
        self.setFixedSize(900, 300)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._banner = QPixmap(str(banner_path or _default_banner_path()))
        self._status = "Initializing Asset Trust Monitor..."
        self._fade_in_ms = max(0, fade_in_ms)
        self._hold_ms = max(0, hold_ms)
        self._fade_out_ms = max(0, fade_out_ms)
        self._auto_finish = auto_finish
        self._finishing = False
        self._ready_started = False
        self._intro_finished_emitted = False
        self._main_window = None
        self._startup = StartupDisplayState()

        self._fade_animation = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade_animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._fade_animation.finished.connect(self._animation_finished)

        self._effects = SplashEffectController(self)
        self._effects.frame_changed.connect(self.update)
        self._effects.status_changed.connect(self._set_animated_status)
        self._finish_timer = QTimer(self)
        self._finish_timer.setSingleShot(True)
        self._finish_timer.setInterval(self._hold_ms)
        self._finish_timer.timeout.connect(self.finish)
        self._ready_timer = QTimer(self)
        self._ready_timer.setSingleShot(True)
        self._ready_timer.setInterval(750)
        self._ready_timer.timeout.connect(self.finish)

        self._view_log_button = QPushButton("View Log", self)
        self._close_button = QPushButton("Close", self)
        for button in (self._view_log_button, self._close_button):
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(
                "QPushButton { color: #E8EEF1; background: #26343C; border: 1px solid #53636C; "
                "border-radius: 6px; padding: 4px 12px; } "
                "QPushButton:hover { background: #34464F; }"
            )
            button.hide()
        self._view_log_button.setGeometry(686, 235, 78, 27)
        self._close_button.setGeometry(772, 235, 78, 27)
        self._view_log_button.clicked.connect(self.view_log_requested)
        self._close_button.clicked.connect(self.close)

    def show_intro(self) -> None:
        """Center, show, and begin the non-blocking intro sequence."""
        self._finishing = False
        self._center_on_current_screen()
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()
        self._effects.start_effects()

        self._fade_animation.stop()
        self._fade_animation.setDuration(self._fade_in_ms)
        self._fade_animation.setStartValue(0.0)
        self._fade_animation.setEndValue(1.0)
        self._fade_animation.start()

    def set_status(self, text: str) -> None:
        """Update the lightweight startup status for future startup stages."""
        self._effects.set_status(text)

    def set_stage(self, current: int, total: int, title: str) -> None:
        """Display a launcher-provided stage without performing its work."""
        self._auto_finish = False
        self._finish_timer.stop()
        self._startup.set_stage(current, total, title)
        self._set_error_controls_visible(False)
        self.update()

    def set_detail(self, text: str) -> None:
        self._startup.set_detail(text)
        self.update()

    def append_detail(self, text: str) -> None:
        self._startup.append_detail(text)
        self.update()

    def set_progress(self, value: float) -> None:
        self._startup.set_progress(value)
        self.update()

    def complete_stage(self, summary: str | None = None) -> None:
        self._startup.complete_current(summary)
        self.update()

    def set_error(self, message: str) -> None:
        """Enter a persistent error state; it never auto-fades."""
        self._auto_finish = False
        self._finish_timer.stop()
        self._ready_timer.stop()
        self._fade_animation.stop()
        self._startup.set_error(message)
        self._set_error_controls_visible(True)
        self._effects.pause_status_animation()
        self.update()

    def set_ready(self) -> None:
        """Show SYSTEM READY, finish one scan/pulse, then use normal fade-out."""
        if self._ready_started or self._finishing or self._startup.error_message:
            return
        self._ready_started = True
        self._auto_finish = False
        self._finish_timer.stop()
        self._startup.set_ready()
        self._set_error_controls_visible(False)
        self._effects.play_ready_transition()
        self._ready_timer.start()
        self.update()

    def start_effects(self) -> None:
        """Start all Phase 2 effects through one extension-friendly API."""
        self._effects.start_effects()

    def stop_effects(self) -> None:
        """Stop every visual timer and animation owned by the splash."""
        self._effects.stop_effects()

    def effects_active(self) -> bool:
        """Expose effect lifecycle state for verification and later phases."""
        return self._effects.timers_active()

    def _set_animated_status(self, text: str) -> None:
        self._status = text
        self.update()

    def finish(self, main_window=None) -> None:
        """Fade out, close cleanly, and optionally reveal a Qt main window."""
        if self._finishing:
            return
        self._finishing = True
        self._main_window = main_window
        self._fade_animation.stop()
        self._fade_animation.setDuration(self._fade_out_ms)
        self._fade_animation.setStartValue(self.windowOpacity())
        self._fade_animation.setEndValue(0.0)
        self._fade_animation.start()

    def _animation_finished(self) -> None:
        if not self._finishing:
            if self._auto_finish and not self._startup.error_message:
                self._finish_timer.start()
            return

        self.close()
        if self._main_window is not None:
            self._main_window.show()

    def _set_error_controls_visible(self, visible: bool) -> None:
        self._view_log_button.setVisible(visible)
        self._close_button.setVisible(visible)
        if visible:
            self._view_log_button.raise_()
            self._close_button.raise_()

    def open_log(self, path: str | os.PathLike[str]) -> bool:
        """Open the startup log with the platform's normal file handler."""
        resolved = Path(path).resolve()
        opened = QDesktopServices.openUrl(QUrl.fromLocalFile(str(resolved)))
        if not opened:
            self.set_error(f"Unable to open the log automatically. Log: {resolved}")
        return opened

    def _emit_intro_finished(self) -> None:
        if not self._intro_finished_emitted:
            self._intro_finished_emitted = True
            self.intro_finished.emit()

    def closeEvent(self, event) -> None:
        if not self._finishing:
            self.cancel_requested.emit()
        self._finish_timer.stop()
        self._ready_timer.stop()
        self._fade_animation.stop()
        self.stop_effects()
        super().closeEvent(event)
        self._emit_intro_finished()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)

    def _center_on_current_screen(self) -> None:
        application = QApplication.instance()
        if application is None:
            return
        screen = application.screenAt(QCursor.pos()) or application.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        self.move(available.center() - self.rect().center())

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        bounds = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        shape = QPainterPath()
        shape.addRoundedRect(bounds, 16, 16)
        painter.setClipPath(shape)
        painter.fillPath(shape, QColor("#081017"))

        if not self._banner.isNull():
            scaled = self._banner.scaled(
                self.size() * 1.018,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            drift = self._effects.background_phase
            x = (self.width() - scaled.width()) // 2 + int((drift - 0.5) * 5)
            y = (self.height() - scaled.height()) // 2 + int((0.5 - drift) * 3)
            painter.setOpacity(0.84)
            painter.drawPixmap(x, y, scaled)
            painter.setOpacity(1.0)

            # Reveal the existing composited artwork without introducing
            # replacement logo/title assets. These bounds correspond to the
            # supplied banner's stable branding regions.
            logo_bounds = QRectF(350, 42, 230, 202)
            title_bounds = QRectF(48, 92, 310, 90)

            painter.save()
            painter.setClipRect(logo_bounds)
            painter.fillRect(
                logo_bounds,
                QColor(2, 8, 12, int(185 * (1.0 - self._effects.logo_reveal))),
            )
            painter.setOpacity(0.08 + self._effects.logo_pulse * 0.16)
            painter.drawPixmap(x, y, scaled)
            painter.restore()

            painter.save()
            painter.setClipRect(title_bounds)
            painter.fillRect(
                title_bounds,
                QColor(2, 8, 12, int(205 * (1.0 - self._effects.title_reveal))),
            )
            painter.setOpacity(self._effects.title_reveal * 0.24)
            title_offset = int((1.0 - self._effects.title_reveal) * -9)
            painter.drawPixmap(x + title_offset, y, scaled)
            painter.restore()
        else:
            painter.setPen(QColor("#F2F5F7"))
            title_font = QApplication.font()
            title_font.setPointSize(28)
            title_font.setWeight(QFont.Weight.DemiBold)
            painter.setFont(title_font)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "AssetTrustMonitor")

        draw_background_motion(painter, bounds, self._effects.background_phase)

        if self._startup.current is not None or self._startup.ready or self._startup.error_message:
            self._paint_startup_panel(painter)
            return

        status_bounds = QRectF(28, self.height() - 48, self.width() - 56, 30)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(3, 10, 15, 185))
        painter.drawRoundedRect(status_bounds, 8, 8)
        painter.setPen(QColor("#DCE5EA"))
        status_font = QApplication.font()
        status_font.setPointSize(10)
        painter.setFont(status_font)
        painter.drawText(status_bounds, Qt.AlignmentFlag.AlignCenter, self._status)

    def _paint_startup_panel(self, painter: QPainter) -> None:
        panel = QRectF(30, 172, self.width() - 60, 116)
        painter.setOpacity(1.0)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(3, 10, 15, 218))
        painter.drawRoundedRect(panel, 12, 12)

        normal_font = QApplication.font()
        normal_font.setPointSize(9)
        title_font = QApplication.font()
        title_font.setPointSize(12)
        title_font.setWeight(QFont.Weight.DemiBold)

        if self._startup.error_message:
            painter.setFont(title_font)
            painter.setPen(QColor("#FF8B86"))
            painter.drawText(QRectF(48, 186, 804, 24), "!  STARTUP ERROR")
            painter.setFont(normal_font)
            painter.setPen(QColor("#E8D6D5"))
            painter.drawText(QRectF(48, 214, 620, 42), Qt.TextFlag.TextWordWrap, self._startup.error_message)
            self._paint_progress(painter, self._startup.progress, error=True)
            return

        if self._startup.ready:
            painter.setFont(title_font)
            painter.setPen(QColor("#74E0A3"))
            painter.drawText(QRectF(48, 190, 804, 28), Qt.AlignmentFlag.AlignCenter, "✓  SYSTEM READY")
            painter.setFont(normal_font)
            painter.setPen(QColor("#CAD5DB"))
            detail = self._startup.latest_detail or "AssetTrustMonitor is ready"
            painter.drawText(QRectF(48, 222, 804, 20), Qt.AlignmentFlag.AlignCenter, detail)
            self._paint_progress(painter, 100)
            return

        stage = self._startup.current
        if stage is None:
            return

        summaries = self._startup.completed_summaries
        painter.setFont(normal_font)
        painter.setPen(QColor("#75D9A0"))
        summary_text = "   •   ".join(f"✓ {summary}" for summary in summaries)
        painter.drawText(QRectF(48, 181, 804, 18), summary_text)

        badge = QRectF(48, 204, 58, 26)
        painter.setBrush(QColor(37, 114, 111, 150))
        painter.setPen(QColor(101, 224, 199, 170))
        painter.drawRoundedRect(badge, 7, 7)
        painter.setFont(normal_font)
        painter.setPen(QColor("#DFF9F3"))
        painter.drawText(
            badge,
            Qt.AlignmentFlag.AlignCenter,
            f"{stage.current}/{stage.total}",
        )

        painter.setFont(title_font)
        painter.setPen(QColor("#F1F5F7"))
        painter.drawText(QRectF(120, 202, 730, 27), stage.title)
        painter.setFont(normal_font)
        detail = "  ·  ".join(self._startup.detail_lines[-2:]) or "Preparing AssetTrustMonitor"
        painter.setPen(QColor("#AEBBC2"))
        painter.drawText(QRectF(120, 231, 730, 21), detail)
        self._paint_progress(painter, self._startup.progress)

    def _paint_progress(self, painter: QPainter, value: int, *, error: bool = False) -> None:
        track = QRectF(48, 268, self.width() - 96, 4)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 24))
        painter.drawRoundedRect(track, 2, 2)
        fill_width = track.width() * max(0, min(100, value)) / 100
        if fill_width <= 0:
            return
        painter.setBrush(QColor("#D76262") if error else QColor("#53D9B0"))
        painter.drawRoundedRect(QRectF(track.left(), track.top(), fill_width, track.height()), 2, 2)


def run_startup_intro(
    banner_path: str | os.PathLike[str] | None = None,
) -> QApplication:
    """Run only the splash stage and return the still-live QApplication."""
    application = QApplication.instance()
    if application is None:
        application = QApplication(sys.argv)
    application.setQuitOnLastWindowClosed(False)

    intro_loop = QEventLoop()
    splash = SplashWindow(banner_path=banner_path)
    splash.intro_finished.connect(intro_loop.quit)
    splash.show_intro()
    intro_loop.exec()
    splash.deleteLater()
    application.processEvents()
    return application
