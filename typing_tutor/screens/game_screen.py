"""Balloon Pop game screen: drawing, keyboard input and the start/pause/end panel."""
from __future__ import annotations

import math
import random
from collections.abc import Callable

from PySide6.QtCore import QElapsedTimer, QEvent, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetricsF,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from ..game import DIFFICULTIES, ESCAPE_Y, Balloon, Event, GameState
from ..sounds import SoundPlayer
from ..theme import BAD, INK, MUTED, mix
from ..ui import label, timer

BALLOON_COLORS = ("#ff6b6b", "#ffb347", "#ffd93d", "#6bcB77", "#4d96ff",
                  "#b37feb", "#ff8fc7", "#3cc6c0")
TYPED = QColor("#1e7a34")
GRASS_H = 34
HUD_H = 64
POP_ANIM = 0.45

# (difficulty, score, key_stats) -> (is_new_best, best_score)
RecordGame = Callable[[str, int, dict], tuple[bool, int]]


class GamePanel(QFrame):
    """The card shown before a game, when paused, and after game over."""
    difficulty_chosen = Signal(str)
    resume_requested = Signal()
    quit_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GamePanel")
        self.title = label("", "Title")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message = label("", "Instruction", wrap=True)
        self.message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message.setTextFormat(Qt.TextFormat.RichText)

        self.difficulty_row = QHBoxLayout()
        self.difficulty_buttons = {}
        for key, diff in DIFFICULTIES.items():
            btn = QPushButton(diff.label)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setMinimumWidth(120)
            btn.clicked.connect(lambda _=False, k=key: self.difficulty_chosen.emit(k))
            self.difficulty_buttons[key] = btn
            self.difficulty_row.addWidget(btn)

        self.resume = QPushButton("Keep playing")
        self.resume.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.resume.clicked.connect(self.resume_requested)
        self.quit = QPushButton("Back to lessons")
        self.quit.setProperty("role", "secondary")
        self.quit.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.quit.clicked.connect(self.quit_requested)
        bottom = QHBoxLayout()
        bottom.addStretch()
        bottom.addWidget(self.quit)
        bottom.addWidget(self.resume)
        bottom.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 28, 36, 28)
        layout.setSpacing(14)
        layout.addWidget(self.title)
        layout.addWidget(self.message)
        layout.addLayout(self.difficulty_row)
        layout.addLayout(bottom)

    def show_choices(self, title: str, message: str, best: dict[str, int],
                     paused: bool = False) -> None:
        self.title.setText(title)
        self.message.setText(message)
        for key, btn in self.difficulty_buttons.items():
            label = DIFFICULTIES[key].label
            btn.setText(f"{label}\nBest {best[key]}" if best.get(key) else label)
            btn.setVisible(not paused)
        self.resume.setVisible(paused)
        self.adjustSize()
        self.show()
        self.raise_()


class GameScreen(QWidget):
    menu_requested = Signal()

    def __init__(self, sounds: SoundPlayer, parent=None):
        super().__init__(parent)
        self.sounds = sounds
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.record_game: RecordGame | None = None
        self._words: list[str] = []
        self._best: dict[str, int] = {}
        self.state: GameState | None = None
        self._paused = False
        self._points: dict[int, int] = {}       # id(balloon) -> points for pop label
        self._shake = 0.0                       # brief wobble when a key is wrong
        self._clouds = [(random.random(), 0.12 + 0.25 * random.random(),
                         0.6 + 0.6 * random.random()) for _ in range(5)]
        self._scenery_time = 0.0

        self.quit_btn = QPushButton("←  Lessons", self)
        self.quit_btn.setProperty("role", "secondary")
        self.quit_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.quit_btn.clicked.connect(self._quit)

        self.panel = GamePanel(self)
        self.panel.difficulty_chosen.connect(self.start_game)
        self.panel.resume_requested.connect(self._resume)
        self.panel.quit_requested.connect(self._quit)

        self._clock = QElapsedTimer()
        self._timer = timer(self, 16, self._tick)

    # Setup ----------------------------------------------------------------

    def open(self, words: list[str], best: dict[str, int]) -> None:
        """Show the start panel for a player."""
        self._words = words
        self._best = dict(best)
        self.state = None
        self._paused = False
        self.panel.show_choices(
            "Balloon Pop!",
            "Type the word on a balloon to pop it.<br>"
            "Don't let <b>3 balloons</b> float away!",
            self._best)
        self._timer.start()          # keep the clouds drifting behind the panel
        self._clock.restart()
        self.setFocus()
        self._layout_children()

    def start_game(self, difficulty: str) -> None:
        self.state = GameState(DIFFICULTIES[difficulty], self._words)
        self._points.clear()
        self._paused = False
        self.panel.hide()
        self._clock.restart()
        self._timer.start()
        self.setFocus()

    # Loop -----------------------------------------------------------------

    def _tick(self) -> None:
        dt = min(0.05, self._clock.restart() / 1000)
        self._scenery_time += dt
        self._shake = max(0.0, self._shake - dt)
        s = self.state
        if s is not None and not self._paused:
            if s.over:
                s.time += dt          # let the last animations finish
            else:
                self._handle(s.update(dt))
        self.update()

    def _handle(self, events: list[Event]) -> None:
        for e in events:
            if e.kind == "hit":
                self.sounds.play("click")
            elif e.kind == "miss":
                self.sounds.play("oops")
                self._shake = 0.2
            elif e.kind == "pop":
                self.sounds.play("pop")
                self._points[id(e.balloon)] = e.points
            elif e.kind == "level":
                self.sounds.play("line")
            elif e.kind == "escape":
                self.sounds.play("whoosh")
            elif e.kind == "over":
                self.sounds.play("gameover")
                QTimer.singleShot(900, self._game_over)

    def _game_over(self) -> None:
        s = self.state
        if s is None:
            return
        key = s.difficulty.key
        is_best, best_score = (False, self._best.get(key, 0))
        if self.record_game is not None:
            is_best, best_score = self.record_game(key, s.score, s.key_stats)
        self._best[key] = best_score
        words = "1 balloon" if s.popped == 1 else f"{s.popped} balloons"
        lines = [f"You popped <b>{words}</b> and scored <b>{s.score}</b> points.",
                 f"Level {s.level} · {s.wpm():.0f} WPM"]
        if is_best:
            lines.insert(0, "<span style='color:#e08a00'><b>New best score!</b></span>")
        self.panel.show_choices("Game over", "<br>".join(lines) + "<br><br>Play again?",
                                self._best)
        self._layout_children()

    # Input ----------------------------------------------------------------

    def focusNextPrevChild(self, next: bool) -> bool:
        return False

    def keyPressEvent(self, event) -> None:
        s = self.state
        if s is None or s.over:
            super().keyPressEvent(event)
            return
        if event.key() == Qt.Key.Key_Escape:
            if self._paused:
                self._resume()
            else:
                self._pause()
            return
        text = event.text()
        if self._paused or event.isAutoRepeat() or len(text) != 1 \
                or not text.isprintable() or text == " ":
            super().keyPressEvent(event)
            return
        self._handle(s.type(text))

    def changeEvent(self, event) -> None:
        # Pause automatically if the window loses focus mid-game.
        if (event.type() == QEvent.Type.ActivationChange and not self.isActiveWindow()
                and self.state is not None and not self.state.over
                and not self._paused and self.isVisible()):
            self._pause()
        super().changeEvent(event)

    def _pause(self) -> None:
        self._paused = True
        self.panel.show_choices("Paused", "Press Esc or click to keep playing.",
                                self._best, paused=True)
        self._layout_children()

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
        self.panel.adjustSize()
        w = max(self.panel.sizeHint().width(), 520)
        h = self.panel.sizeHint().height()
        self.panel.setGeometry((self.width() - w) // 2, (self.height() - h) // 2, w, h)

    # Drawing --------------------------------------------------------------

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        sky = QLinearGradient(0, 0, 0, h)
        sky.setColorAt(0, QColor("#8fd3ff"))
        sky.setColorAt(1, QColor("#eaf8ff"))
        p.fillRect(self.rect(), sky)
        self._draw_clouds(p, w, h)

        play = QRectF(0, HUD_H, w, h - HUD_H - GRASS_H)
        s = self.state
        if s is not None:
            for b in sorted(s.balloons, key=lambda b: b is s.target):
                self._draw_balloon(p, b, play, s)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#9be7a0"))
        p.drawRect(QRectF(0, h - GRASS_H, w, GRASS_H))
        p.setBrush(QColor("#6bcB77"))
        p.drawRect(QRectF(0, h - GRASS_H, w, 5))

        self._draw_hud(p, w, s)

    def _draw_clouds(self, p: QPainter, w: int, h: int) -> None:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 210))
        for x0, y, size in self._clouds:
            x = ((x0 + self._scenery_time * 0.008 * size) % 1.3 - 0.15) * w
            r = 34 * size
            cy = HUD_H + y * (h - HUD_H)
            for dx, dy, k in ((0, 0, 1.0), (r * 0.9, -r * 0.3, 1.2), (r * 1.9, 0, 0.9)):
                p.drawEllipse(QPointF(x + dx, cy + dy), r * k, r * k * 0.75)

    def _balloon_font(self) -> QFont:
        font = QFont(self.font())
        font.setPixelSize(24)
        font.setBold(True)
        return font

    def _draw_balloon(self, p: QPainter, b: Balloon, play: QRectF, s: GameState) -> None:
        font = self._balloon_font()
        fm = QFontMetricsF(font)
        tw = fm.horizontalAdvance(b.word)
        rx = max(40.0, tw / 2 + 18)
        ry = max(rx * 1.15, 52.0)
        cx = b.x * play.width()
        cy = play.top() + b.y * play.height()
        escaped = not b.active and b.y < ESCAPE_Y
        if not b.active and not escaped:
            self._draw_pop(p, b, cx, cy, rx, s)
            return
        if b is s.target and self._shake > 0:
            cx += math.sin(self._shake * 60) * 5
        color = QColor(BALLOON_COLORS[b.color % len(BALLOON_COLORS)])

        # String, gently swaying.
        sway = math.sin(s.time * 2 + b.x * 10) * 8
        string = QPainterPath(QPointF(cx, cy + ry + 6))
        string.cubicTo(QPointF(cx + sway, cy + ry + 30), QPointF(cx - sway, cy + ry + 50),
                       QPointF(cx + sway * 0.5, cy + ry + 70))
        p.setPen(QPen(QColor("#7a7062"), 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(string)

        # Knot.
        knot = QPainterPath(QPointF(cx - 7, cy + ry + 8))
        knot.lineTo(QPointF(cx + 7, cy + ry + 8))
        knot.lineTo(QPointF(cx, cy + ry - 2))
        knot.closeSubpath()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color.darker(115))
        p.drawPath(knot)

        # Body with a soft highlight.
        grad = QRadialGradient(QPointF(cx - rx * 0.35, cy - ry * 0.4), rx * 1.6)
        grad.setColorAt(0, mix(color, QColor("white"), 0.55))
        grad.setColorAt(0.5, color)
        grad.setColorAt(1, color.darker(112))
        if b is s.target:
            p.setPen(QPen(QColor("white"), 5))
        else:
            p.setPen(QPen(color.darker(125), 1.5))
        p.setBrush(grad)
        p.drawEllipse(QPointF(cx, cy), rx, ry)

        # Word: typed letters green, the rest dark.
        p.setFont(font)
        x = cx - tw / 2
        baseline = cy + (fm.ascent() - fm.descent()) / 2
        done, rest = b.word[:b.typed], b.word[b.typed:]
        p.setPen(TYPED)
        p.drawText(QPointF(x, baseline), done)
        p.setPen(QColor(INK))
        p.drawText(QPointF(x + fm.horizontalAdvance(done), baseline), rest)
        if b is s.target and rest:
            nx = x + fm.horizontalAdvance(done)
            p.setPen(QPen(QColor(INK), 2.5))
            p.drawLine(QPointF(nx, baseline + 5),
                       QPointF(nx + fm.horizontalAdvance(rest[0]), baseline + 5))

    def _draw_pop(self, p: QPainter, b: Balloon, cx: float, cy: float, rx: float,
                  s: GameState) -> None:
        age = min(POP_ANIM, s.time - (b.popped_at or s.time))
        k = age / POP_ANIM
        alpha = int(255 * (1 - k))
        color = QColor(BALLOON_COLORS[b.color % len(BALLOON_COLORS)])
        color.setAlpha(alpha)
        pen = QPen(color, 4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        for i in range(10):
            a = i * math.pi / 5
            r1, r2 = rx * (0.4 + k), rx * (0.7 + 1.2 * k)
            p.drawLine(QPointF(cx + math.cos(a) * r1, cy + math.sin(a) * r1),
                       QPointF(cx + math.cos(a) * r2, cy + math.sin(a) * r2))
        points = self._points.get(id(b))
        if points:
            font = self._balloon_font()
            p.setFont(font)
            ink = QColor(INK)
            ink.setAlpha(alpha)
            p.setPen(ink)
            p.drawText(QRectF(cx - 60, cy - 20 - 50 * k, 120, 40),
                       Qt.AlignmentFlag.AlignCenter, f"+{points}")

    def _draw_hud(self, p: QPainter, w: int, s: GameState | None) -> None:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 170))
        p.drawRect(QRectF(0, 0, w, HUD_H))
        if s is None:
            return
        big = QFont(self.font())
        big.setPixelSize(26)
        big.setBold(True)
        small = QFont(self.font())
        small.setPixelSize(16)
        p.setFont(big)
        p.setPen(QColor(INK))
        p.drawText(QRectF(0, 0, w, HUD_H), Qt.AlignmentFlag.AlignCenter, f"Score {s.score}")
        p.setFont(small)
        p.setPen(QColor(MUTED))
        p.drawText(QRectF(w - 480, 0, 300, HUD_H),
                   Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                   f"Level {s.level}   ·   Esc pauses")
        for i in range(3):
            self._draw_heart(p, QPointF(w - 150 + i * 42, HUD_H / 2), 15, i < s.lives)

    def _draw_heart(self, p: QPainter, c: QPointF, r: float, full: bool) -> None:
        path = QPainterPath(QPointF(c.x(), c.y() + r))
        path.cubicTo(QPointF(c.x() - r * 1.6, c.y() - r * 0.2),
                     QPointF(c.x() - r * 0.7, c.y() - r * 1.4),
                     QPointF(c.x(), c.y() - r * 0.5))
        path.cubicTo(QPointF(c.x() + r * 0.7, c.y() - r * 1.4),
                     QPointF(c.x() + r * 1.6, c.y() - r * 0.2),
                     QPointF(c.x(), c.y() + r))
        if full:
            p.setPen(QPen(QColor(BAD).darker(120), 1.5))
            p.setBrush(QColor(BAD))
        else:
            p.setPen(QPen(QColor("#c9bfae"), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
