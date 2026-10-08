"""Single-widget, painter-based data particles for the startup splash."""

from __future__ import annotations

import random
from dataclasses import dataclass

from PySide6.QtCore import QElapsedTimer, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


@dataclass
class _Particle:
    x: float
    y: float
    speed: float
    length: float
    alpha: int
    square: bool


class ParticleLayer(QWidget):
    """Render a small bounded set of slow-moving data fragments."""

    def __init__(self, parent: QWidget, particle_count: int = 18) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._random = random.Random(1843)
        self._particles = [self._new_particle(initial=True) for _ in range(max(10, min(25, particle_count)))]
        self._elapsed = QElapsedTimer()
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._tick)

    def _new_particle(self, *, initial: bool = False) -> _Particle:
        return _Particle(
            x=self._random.uniform(0, 900) if initial else self._random.uniform(-30, -4),
            y=self._random.uniform(18, 245),
            speed=self._random.uniform(7, 18),
            length=self._random.uniform(2, 8),
            alpha=self._random.randint(20, 54),
            square=self._random.random() < 0.45,
        )

    def start_effects(self) -> None:
        self._elapsed.restart()
        self._timer.start()
        self.show()

    def stop_effects(self) -> None:
        self._timer.stop()
        self.hide()

    def timer_active(self) -> bool:
        return self._timer.isActive()

    def _tick(self) -> None:
        elapsed_seconds = min(self._elapsed.restart() / 1000.0, 0.1)
        for index, particle in enumerate(self._particles):
            particle.x += particle.speed * elapsed_seconds
            if particle.x > self.width() + 20:
                self._particles[index] = self._new_particle()
        self.update()

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 16, 16)
        painter.setClipPath(clip)

        colors = ((69, 195, 225), (66, 218, 174), (84, 151, 218))
        for index, particle in enumerate(self._particles):
            red, green, blue = colors[index % len(colors)]
            color = QColor(red, green, blue, particle.alpha)
            if particle.square:
                painter.fillRect(QRectF(particle.x, particle.y, 2.2, 2.2), color)
            else:
                painter.setPen(QPen(color, 1))
                painter.drawLine(
                    int(particle.x),
                    int(particle.y),
                    int(particle.x + particle.length),
                    int(particle.y),
                )
