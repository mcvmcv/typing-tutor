"""Lesson menu: shows each step with stars, locks and a 'keep going' button."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..game import MIN_WORDS, game_words
from ..keyboard import fingers_for_char
from ..lessons import ALL_STEPS, LESSONS, Lesson, first_unfinished, is_unlocked
from ..plays import key_scores, known_keys, weak_keys
from ..storage import Profile
from ..theme import INK, finger_color
from ..ui import clear_layout, frame, label

COLUMNS = 3


def chip_text(key: str) -> str:
    if key.isupper():
        return f"Shift+{key}"
    return key.upper() if key.isalpha() else key


def star_text(stars: int) -> str:
    return "★" * stars + "☆" * (3 - stars)


class LessonMenuScreen(QWidget):
    step_chosen = Signal(object, int)  # Lesson, step index
    switch_player = Signal()
    review_requested = Signal()
    settings_requested = Signal()
    progress_requested = Signal()
    game_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._profile: Profile | None = None
        self._next_button: QPushButton | None = None

        self.avatar = QLabel()
        self.avatar.setFixedSize(64, 64)
        self.avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.greeting = label("", "Title")
        switch = QPushButton("Switch player")
        switch.setProperty("role", "secondary")
        switch.clicked.connect(self.switch_player)
        header = QHBoxLayout()
        header.addWidget(self.avatar)
        header.addSpacing(12)
        header.addWidget(self.greeting)
        header.addStretch()
        progress = QPushButton("My progress")
        progress.setProperty("role", "secondary")
        progress.clicked.connect(self.progress_requested)
        header.addWidget(progress)
        settings = QPushButton("Settings")
        settings.setProperty("role", "secondary")
        settings.clicked.connect(self.settings_requested)
        header.addWidget(settings)
        header.addWidget(switch)

        self.continue_btn = QPushButton()
        self.continue_btn.setMinimumHeight(64)
        self.continue_btn.setStyleSheet("font-size: 24px;")
        self.continue_btn.clicked.connect(self._continue)
        self.game_btn = QPushButton()
        self.game_btn.setMinimumHeight(64)
        self.game_btn.setStyleSheet(
            "QPushButton { background: #8fd3ff; font-size: 20px; }"
            "QPushButton:hover { background: #6cc4fb; }"
            "QPushButton:disabled { background: #ebe4d6; color: #aaa294; font-size: 15px; }"
        )
        self.game_btn.clicked.connect(self.game_requested)
        actions = QHBoxLayout()
        actions.setSpacing(14)
        actions.addWidget(self.continue_btn, 3)
        actions.addWidget(self.game_btn, 1)

        # Tricky keys panel.
        self.tricky_panel = frame("Panel")
        tricky = QHBoxLayout(self.tricky_panel)
        tricky.setContentsMargins(18, 12, 18, 12)
        self.tricky_label = label("", "Instruction")
        self.chips = QHBoxLayout()
        self.chips.setSpacing(8)
        self.review_btn = QPushButton("Practise them")
        self.review_btn.clicked.connect(self.review_requested)
        tricky.addWidget(self.tricky_label)
        tricky.addSpacing(8)
        tricky.addLayout(self.chips)
        tricky.addStretch()
        tricky.addWidget(self.review_btn)

        self.lessons_box = QVBoxLayout()
        self.lessons_box.setSpacing(24)
        holder = QWidget()
        holder_layout = QVBoxLayout(holder)
        holder_layout.setContentsMargins(0, 0, 0, 0)
        holder_layout.addLayout(self.lessons_box)
        holder_layout.addStretch()
        self.scroll_area = scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(holder)
        holder.setAutoFillBackground(False)
        scroll.viewport().setAutoFillBackground(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.addLayout(header)
        layout.addSpacing(18)
        layout.addLayout(actions)
        layout.addSpacing(12)
        layout.addWidget(self.tricky_panel)
        layout.addSpacing(12)
        layout.addWidget(scroll, 1)

    @property
    def profile(self) -> Profile:
        if self._profile is None:
            raise RuntimeError("set_profile() must be called first")
        return self._profile

    def set_profile(self, profile: Profile) -> None:
        self._profile = profile
        self.avatar.setText(profile.name[:1].upper())
        self.avatar.setStyleSheet(
            f"background: {profile.color}; border-radius: 32px; font-size: 30px;"
            f" font-weight: bold; color: {INK};"
        )
        self.greeting.setText(f"Hi, {profile.name}!")
        self.refresh()

    def refresh(self) -> None:
        if self._profile is None:
            return
        self._next_button = None
        clear_layout(self.lessons_box)
        for lesson in LESSONS:
            self.lessons_box.addWidget(self._lesson_section(lesson))
        if first_unfinished(self.profile.stars) is None:
            self.continue_btn.setText("▶  Play again")
        elif all(self.profile.stars(les.step_id(i)) == 0 for les, i in ALL_STEPS):
            self.continue_btn.setText("▶  Start your first lesson!")
        else:
            self.continue_btn.setText("▶  Keep going!")
        self._refresh_tricky()
        unlocked = len(game_words(known_keys(self.profile))) >= MIN_WORDS
        self.game_btn.setEnabled(unlocked)
        self.game_btn.setText("Balloon Pop" if unlocked else "Balloon Pop\nunlocks after step 5")
        # Wait for the layout to settle, then bring the current step into view.
        QTimer.singleShot(0, self._scroll_to_next)

    def _refresh_tricky(self) -> None:
        clear_layout(self.chips)
        profile = self.profile
        if not key_scores(profile):
            # Not enough typing yet to tell which keys are tricky.
            self.tricky_panel.setVisible(False)
            return
        self.tricky_panel.setVisible(True)
        weak = weak_keys(profile)
        if not weak:
            self.tricky_label.setText("No tricky keys right now. Great typing!")
            self.review_btn.setVisible(False)
            return
        self.tricky_label.setText("Your tricky keys:")
        self.review_btn.setVisible(True)
        for key in weak:
            chip = label(chip_text(key), "Chip")
            fingers = fingers_for_char(key)
            color = finger_color(fingers[0]) if fingers else QColor("#ddd5c6")
            chip.setStyleSheet(f"background: {color.name()};")
            self.chips.addWidget(chip)

    def _scroll_to_next(self) -> None:
        if self._next_button is not None:
            self.scroll_area.ensureWidgetVisible(self._next_button, 0, 120)

    def _lesson_section(self, lesson: Lesson) -> QWidget:
        profile = self.profile
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label(lesson.title, "Heading"))
        layout.addWidget(label(lesson.description, "Subtitle"))
        grid = QGridLayout()
        grid.setSpacing(14)
        upcoming = first_unfinished(profile.stars)
        for i, step in enumerate(lesson.steps):
            stars = profile.stars(lesson.step_id(i))
            unlocked = is_unlocked(profile.stars, lesson, i)
            btn = QPushButton()
            btn.setMinimumHeight(92)
            if not unlocked:
                btn.setText(f"{i + 1}. {step.title}\nLocked")
                btn.setEnabled(False)
                btn.setProperty("state", "locked")
            else:
                btn.setText(f"{i + 1}. {step.title}\n{star_text(stars)}")
                if upcoming == (lesson, i):
                    state = "next"
                    self._next_button = btn
                elif stars:
                    state = "done"
                else:
                    state = "open"
                btn.setProperty("state", state)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.clicked.connect(lambda _=False, les=lesson, n=i: self.step_chosen.emit(les, n))
            grid.addWidget(btn, i // COLUMNS, i % COLUMNS)
        layout.addSpacing(6)
        layout.addLayout(grid)
        return section

    def _continue(self) -> None:
        target = first_unfinished(self.profile.stars) or ALL_STEPS[0]
        self.step_chosen.emit(*target)
