"""On-screen keyboard, coloured by finger, with the next key pulsing."""
from __future__ import annotations

import math

from PySide6.QtCore import QElapsedTimer, QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from ..keyboard import ROW_UNITS, ROWS, keys_for_char
from ..theme import INK, finger_color, mix
from ..ui import timer

NEUTRAL_KEY = QColor("#ddd5c6")
WRONG_KEY = QColor("#ff6b6b")


class KeyboardView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._targets: set[str] = set()
        self._wrong: str | None = None
        self._clock = QElapsedTimer()
        self._clock.start()
        self._pulse_timer = timer(self, 33, self.update)
        self._wrong_timer = timer(self, 400, self._clear_wrong, single_shot=True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(560, 190)

    def sizeHint(self) -> QSize:
        return QSize(960, 320)

    def set_target_char(self, ch: str | None) -> None:
        self._targets = {k.ident for k in keys_for_char(ch)} if ch else set()
        if self._targets:
            self._pulse_timer.start()
        else:
            self._pulse_timer.stop()
        self.update()

    def flash_wrong_char(self, ch: str) -> None:
        keys = keys_for_char(ch) or keys_for_char(ch.lower())
        self._wrong = keys[0].ident if keys else None
        self._wrong_timer.start()
        self.update()

    def _clear_wrong(self) -> None:
        self._wrong = None
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rows = len(ROWS)
        unit = min(self.width() / (ROW_UNITS + 0.4), self.height() / (rows + 0.4))
        x0 = (self.width() - unit * ROW_UNITS) / 2
        y0 = (self.height() - unit * rows) / 2
        gap = unit * 0.1
        pulse = (math.sin(self._clock.elapsed() / 170) + 1) / 2

        big = QFont(self.font())
        big.setBold(True)
        big.setPixelSize(max(8, int(unit * 0.38)))
        small = QFont(self.font())
        small.setPixelSize(max(7, int(unit * 0.2)))

        placed = []
        for r, row in enumerate(ROWS):
            x = 0.0
            for key in row:
                rect = QRectF(x0 + x * unit + gap / 2, y0 + r * unit + gap / 2,
                              key.width * unit - gap, unit - gap)
                placed.append((key, rect))
                x += key.width

        # Draw the highlighted keys last so their glow sits on top.
        placed.sort(key=lambda kr: kr[0].ident in self._targets)
        for key, rect in placed:
            self._paint_key(p, key, rect, unit, pulse, big, small)

    def _paint_key(self, p, key, rect, unit, pulse, big, small) -> None:
        base = finger_color(key.fingers[0]) if key.fingers else NEUTRAL_KEY
        radius = unit * 0.14
        if key.ident == self._wrong:
            fill, pen = WRONG_KEY, QPen(QColor("#c0392b"), max(2.0, unit * 0.06))
        elif key.ident in self._targets:
            grow = unit * 0.06 * pulse
            rect = rect.adjusted(-grow, -grow, grow, grow)
            fill = mix(base, QColor("white"), 0.2 * pulse)
            pen = QPen(QColor(INK), max(2.0, unit * 0.07))
            glow = QColor(base)
            glow.setAlpha(int(90 + 80 * pulse))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(glow)
            g = unit * 0.12
            p.drawRoundedRect(rect.adjusted(-g, -g, g, g), radius * 1.6, radius * 1.6)
        else:
            fill = mix(base, QColor("white"), 0.55)
            pen = QPen(mix(base, QColor(INK), 0.3), 1.2)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 35))
        p.drawRoundedRect(rect.translated(0, unit * 0.04), radius, radius)
        p.setPen(pen)
        p.setBrush(fill)
        p.drawRoundedRect(rect, radius, radius)

        if key.bump:
            pen = QPen(QColor(INK), max(1.5, unit * 0.04))
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            y = rect.bottom() - rect.height() * 0.2
            p.drawLine(QPointF(rect.center().x() - unit * 0.1, y),
                       QPointF(rect.center().x() + unit * 0.1, y))

        if key.label:
            p.setPen(QColor(INK))
            p.setFont(big if len(key.label) == 1 else small)
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, key.label)
