"""Two cartoon hands showing which finger to use."""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from ..keyboard import HOME_KEYS
from ..theme import INK, SKIN, finger_color, mix

FINGER_LENGTH = {"5": 0.55, "4": 0.8, "3": 0.92, "2": 0.78}


class HandsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._active: tuple[str, ...] = ()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setMinimumHeight(170)

    def sizeHint(self) -> QSize:
        return QSize(700, 200)

    def set_active_fingers(self, fingers: tuple[str, ...]) -> None:
        self._active = fingers
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        h = self.height() - 8
        hand_w = min(self.width() * 0.36, h * 1.45)
        between = hand_w * 0.3
        left = (self.width() - (2 * hand_w + between)) / 2
        self._draw_hand(p, QRectF(left, 4, hand_w, h), "L")
        self._draw_hand(p, QRectF(left + hand_w + between, 4, hand_w, h), "R")

    def _draw_hand(self, p: QPainter, rect: QRectF, side: str) -> None:
        fw = rect.width() / 5.8
        gap = fw * 0.18
        block_w = 4 * fw + 3 * gap
        palm_h = rect.height() * 0.42
        palm_top = rect.bottom() - palm_h
        reach = palm_top - rect.top() - fw * 0.8  # room for the sparkle
        if side == "L":
            palm_left = rect.left()
            order = ("L5", "L4", "L3", "L2")
        else:
            palm_left = rect.right() - block_w
            order = ("R2", "R3", "R4", "R5")

        label_font = QFont(self.font())
        label_font.setBold(True)
        label_font.setPixelSize(max(8, int(fw * 0.5)))

        # Thumb, angled toward the middle.
        thumb = side + "T"
        p.save()
        if side == "L":
            p.translate(palm_left + block_w - fw * 0.15, palm_top + palm_h * 0.8)
            p.rotate(35)
        else:
            p.translate(palm_left + fw * 0.15, palm_top + palm_h * 0.8)
            p.rotate(-35)
        length = palm_h * 1.05
        self._finger_shape(p, QRectF(-fw / 2, -length, fw, length), fw, thumb)
        p.restore()

        for i, finger in enumerate(order):
            x = palm_left + i * (fw + gap)
            top = palm_top - reach * FINGER_LENGTH[finger[1]]
            frect = QRectF(x, top, fw, palm_top - top + fw)
            self._finger_shape(p, frect, fw, finger)
            p.setPen(QColor(INK))
            p.setFont(label_font)
            p.drawText(QRectF(x, top + fw * 0.1, fw, fw * 0.9),
                       Qt.AlignmentFlag.AlignCenter, HOME_KEYS[finger].upper())

        p.setPen(QPen(mix(QColor(SKIN), QColor(INK), 0.35), 1.5))
        p.setBrush(QColor(SKIN))
        p.drawRoundedRect(QRectF(palm_left, palm_top, block_w, palm_h), fw * 0.7, fw * 0.7)

    def _finger_shape(self, p: QPainter, rect: QRectF, fw: float, finger: str) -> None:
        color = finger_color(finger)
        if finger in self._active:
            fill = color
            pen = QPen(QColor(INK), max(2.0, fw * 0.1))
        else:
            fill = mix(QColor(SKIN), color, 0.3)
            pen = QPen(mix(QColor(SKIN), QColor(INK), 0.35), 1.5)
        p.setPen(pen)
        p.setBrush(fill)
        p.drawRoundedRect(rect, fw / 2, fw / 2)
        if finger in self._active:
            # A little sparkle above the active fingertip.
            pen = QPen(QColor(INK), max(1.5, fw * 0.07))
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            c = QPointF(rect.center().x(), rect.top() - fw * 0.45)
            for dx, dy in ((0, -1), (-0.8, -0.5), (0.8, -0.5)):
                p.drawLine(QPointF(c.x() + dx * fw * 0.2, c.y() + dy * fw * 0.2),
                           QPointF(c.x() + dx * fw * 0.45, c.y() + dy * fw * 0.45))
