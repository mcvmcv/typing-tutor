"""Line chart of typing speed with a hover crosshair and tooltip."""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from ..progress import Point
from ..theme import INK, MUTED

SERIES = QColor("#2a78d6")
GRID = QColor("#eee6d6")
SURFACE = QColor("white")
MARGIN_LEFT, MARGIN_RIGHT, MARGIN_TOP, MARGIN_BOTTOM = 52, 70, 20, 40
MAX_X_LABELS = 8


def nice_step(span: float, target_ticks: int = 4) -> float:
    raw = span / target_ticks
    mag = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 2.5, 5, 10):
        if raw <= m * mag:
            return m * mag
    return 10 * mag


class WpmChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._points: list[Point] = []
        self._goal = 0.0
        self._hover: int | None = None
        self._empty_text = ""
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(240)

    def sizeHint(self) -> QSize:
        return QSize(900, 320)

    def set_data(self, points: list[Point], goal: float, empty_text: str) -> None:
        self._points = points
        self._goal = goal
        self._hover = None
        self._empty_text = empty_text
        self.update()

    # Geometry ---------------------------------------------------------------

    def _plot_rect(self) -> QRectF:
        return QRectF(MARGIN_LEFT, MARGIN_TOP,
                      self.width() - MARGIN_LEFT - MARGIN_RIGHT,
                      self.height() - MARGIN_TOP - MARGIN_BOTTOM)

    def _y_max(self) -> tuple[float, float]:
        top = max([p.wpm for p in self._points] + [self._goal, 5.0]) * 1.15
        step = nice_step(top)
        return math.ceil(top / step) * step, step

    def _x(self, i: int, plot: QRectF) -> float:
        n = len(self._points)
        if n == 1:
            return plot.center().x()
        return plot.left() + plot.width() * i / (n - 1)

    def _y(self, value: float, plot: QRectF, y_max: float) -> float:
        return plot.bottom() - plot.height() * value / y_max

    # Events -----------------------------------------------------------------

    def mouseMoveEvent(self, event) -> None:
        if not self._points:
            return
        plot = self._plot_rect()
        x = event.position().x()
        # Snap to the nearest point; the whole column is the hit target.
        nearest = min(range(len(self._points)), key=lambda i: abs(self._x(i, plot) - x))
        if nearest != self._hover:
            self._hover = nearest
            self.update()

    def leaveEvent(self, event) -> None:
        self._hover = None
        self.update()

    # Painting ---------------------------------------------------------------

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor("#e8dcc2"), 2))
        p.setBrush(SURFACE)
        p.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 16, 16)

        small = QFont(self.font())
        small.setPixelSize(13)
        p.setFont(small)
        fm = QFontMetricsF(small)

        if not self._points:
            p.setPen(QColor(MUTED))
            big = QFont(self.font())
            big.setPixelSize(18)
            p.setFont(big)
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._empty_text)
            return

        plot = self._plot_rect()
        y_max, step = self._y_max()

        # Recessive grid and y labels.
        value = 0.0
        while value <= y_max + 1e-9:
            y = self._y(value, plot, y_max)
            p.setPen(QPen(GRID, 1))
            p.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            p.setPen(QColor(MUTED))
            label = f"{value:g}"
            p.drawText(QRectF(0, y - 9, MARGIN_LEFT - 10, 18),
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, label)
            value += step

        # X labels: only where the date changes, thinned so they never collide.
        n = len(self._points)
        min_gap = plot.width() / MAX_X_LABELS
        last_right = -1e9
        last_x = -1e9
        for i, pt in enumerate(self._points):
            if i > 0 and pt.label == self._points[i - 1].label:
                continue
            x = self._x(i, plot)
            if x - last_x < min_gap:
                continue
            w = fm.horizontalAdvance(pt.label)
            if x - w / 2 < last_right + 8:
                continue
            p.setPen(QColor(MUTED))
            p.drawText(QRectF(x - w / 2 - 2, plot.bottom() + 10, w + 4, 18),
                       Qt.AlignmentFlag.AlignCenter, pt.label)
            last_right = x + w / 2
            last_x = x

        # Speed goal reference line.
        if self._goal:
            y = self._y(self._goal, plot, y_max)
            pen = QPen(QColor(MUTED), 1.5, Qt.PenStyle.DashLine)
            p.setPen(pen)
            p.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            p.setPen(QColor(INK))
            p.drawText(QRectF(plot.right() + 6, y - 9, MARGIN_RIGHT - 6, 18),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       f"Goal {self._goal:g}")

        # The line.
        pts = [QPointF(self._x(i, plot), self._y(pt.wpm, plot, y_max))
               for i, pt in enumerate(self._points)]
        if len(pts) > 1:
            path = QPainterPath(pts[0])
            for q in pts[1:]:
                path.lineTo(q)
            pen = QPen(SERIES, 2)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)

        # Crosshair under the markers.
        if self._hover is not None:
            x = pts[self._hover].x()
            p.setPen(QPen(QColor("#c9bfae"), 1))
            p.drawLine(QPointF(x, plot.top()), QPointF(x, plot.bottom()))

        # Markers with a surface ring; skip them when points are dense.
        show_markers = len(pts) <= 40
        for i, q in enumerate(pts):
            hovered = i == self._hover
            if not (show_markers or hovered or i == len(pts) - 1):
                continue
            r = 6 if hovered else 4
            p.setPen(QPen(SURFACE, 2))
            p.setBrush(SERIES)
            p.drawEllipse(q, r, r)

        # Direct label on the latest point only.
        last = self._points[-1]
        if self._hover != len(pts) - 1:
            p.setPen(QColor(INK))
            bold = QFont(small)
            bold.setBold(True)
            p.setFont(bold)
            p.drawText(QRectF(pts[-1].x() + 8, pts[-1].y() - 20, MARGIN_RIGHT, 18),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       f"{last.wpm:.0f}")
            p.setFont(small)

        if self._hover is not None:
            self._draw_tooltip(p, pts[self._hover], self._points[self._hover], fm)

    def _draw_tooltip(self, p: QPainter, at: QPointF, pt: Point, fm: QFontMetricsF) -> None:
        lines = [pt.label, f"{pt.wpm:.0f} WPM", f"{pt.accuracy:.0f}% accuracy", pt.detail]
        regular = QFont(p.font())
        bold = QFont(regular)
        bold.setBold(True)
        w = max(QFontMetricsF(bold).horizontalAdvance(s) for s in lines) + 24
        h = len(lines) * 19 + 14
        x = at.x() + 14
        if x + w > self.width() - 8:
            x = at.x() - 14 - w
        y = min(max(8, at.y() - h / 2), self.height() - h - 8)
        box = QRectF(x, y, w, h)
        p.setPen(QPen(QColor("#e0d5bd"), 1))
        p.setBrush(QColor(255, 255, 255, 245))
        p.drawRoundedRect(box, 8, 8)
        for i, text in enumerate(lines):
            p.setFont(bold if i == 1 else regular)
            p.setPen(QColor(INK) if i < 2 else QColor(MUTED))
            p.drawText(QRectF(x + 12, y + 7 + i * 19, w - 24, 19),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)
        p.setFont(regular)
