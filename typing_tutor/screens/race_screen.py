"""Snail Race screen: the garden track, the line to type, and the start/end panel."""

from __future__ import annotations

import math
import random
from collections.abc import Callable

from PySide6.QtCore import QElapsedTimer, QEvent, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QPushButton, QWidget

from ..race import (
    RACE_DIFFICULTIES,
    RIVAL_NAME,
    RaceEvent,
    RaceState,
    race_text,
    rival_pace,
)
from ..sounds import SoundPlayer
from ..theme import INK, MUTED, mix
from ..ui import timer
from ..widgets.typing_view import TypingView
from .game_screen import GamePanel

HUD_H = 64
LINE_H = 110  # the typing line at the bottom
RIVAL_COLOR = QColor("#b39ddb")
TRACK = QColor("#d9b98a")

# (difficulty, wpm, key_stats) -> (is_new_best, best_wpm)
RecordRace = Callable[[str, float, dict], tuple[bool, float]]


def wpm_text(value: float) -> str:
    return f"{value:.0f} WPM"


class RaceScreen(QWidget):
    menu_requested = Signal()

    def __init__(self, sounds: SoundPlayer, parent=None):
        super().__init__(parent)
        self.sounds = sounds
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.record_race: RecordRace | None = None
        self.state: RaceState | None = None
        self.rng = random.Random()
        self._known: frozenset[str] = frozenset()
        self._history: list[dict] = []
        self._best: dict[str, float] = {}
        self._player_name = ""
        self._player_color = QColor("#64b5f6")
        self._paused = False
        self._wiggle = 0.0  # a little shake when a key is wrong

        self.quit_btn = QPushButton("←  Lessons", self)
        self.quit_btn.setProperty("role", "secondary")
        self.quit_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.quit_btn.clicked.connect(self._quit)

        self.typing = TypingView(self)
        self.typing.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        labels = {k: d.label for k, d in RACE_DIFFICULTIES.items()}
        self.panel = GamePanel(self, labels)
        self.panel.difficulty_chosen.connect(self.start_race)
        self.panel.resume_requested.connect(self._resume)
        self.panel.quit_requested.connect(self._quit)

        self._clock = QElapsedTimer()
        self._timer = timer(self, 16, self._tick)

    # Setup ----------------------------------------------------------------

    def open(
        self,
        known: frozenset[str],
        history: list[dict],
        best: dict[str, float],
        name: str,
        color: str,
    ) -> None:
        """Show the start panel for a player."""
        self._known, self._history, self._best = known, history, dict(best)
        self._player_name, self._player_color = name, QColor(color)
        self.state = None
        self._paused = False
        self.typing.hide()
        self._show_panel(
            "Snail Race!",
            f"Type the line to move your snail. Can you beat <b>{RIVAL_NAME}</b> "
            "to the flag?<br>She races at a speed that suits you.",
        )
        self._timer.start()
        self._clock.restart()
        self.setFocus()

    def start_race(self, difficulty: str) -> None:
        diff = RACE_DIFFICULTIES[difficulty]
        text = race_text(self._known, self.rng)
        self.state = RaceState(diff, text, rival_pace(self._history, diff))
        self.typing.set_session(self.state.session)
        self.typing.show()
        self._paused = False
        self.panel.hide()
        self._layout_children()
        self._clock.restart()
        self._timer.start()
        self.setFocus()

    def _show_panel(self, title: str, message: str, paused: bool = False) -> None:
        self.panel.show_choices(title, message, self._best, paused=paused, best_text=wpm_text)
        self._layout_children()

    # Loop -----------------------------------------------------------------

    def _tick(self) -> None:
        dt = min(0.05, self._clock.restart() / 1000)
        self._wiggle = max(0.0, self._wiggle - dt)
        s = self.state
        if s is not None and not self._paused and not s.over:
            self._handle(s.update(dt))
        self.update()

    def _handle(self, events: list[RaceEvent]) -> None:
        for e in events:
            if e.kind == "go":
                self.sounds.play("line")
            elif e.kind == "hit":
                self.sounds.play("click")
            elif e.kind == "miss":
                self.sounds.play("oops")
                self._wiggle = 0.25
            elif e.kind == "rival-finished":
                self.sounds.play("whoosh")
            elif e.kind == "finish":
                self._finished()
        self.typing.update()

    def _finished(self) -> None:
        s = self.state
        if s is None:
            return
        self.sounds.stars(3 if s.won else 1)
        key = s.difficulty.key
        wpm = round(s.wpm(), 1)
        is_best, best = False, self._best.get(key, 0.0)
        if self.record_race is not None:
            is_best, best = self.record_race(key, wpm, s.session.key_stats)
        self._best[key] = best
        title = "You won!" if s.won else f"{RIVAL_NAME} won this time"
        lines = [
            f"<b>{wpm:.0f} WPM</b> · {s.session.accuracy():.0f}% accuracy · "
            f"{s.elapsed:.0f} seconds",
            f"{RIVAL_NAME} went at {s.pace_wpm:.0f} WPM.",
        ]
        if is_best:
            lines.insert(0, "<span style='color:#e08a00'><b>Your fastest race yet!</b></span>")
        if not s.won:
            lines.append("Try Easy, or race again. She gets tired too!")
        self._show_panel(title, "<br>".join(lines) + "<br><br>Race again?")

    # Input ----------------------------------------------------------------

    def focusNextPrevChild(self, next: bool) -> bool:
        return False

    def keyPressEvent(self, event) -> None:
        s = self.state
        if s is None or s.over:
            super().keyPressEvent(event)
            return
        if event.key() == Qt.Key.Key_Escape:
            self._resume() if self._paused else self._pause()
            return
        text = event.text()
        if self._paused or event.isAutoRepeat() or len(text) != 1 or not text.isprintable():
            super().keyPressEvent(event)
            return
        self._handle(s.type(text))

    def changeEvent(self, event) -> None:
        # Pause automatically if the window loses focus mid-race.
        if (
            event.type() == QEvent.Type.ActivationChange
            and not self.isActiveWindow()
            and self.state is not None
            and not self.state.over
            and not self._paused
            and self.isVisible()
        ):
            self._pause()
        super().changeEvent(event)

    def _pause(self) -> None:
        self._paused = True
        self._show_panel("Paused", "Press Esc or click to keep racing.", paused=True)

    def _resume(self) -> None:
        self._paused = False
        self.panel.hide()
        self._clock.restart()
        self.setFocus()

    def _quit(self) -> None:
        self._timer.stop()
        self.state = None
        self.panel.hide()
        self.menu_requested.emit()

    def hideEvent(self, event) -> None:
        self._timer.stop()
        super().hideEvent(event)

    # Layout ---------------------------------------------------------------

    def resizeEvent(self, event) -> None:
        self._layout_children()
        super().resizeEvent(event)

    def _layout_children(self) -> None:
        self.quit_btn.adjustSize()
        self.quit_btn.move(20, (HUD_H - self.quit_btn.height()) // 2)
        self.typing.setGeometry(32, self.height() - LINE_H - 24, self.width() - 64, LINE_H)
        self.panel.adjustSize()
        w = max(self.panel.sizeHint().width(), 520)
        h = self.panel.sizeHint().height()
        self.panel.setGeometry((self.width() - w) // 2, (self.height() - h) // 2, w, h)

    def track_rect(self) -> QRectF:
        """Where the two lanes are drawn, between the top bar and the typing line."""
        top = HUD_H + 30
        bottom = self.height() - LINE_H - 60
        return QRectF(60, top, self.width() - 120, max(120.0, bottom - top))

    # Drawing --------------------------------------------------------------

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        grass = QLinearGradient(0, 0, 0, h)
        grass.setColorAt(0, QColor("#c8f0b4"))
        grass.setColorAt(1, QColor("#9fdc8c"))
        p.fillRect(self.rect(), grass)
        self._draw_flowers(p, w, h)

        track = self.track_rect()
        lane_h = track.height() / 2
        s = self.state
        lanes = (
            (self._player_name, self._player_color, s.player_progress if s else 0.0),
            (RIVAL_NAME, RIVAL_COLOR, s.rival_progress if s else 0.0),
        )
        for i, (name, color, progress) in enumerate(lanes):
            lane = QRectF(track.left(), track.top() + i * lane_h, track.width(), lane_h)
            self._draw_lane(p, lane, name, color, progress, wiggle=i == 0)
        self._draw_finish(p, track)
        self._draw_hud(p, w, s)
        if s is not None and s.countdown and not self._paused:
            self._draw_countdown(p, track, s.countdown)

    def _draw_flowers(self, p: QPainter, w: int, h: int) -> None:
        rng = random.Random(7)  # the same flowers every frame
        p.setPen(Qt.PenStyle.NoPen)
        for _ in range(26):
            x, y = rng.random() * w, HUD_H + rng.random() * (h - HUD_H)
            petal = QColor(rng.choice(("#ffffff", "#ffd93d", "#ff8fc7", "#b39ddb")))
            p.setBrush(petal)
            for k in range(5):
                a = k * 2 * math.pi / 5
                p.drawEllipse(QPointF(x + math.cos(a) * 5, y + math.sin(a) * 5), 4, 4)
            p.setBrush(QColor("#ffb347"))
            p.drawEllipse(QPointF(x, y), 3, 3)

    def _draw_lane(
        self, p: QPainter, lane: QRectF, name: str, color: QColor, progress: float, wiggle: bool
    ) -> None:
        strip = lane.adjusted(0, lane.height() * 0.18, 0, -lane.height() * 0.18)
        p.setPen(QPen(TRACK.darker(115), 2))
        p.setBrush(TRACK)
        p.drawRoundedRect(strip, 14, 14)
        # Dashes along the lane, like a running track.
        p.setPen(QPen(mix(TRACK, QColor("white"), 0.5), 3, Qt.PenStyle.DashLine))
        mid = strip.center().y()
        p.drawLine(QPointF(strip.left() + 20, mid), QPointF(strip.right() - 20, mid))

        size = min(strip.height() * 0.85, 90.0)
        start, end = strip.left() + size * 0.7, strip.right() - size * 0.9
        x = start + (end - start) * progress
        if wiggle and self._wiggle > 0:
            x += math.sin(self._wiggle * 50) * 4
        self._draw_snail(p, QPointF(x, strip.bottom() - size * 0.12), size, color)

        font = QFont(self.font())
        font.setPixelSize(16)
        font.setBold(True)
        p.setFont(font)
        p.setPen(QColor(INK))
        p.drawText(
            QRectF(strip.left() + 8, lane.top(), 300, lane.height() * 0.18),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            name,
        )

    def _draw_snail(self, p: QPainter, foot: QPointF, size: float, color: QColor) -> None:
        """A friendly snail facing right, standing on `foot` (bottom middle)."""
        body = QColor("#ffe0a8")
        x, y = foot.x(), foot.y()
        # Body: a long rounded blob with the head raised on the right.
        path = QPainterPath(QPointF(x - size * 0.7, y))
        path.quadTo(
            QPointF(x - size * 0.75, y - size * 0.2), QPointF(x - size * 0.4, y - size * 0.18)
        )
        path.lineTo(QPointF(x + size * 0.35, y - size * 0.18))
        path.quadTo(
            QPointF(x + size * 0.45, y - size * 0.6), QPointF(x + size * 0.62, y - size * 0.5)
        )
        path.quadTo(QPointF(x + size * 0.75, y - size * 0.3), QPointF(x + size * 0.6, y))
        path.closeSubpath()
        p.setPen(QPen(body.darker(130), 2))
        p.setBrush(body)
        p.drawPath(path)
        # Eye stalks and eyes.
        p.setPen(QPen(body.darker(130), 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        for dx, tip in (
            (0.5, QPointF(x + size * 0.45, y - size * 0.82)),
            (0.62, QPointF(x + size * 0.68, y - size * 0.8)),
        ):
            p.drawLine(QPointF(x + size * dx, y - size * 0.5), tip)
        for tip in (
            QPointF(x + size * 0.45, y - size * 0.82),
            QPointF(x + size * 0.68, y - size * 0.8),
        ):
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("white"))
            p.drawEllipse(tip, size * 0.07, size * 0.07)
            p.setBrush(QColor(INK))
            p.drawEllipse(tip + QPointF(size * 0.02, 0), size * 0.035, size * 0.035)
        # Smile.
        p.setPen(QPen(QColor(INK), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(
            QRectF(x + size * 0.5, y - size * 0.42, size * 0.14, size * 0.12), 200 * 16, 140 * 16
        )
        # Shell: a coloured circle with a spiral.
        centre = QPointF(x - size * 0.12, y - size * 0.48)
        r = size * 0.36
        p.setPen(QPen(color.darker(140), 2.5))
        p.setBrush(color)
        p.drawEllipse(centre, r, r)
        spiral = QPainterPath(centre)
        for i in range(1, 60):
            a = i * 0.25
            rr = r * 0.85 * i / 60
            spiral.lineTo(centre + QPointF(math.cos(a) * rr, math.sin(a) * rr))
        p.setPen(QPen(color.darker(150), 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(spiral)

    def _draw_finish(self, p: QPainter, track: QRectF) -> None:
        x = track.right() - 10
        square = 10.0
        p.setPen(Qt.PenStyle.NoPen)
        rows = int(track.height() / square)
        for row in range(rows):
            for col in range(2):
                p.setBrush(QColor(INK) if (row + col) % 2 else QColor("white"))
                p.drawRect(QRectF(x + col * square, track.top() + row * square, square, square))
        # A little flag on top.
        p.setPen(QPen(QColor(INK), 3))
        p.drawLine(QPointF(x + square, track.top()), QPointF(x + square, track.top() - 34))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#ff6b6b"))
        flag = QPainterPath(QPointF(x + square, track.top() - 34))
        flag.lineTo(QPointF(x + square + 26, track.top() - 26))
        flag.lineTo(QPointF(x + square, track.top() - 18))
        flag.closeSubpath()
        p.drawPath(flag)

    def _draw_hud(self, p: QPainter, w: int, s: RaceState | None) -> None:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 170))
        p.drawRect(QRectF(0, 0, w, HUD_H))
        big = QFont(self.font())
        big.setPixelSize(26)
        big.setBold(True)
        p.setFont(big)
        p.setPen(QColor(INK))
        p.drawText(QRectF(0, 0, w, HUD_H), Qt.AlignmentFlag.AlignCenter, "Snail Race")
        if s is None:
            return
        small = QFont(self.font())
        small.setPixelSize(16)
        p.setFont(small)
        p.setPen(QColor(MUTED))
        speeds = f"{RIVAL_NAME}: {s.pace_wpm:.0f} WPM   ·   You: {s.wpm():.0f} WPM"
        p.drawText(
            QRectF(w - 440, 0, 420, HUD_H),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            speeds + ("   ·   Esc pauses" if w >= 1050 else ""),
        )

    def _draw_countdown(self, p: QPainter, track: QRectF, n: int) -> None:
        font = QFont(self.font())
        font.setPixelSize(96)
        font.setBold(True)
        p.setFont(font)
        p.setPen(QColor(INK))
        p.drawText(track, Qt.AlignmentFlag.AlignCenter, str(n))
