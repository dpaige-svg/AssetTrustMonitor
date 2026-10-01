"""Reusable, lightweight animation effects for the startup splash."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QObject, Property, QPropertyAnimation, QRectF, QTimer, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen


def draw_background_motion(painter: QPainter, bounds: QRectF, phase: float) -> None:
    """Draw a faint drifting data grid behind the primary branding."""
    painter.save()
    painter.setClipRect(bounds)
    painter.setPen(QPen(QColor(66, 196, 190, 12), 1))
    spacing = 54
    offset = (phase * spacing) % spacing
    x = bounds.left() - spacing + offset
    while x < bounds.right() + spacing:
        painter.drawLine(int(x), int(bounds.top()), int(x + 42), int(bounds.bottom()))
        x += spacing
    painter.restore()


def draw_scan_line(painter: QPainter, bounds: QRectF, position: float) -> None:
    """Draw a clipped cyan/green scan line at a normalized position."""
    x = bounds.left() + position * bounds.width()
    gradient = QLinearGradient(x - 22, 0, x + 22, 0)
    gradient.setColorAt(0.0, QColor(42, 220, 207, 0))
    gradient.setColorAt(0.5, QColor(82, 235, 180, 56))
    gradient.setColorAt(1.0, QColor(42, 220, 207, 0))

    painter.save()
    painter.setClipRect(bounds)
    painter.fillRect(QRectF(x - 22, bounds.top(), 44, bounds.height()), gradient)
    painter.fillRect(QRectF(x, bounds.top(), 1.2, bounds.height()), QColor(132, 255, 216, 92))
    painter.restore()


class SplashEffectController(QObject):
    """Own all splash animations/timers and expose paint-friendly values."""

    frame_changed = Signal()
    status_changed = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._active = False
        self._scan_position = -0.08
        self._background_phase = 0.0
        self._logo_reveal = 0.0
        self._logo_pulse = 0.0
        self._title_reveal = 0.0
        self._status_base = "Initializing Asset Trust Monitor"
        self._dot_count = 0

        self._scan = self._animation(b"scanPosition", 2000, -0.08, 1.08, loops=-1)
        self._scan.setEasingCurve(QEasingCurve.Type.Linear)
        self._background = self._animation(b"backgroundPhase", 12000, 0.0, 1.0, loops=-1)
        self._logo_reveal_animation = self._animation(b"logoReveal", 360, 0.0, 1.0)
        self._title_reveal_animation = self._animation(b"titleReveal", 520, 0.0, 1.0)
        self._logo_pulse_animation = self._animation(b"logoPulse", 1900, 0.0, 0.0, loops=-1)
        self._logo_pulse_animation.setKeyValueAt(0.5, 1.0)

        self._status_timer = QTimer(self)
        self._status_timer.setInterval(360)
        self._status_timer.timeout.connect(self._advance_status)

        self._logo_timer = self._delay_timer(100, self._logo_reveal_animation.start)
        self._title_timer = self._delay_timer(320, self._title_reveal_animation.start)
        self._pulse_timer = self._delay_timer(900, self._logo_pulse_animation.start)

    def _animation(
        self,
        property_name: bytes,
        duration: int,
        start: float,
        end: float,
        *,
        loops: int = 1,
    ) -> QPropertyAnimation:
        animation = QPropertyAnimation(self, property_name, self)
        animation.setDuration(duration)
        animation.setStartValue(start)
        animation.setEndValue(end)
        animation.setLoopCount(loops)
        animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        return animation

    def _delay_timer(self, interval: int, callback) -> QTimer:
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(interval)
        timer.timeout.connect(callback)
        return timer

    def start_effects(self) -> None:
        self.stop_effects()
        self._active = True
        self._scan_position = -0.08
        self._background_phase = 0.0
        self._logo_reveal = 0.0
        self._logo_pulse = 0.0
        self._title_reveal = 0.0
        self._dot_count = 0
        self._background.start()
        self._status_timer.start()
        self._logo_timer.start()
        self._title_timer.start()
        self._pulse_timer.start()
        self._advance_status()
        self.frame_changed.emit()

    def stop_effects(self) -> None:
        self._active = False
        for timer in (
            self._status_timer,
            self._logo_timer,
            self._title_timer,
            self._pulse_timer,
        ):
            timer.stop()
        for animation in (
            self._scan,
            self._background,
            self._logo_reveal_animation,
            self._title_reveal_animation,
            self._logo_pulse_animation,
        ):
            animation.stop()

    def set_status(self, text: str) -> None:
        self._status_base = str(text).rstrip(".")
        self._dot_count = 0
        self._advance_status()

    def play_ready_transition(self) -> None:
        """Play one restrained logo pulse for the ready transition."""
        self._status_timer.stop()
        self._scan.stop()

        self._logo_pulse_animation.stop()
        self._logo_pulse_animation.setLoopCount(1)
        self._logo_pulse_animation.setDuration(700)
        self._logo_pulse_animation.start()

    def pause_status_animation(self) -> None:
        self._status_timer.stop()

    def timers_active(self) -> bool:
        timers = self.findChildren(QTimer)
        animations = self.findChildren(QPropertyAnimation)
        return any(timer.isActive() for timer in timers) or any(
            animation.state() == QPropertyAnimation.State.Running for animation in animations
        )

    def _advance_status(self) -> None:
        self._dot_count = self._dot_count % 3 + 1
        self.status_changed.emit(self._status_base + "." * self._dot_count)

    def _get_scan_position(self) -> float:
        return self._scan_position

    def _set_scan_position(self, value: float) -> None:
        self._scan_position = value
        self.frame_changed.emit()

    scanPosition = Property(float, _get_scan_position, _set_scan_position, notify=frame_changed)

    def _get_background_phase(self) -> float:
        return self._background_phase

    def _set_background_phase(self, value: float) -> None:
        self._background_phase = value
        self.frame_changed.emit()

    backgroundPhase = Property(float, _get_background_phase, _set_background_phase, notify=frame_changed)

    def _get_logo_reveal(self) -> float:
        return self._logo_reveal

    def _set_logo_reveal(self, value: float) -> None:
        self._logo_reveal = value
        self.frame_changed.emit()

    logoReveal = Property(float, _get_logo_reveal, _set_logo_reveal, notify=frame_changed)

    def _get_logo_pulse(self) -> float:
        return self._logo_pulse

    def _set_logo_pulse(self, value: float) -> None:
        self._logo_pulse = value
        self.frame_changed.emit()

    logoPulse = Property(float, _get_logo_pulse, _set_logo_pulse, notify=frame_changed)

    def _get_title_reveal(self) -> float:
        return self._title_reveal

    def _set_title_reveal(self, value: float) -> None:
        self._title_reveal = value
        self.frame_changed.emit()

    titleReveal = Property(float, _get_title_reveal, _set_title_reveal, notify=frame_changed)

    @property
    def scan_position(self) -> float:
        return self._scan_position

    @property
    def background_phase(self) -> float:
        return self._background_phase

    @property
    def logo_reveal(self) -> float:
        return self._logo_reveal

    @property
    def logo_pulse(self) -> float:
        return self._logo_pulse

    @property
    def title_reveal(self) -> float:
        return self._title_reveal
