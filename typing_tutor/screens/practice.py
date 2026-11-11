"""The practice screen: text, keyboard, hands, and the end-of-step result."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..keyboard import char_name, finger_hint, fingers_for_char
from ..plays import Play
from ..session import StepRun, stars_for
from ..sounds import SoundPlayer
from ..theme import repolish
from ..ui import label, timer
from ..widgets.hands_view import MIN_HEIGHT as HANDS_MIN_HEIGHT
from ..widgets.hands_view import HandsView
from ..widgets.keyboard_view import MIN_HEIGHT as KEYBOARD_MIN_HEIGHT
from ..widgets.keyboard_view import KeyboardView
from ..widgets.typing_view import BASE_HEIGHT, TypingView


@dataclass
class StepResult:
    step_id: str
    wpm: float
    accuracy: float
    stars: int
    key_stats: dict


class PracticeScreen(QWidget):
    menu_requested = Signal()
    step_completed = Signal(object)  # StepResult
    sound_toggled = Signal(bool)

    def __init__(self, sounds: SoundPlayer, parent=None):
        super().__init__(parent)
        self.sounds = sounds
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._play: Play | None = None
        self._run: StepRun | None = None
        self._finishing = False

        back = QPushButton("←  Lessons")
        back.setProperty("role", "secondary")
        back.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        back.clicked.connect(self.menu_requested)
        self.title = label("", "Heading")
        self.step_count = label("", "Subtitle")
        top = QHBoxLayout()
        top.addWidget(back)
        top.addSpacing(16)
        top.addWidget(self.title)
        top.addStretch()
        top.addWidget(self.step_count)
        top.addSpacing(12)
        self.sound_btn = QPushButton()
        self.sound_btn.setProperty("role", "secondary")
        self.sound_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.sound_btn.clicked.connect(self._toggle_sound)
        top.addWidget(self.sound_btn)

        self.instruction = label("", "Instruction", wrap=True)
        self.typing = TypingView()
        self.next_line = label("", "Stat")
        self.next_line.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.progress = QProgressBar(textVisible=False)
        self.accuracy_label = label("", "Stat")
        self.speed_label = label("", "Stat")
        stats = QHBoxLayout()
        stats.addWidget(self.progress, 1)
        stats.addSpacing(20)
        stats.addWidget(self.accuracy_label)
        stats.addSpacing(20)
        stats.addWidget(self.speed_label)

        self.hint = label("", "Hint")
        self.hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.keyboard = KeyboardView()
        self.hands = HandsView()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 20, 32, 16)
        layout.setSpacing(12)
        layout.addLayout(top)
        layout.addWidget(self.instruction)
        layout.addWidget(self.typing)
        layout.addWidget(self.next_line)
        layout.addLayout(stats)
        layout.addWidget(self.hint)
        layout.addWidget(self.keyboard, 5)
        layout.addWidget(self.hands, 2)

        self._stats_timer = timer(self, 500, self._update_stats)
        self.text_scale = 1.0

    def set_text_scale(self, scale: float) -> None:
        """Make the typing line, instruction and hint bigger (1.0 is normal)."""
        self.text_scale = scale
        self.typing.set_scale(scale)
        for widget, size in ((self.instruction, 20), (self.hint, 20), (self.next_line, 17)):
            widget.setStyleSheet(f"font-size: {round(size * scale)}px;")
        # Make room for the bigger text by letting the pictures below shrink,
        # so everything still fits in the smallest window.
        extra = (BASE_HEIGHT + 75) * (scale - 1)
        self.keyboard.setMinimumHeight(max(120, round(KEYBOARD_MIN_HEIGHT - extra * 0.45)))
        self.hands.setMinimumHeight(max(70, round(HANDS_MIN_HEIGHT - extra * 0.55)))

    def start(self, play: Play) -> None:
        self._play = play
        self._run = StepRun(play.make_lines())
        self._finishing = False
        self.title.setText(play.title)
        self.instruction.setText(play.instruction)
        self.typing.set_session(self._run.current)
        self.progress.setRange(0, self._run.total_chars)
        self._set_hint(None)
        self._update_sound_button()
        self._refresh()
        self._stats_timer.start()
        self.setFocus()

    def _current(self) -> tuple[StepRun, Play]:
        if self._run is None or self._play is None:
            raise RuntimeError("start() must be called first")
        return self._run, self._play

    # Keep Tab from moving focus away from the typing area.
    def focusNextPrevChild(self, next: bool) -> bool:
        return False

    def keyPressEvent(self, event) -> None:
        run = self._run
        text = event.text()
        if (
            run is None
            or self._finishing
            or event.isAutoRepeat()
            or len(text) != 1
            or not text.isprintable()
        ):
            super().keyPressEvent(event)
            return
        s = run.current
        expected = s.expected
        if expected is None:
            return
        if s.press(text):
            self._set_hint(None)
            if not s.finished:
                self.sounds.play("click")
            else:
                if run.advance():
                    self.sounds.play("line")
                    self.typing.set_session(run.current)
                else:
                    self._finishing = True
                    self._stats_timer.stop()
                    QTimer.singleShot(350, self._show_result)
        else:
            self.sounds.play("oops")
            self.keyboard.flash_wrong_char(text)
            if text.isalpha() and text.lower() == expected:
                self._set_hint("Oops! Is Caps Lock on? Press Caps Lock to turn it off.")
            elif text.isalpha() and text.upper() == expected:
                self._set_hint(
                    f"That needs a capital! Hold Shift with your "
                    f"{finger_hint(expected).split('Shift with your ')[-1]}."
                )
            else:
                self._set_hint(f"Oops! That was {char_name(text)}. Try {char_name(expected)}.")
        self._refresh()

    def _toggle_sound(self) -> None:
        self.sounds.enabled = not self.sounds.enabled
        self._update_sound_button()
        self.sound_toggled.emit(self.sounds.enabled)

    def _update_sound_button(self) -> None:
        self.sound_btn.setText("Sound: on" if self.sounds.enabled else "Sound: off")

    def _set_hint(self, error: str | None) -> None:
        self._hint_error = error
        self.hint.setProperty("error", error is not None)
        repolish(self.hint)

    def _refresh(self) -> None:
        run, play = self._current()
        s = run.current
        expected = s.expected
        self.keyboard.set_target_char(expected)
        self.hands.set_active_fingers(fingers_for_char(expected) if expected else ())
        self.typing.update()
        self.progress.setValue(run.typed_chars)
        self.step_count.setText(f"{play.header} · line {run.index + 1} of {len(run.lines)}")
        self.next_line.setText("" if run.on_last_line else f"Next:  {run.lines[run.index + 1]}")
        if self._hint_error:
            self.hint.setText(self._hint_error)
        elif expected is None:
            self.hint.setText("All done!")
        else:
            self.hint.setText(f"Press {char_name(expected)} with your {finger_hint(expected)}")
        self._update_stats()

    def _update_stats(self) -> None:
        if self._run is None or self._play is None:
            return
        s = self._run
        self.accuracy_label.setText(f"Accuracy: {s.accuracy():.0f}%")
        goal = self._play.speed_goal
        if goal:
            self.speed_label.setText(f"Speed: {s.wpm():.0f} / {goal:.0f} WPM")
        else:
            self.speed_label.setText(f"Speed: {s.wpm():.0f} WPM")

    def _show_result(self) -> None:
        run, play = self._current()
        accuracy, wpm = run.accuracy(), run.wpm()
        stars = stars_for(accuracy, wpm, play.speed_goal)
        self.step_completed.emit(StepResult(play.step_id, wpm, accuracy, stars, run.key_stats()))

        self.sounds.stars(stars)
        upcoming = play.next_play() if play.next_play else None
        dlg = ResultDialog(
            stars,
            accuracy,
            wpm,
            run.mistakes,
            play.speed_goal,
            has_next=upcoming is not None,
            parent=self,
        )
        dlg.exec()
        if dlg.choice == "retry":
            self.start(play)
        elif dlg.choice == "next" and upcoming:
            self.start(upcoming)
        else:
            self.menu_requested.emit()


class ResultDialog(QDialog):
    MESSAGES: ClassVar[dict[int, str]] = {3: "Amazing!", 2: "Great job!", 1: "Nice work!"}
    SUBTEXT: ClassVar[dict[int, str]] = {
        3: "Super careful typing. You're a typing hero!",
        2: "Really good! A little more practice and you'll get 3 stars.",
        1: "Practice makes perfect. Try again for more stars!",
    }

    def __init__(
        self,
        stars: int,
        accuracy: float,
        wpm: float,
        mistakes: int,
        speed_goal: float,
        has_next: bool,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Step complete")
        self.setMinimumWidth(480)
        self.choice = "menu"

        star_label = QLabel(
            f'<span style="color:#ffb300">{"★" * stars}</span>'
            f'<span style="color:#ddd3bf">{"★" * (3 - stars)}</span>'
        )
        star_label.setStyleSheet("font-size: 72px;")
        star_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = label(self.MESSAGES[stars], "Title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub = label(self.SUBTEXT[stars], "Subtitle", wrap=True)
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        oops = {0: "no oopses", 1: "1 oops"}.get(mistakes, f"{mistakes} oopses")
        stats = label(f"Accuracy {accuracy:.0f}%   ·   Speed {wpm:.0f} WPM   ·   {oops}", "Stat")
        stats.setAlignment(Qt.AlignmentFlag.AlignCenter)
        goal_label = label("", "Stat")
        goal_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if speed_goal:
            if wpm >= speed_goal:
                goal_label.setText(f"Speed goal {speed_goal:.0f} WPM: reached!")
            else:
                goal_label.setText(f"Speed goal {speed_goal:.0f} WPM: {speed_goal - wpm:.0f} to go")
            if stars < 3 and accuracy >= 95:
                sub.setText("Super careful! Now try going a little faster for 3 stars.")
        goal_label.setVisible(bool(speed_goal))

        buttons = QHBoxLayout()
        menu = self._button("Lessons", "menu", secondary=True)
        retry = self._button("Try again", "retry", secondary=has_next)
        buttons.addWidget(menu)
        buttons.addStretch()
        buttons.addWidget(retry)
        if has_next:
            nxt = self._button("Next step  →", "next")
            nxt.setDefault(True)
            buttons.addWidget(nxt)
        else:
            retry.setDefault(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 24)
        layout.addWidget(star_label)
        layout.addWidget(title)
        layout.addWidget(sub)
        layout.addSpacing(8)
        layout.addWidget(stats)
        layout.addWidget(goal_label)
        layout.addSpacing(20)
        layout.addLayout(buttons)

    def _button(self, text: str, choice: str, secondary: bool = False) -> QPushButton:
        btn = QPushButton(text)
        # No keyboard focus, so a stray Space right after finishing can't pick
        # an option by accident. Enter still triggers the default button.
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        if secondary:
            btn.setProperty("role", "secondary")
        btn.clicked.connect(lambda: self._choose(choice))
        return btn

    def _choose(self, choice: str) -> None:
        self.choice = choice
        self.accept()
