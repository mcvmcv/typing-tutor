"""The practice screen: text, keyboard, hands, and the end-of-step result."""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QProgressBar,
                               QPushButton, QVBoxLayout, QWidget)

from ..keyboard import char_name, finger_hint, fingers_for_char
from ..generator import build_lines
from ..lessons import Lesson, next_step
from ..session import StepRun, stars_for
from ..theme import repolish
from ..widgets.hands_view import HandsView
from ..widgets.keyboard_view import KeyboardView
from ..widgets.typing_view import TypingView


class PracticeScreen(QWidget):
    menu_requested = Signal()
    step_completed = Signal(str, float, float, int)  # step_id, wpm, accuracy, stars

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._lesson: Lesson | None = None
        self._index = 0
        self._run: StepRun | None = None
        self._finishing = False

        back = QPushButton("←  Lessons")
        back.setProperty("role", "secondary")
        back.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        back.clicked.connect(self.menu_requested)
        self.title = QLabel(objectName="Heading")
        self.step_count = QLabel(objectName="Subtitle")
        top = QHBoxLayout()
        top.addWidget(back)
        top.addSpacing(16)
        top.addWidget(self.title)
        top.addStretch()
        top.addWidget(self.step_count)

        self.instruction = QLabel(objectName="Instruction", wordWrap=True)
        self.typing = TypingView()
        self.next_line = QLabel(objectName="Stat")
        self.next_line.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.progress = QProgressBar(textVisible=False)
        self.accuracy_label = QLabel(objectName="Stat")
        self.speed_label = QLabel(objectName="Stat")
        stats = QHBoxLayout()
        stats.addWidget(self.progress, 1)
        stats.addSpacing(20)
        stats.addWidget(self.accuracy_label)
        stats.addSpacing(20)
        stats.addWidget(self.speed_label)

        self.hint = QLabel(objectName="Hint")
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

        self._stats_timer = QTimer(self, interval=500, timeout=self._update_stats)

    def start(self, lesson: Lesson, index: int) -> None:
        self._lesson, self._index = lesson, index
        step = lesson.steps[index]
        self._run = StepRun(build_lines(lesson, index))
        self._finishing = False
        self.title.setText(step.title)
        self.instruction.setText(step.instruction)
        self.typing.set_session(self._run.current)
        self.progress.setRange(0, self._run.total_chars)
        self._set_hint(None)
        self._refresh()
        self._stats_timer.start()
        self.setFocus()

    # Keep Tab from moving focus away from the typing area.
    def focusNextPrevChild(self, next: bool) -> bool:
        return False

    def keyPressEvent(self, event) -> None:
        run = self._run
        text = event.text()
        if run is None or self._finishing or event.isAutoRepeat() or len(text) != 1 \
                or not text.isprintable():
            super().keyPressEvent(event)
            return
        s = run.current
        expected = s.expected
        if s.press(text):
            self._set_hint(None)
            if s.finished:
                if run.advance():
                    self.typing.set_session(run.current)
                else:
                    self._finishing = True
                    self._stats_timer.stop()
                    QTimer.singleShot(350, self._show_result)
        else:
            self.keyboard.flash_wrong_char(text)
            if text.isalpha() and text.lower() == expected:
                self._set_hint("Oops! Is Caps Lock on? Press Caps Lock to turn it off.")
            elif text.isalpha() and text.upper() == expected:
                self._set_hint(f"That needs a capital! Hold Shift with your "
                               f"{finger_hint(expected).split('Shift with your ')[-1]}.")
            else:
                self._set_hint(f"Oops! That was {char_name(text)}. "
                               f"Try {char_name(expected)}.")
        self._refresh()

    def _set_hint(self, error: str | None) -> None:
        self._hint_error = error
        self.hint.setProperty("error", error is not None)
        repolish(self.hint)

    def _refresh(self) -> None:
        run = self._run
        s = run.current
        expected = s.expected
        self.keyboard.set_target_char(expected)
        self.hands.set_active_fingers(fingers_for_char(expected) if expected else ())
        self.typing.update()
        self.progress.setValue(run.typed_chars)
        lesson = self._lesson
        self.step_count.setText(
            f"{lesson.title} · step {self._index + 1} of {len(lesson.steps)}"
            f" · line {run.index + 1} of {len(run.lines)}")
        self.next_line.setText("" if run.on_last_line
                               else f"Next:  {run.lines[run.index + 1]}")
        if self._hint_error:
            self.hint.setText(self._hint_error)
        elif expected is None:
            self.hint.setText("All done!")
        else:
            self.hint.setText(f"Press {char_name(expected)} with your {finger_hint(expected)}")
        self._update_stats()

    def _update_stats(self) -> None:
        s = self._run
        if s is None:
            return
        self.accuracy_label.setText(f"Accuracy: {s.accuracy():.0f}%")
        self.speed_label.setText(f"Speed: {s.wpm():.0f} WPM")

    def _show_result(self) -> None:
        s, lesson, index = self._run, self._lesson, self._index
        accuracy, wpm = s.accuracy(), s.wpm()
        stars = stars_for(accuracy)
        self.step_completed.emit(lesson.step_id(index), wpm, accuracy, stars)

        upcoming = next_step(lesson, index)
        dlg = ResultDialog(stars, accuracy, wpm, s.mistakes, has_next=upcoming is not None,
                           parent=self)
        dlg.exec()
        if dlg.choice == "retry":
            self.start(lesson, index)
        elif dlg.choice == "next" and upcoming:
            self.start(*upcoming)
        else:
            self.menu_requested.emit()


class ResultDialog(QDialog):
    MESSAGES = {3: "Amazing!", 2: "Great job!", 1: "Nice work!"}
    SUBTEXT = {
        3: "Super careful typing. You're a typing hero!",
        2: "Really good! A little more practice and you'll get 3 stars.",
        1: "Practice makes perfect. Try again for more stars!",
    }

    def __init__(self, stars: int, accuracy: float, wpm: float, mistakes: int,
                 has_next: bool, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Step complete")
        self.setMinimumWidth(480)
        self.choice = "menu"

        star_label = QLabel(
            f'<span style="color:#ffb300">{"★" * stars}</span>'
            f'<span style="color:#ddd3bf">{"★" * (3 - stars)}</span>')
        star_label.setStyleSheet("font-size: 72px;")
        star_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel(self.MESSAGES[stars], objectName="Title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub = QLabel(self.SUBTEXT[stars], objectName="Subtitle", wordWrap=True)
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        oops = "1 oops" if mistakes == 1 else f"{mistakes} oopses"
        stats = QLabel(f"Accuracy {accuracy:.0f}%   ·   Speed {wpm:.0f} WPM   ·   {oops}",
                       objectName="Stat")
        stats.setAlignment(Qt.AlignmentFlag.AlignCenter)

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
