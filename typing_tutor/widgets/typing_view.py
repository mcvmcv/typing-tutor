"""The line of text being typed, coloured as the child progresses."""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize
from PySide6.QtGui import QColor, QFontDatabase, QFontMetricsF, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from ..session import CharState, TypingSession
from ..theme import FIXED, GOOD, INK

PENDING = QColor("#9a9182")
CURSOR = QColor("#ffe08a")
CURSOR_ERROR = QColor("#ffb3b3")


class TypingView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._session: TypingSession | None = None
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(110)

    def sizeHint(self) -> QSize:
        return QSize(900, 110)

    def set_session(self, session: TypingSession) -> None:
        self._session = session
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        box = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        p.setPen(QPen(QColor("#e8dcc2"), 2))
        p.setBrush(QColor("white"))
        p.drawRoundedRect(box, 18, 18)

        s = self._session
        if s is None:
            return

        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        font.setPixelSize(int(self.height() * 0.4))
        font.setBold(True)
        fm = QFontMetricsF(font)
        cw = fm.horizontalAdvance("M")
        inner = box.adjusted(28, 0, -28, 0)
        total = len(s.text) * cw
        if total <= inner.width():
            x0 = inner.left() + (inner.width() - total) / 2
        else:
            # Scroll so the cursor stays about a third of the way in.
            x0 = inner.left() + inner.width() * 0.35 - s.pos * cw
            x0 = min(inner.left(), max(x0, inner.right() - total))

        p.setClipRect(inner)
        p.setFont(font)
        mid = box.center().y()
        baseline = mid + (fm.ascent() - fm.descent()) / 2
        cell_h = fm.height() * 1.25

        for i, ch in enumerate(s.text):
            x = x0 + i * cw
            if x + cw < inner.left() or x > inner.right():
                continue
            if i == s.pos:
                p.setPen(QColor(0, 0, 0, 0))
                p.setBrush(CURSOR_ERROR if s.error_at_cursor else CURSOR)
                p.drawRoundedRect(QRectF(x - 1, mid - cell_h / 2, cw + 2, cell_h), 6, 6)
                p.setPen(QPen(QColor(INK), 3))
                p.drawLine(QPointF(x + 3, mid + cell_h / 2 - 4),
                           QPointF(x + cw - 3, mid + cell_h / 2 - 4))
            state = s.states[i]
            if state is CharState.CORRECT:
                color = QColor(GOOD)
            elif state is CharState.CORRECTED:
                color = QColor(FIXED)
            elif i == s.pos:
                color = QColor(INK)
            else:
                color = PENDING
            if ch == " ":
                if i < s.pos:
                    continue
                glyph = "·"   # show upcoming spaces so they aren't missed
            else:
                glyph = ch
            p.setPen(color)
            gx = x + (cw - fm.horizontalAdvance(glyph)) / 2
            p.drawText(QPointF(gx, baseline), glyph)
