"""Lesson menu: shows each step with stars, locks and a 'keep going' button."""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (QGridLayout, QHBoxLayout, QLabel, QPushButton,
                               QScrollArea, QVBoxLayout, QWidget)

from ..lessons import ALL_STEPS, LESSONS, Lesson, first_unfinished, is_unlocked
from ..storage import Profile
from ..theme import INK

COLUMNS = 3


def star_text(stars: int) -> str:
    return "★" * stars + "☆" * (3 - stars)


class LessonMenuScreen(QWidget):
    step_chosen = Signal(object, int)   # Lesson, step index
    switch_player = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._profile: Profile | None = None
        self._next_button: QPushButton | None = None

        self.avatar = QLabel()
        self.avatar.setFixedSize(64, 64)
        self.avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.greeting = QLabel(objectName="Title")
        switch = QPushButton("Switch player")
        switch.setProperty("role", "secondary")
        switch.clicked.connect(self.switch_player)
        header = QHBoxLayout()
        header.addWidget(self.avatar)
        header.addSpacing(12)
        header.addWidget(self.greeting)
        header.addStretch()
        header.addWidget(switch)

        self.continue_btn = QPushButton()
        self.continue_btn.setMinimumHeight(64)
        self.continue_btn.setStyleSheet("font-size: 24px;")
        self.continue_btn.clicked.connect(self._continue)

        self.lessons_box = QVBoxLayout()
        self.lessons_box.setSpacing(24)
        holder = QWidget()
        holder_layout = QVBoxLayout(holder)
        holder_layout.setContentsMargins(0, 0, 0, 0)
        holder_layout.addLayout(self.lessons_box)
        holder_layout.addStretch()
        self.scroll = scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(holder)
        holder.setAutoFillBackground(False)
        scroll.viewport().setAutoFillBackground(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.addLayout(header)
        layout.addSpacing(18)
        layout.addWidget(self.continue_btn)
        layout.addSpacing(18)
        layout.addWidget(scroll, 1)

    def set_profile(self, profile: Profile) -> None:
        self._profile = profile
        self.avatar.setText(profile.name[:1].upper())
        self.avatar.setStyleSheet(
            f"background: {profile.color}; border-radius: 32px; font-size: 30px;"
            f" font-weight: bold; color: {INK};")
        self.greeting.setText(f"Hi, {profile.name}!")
        self.refresh()

    def refresh(self) -> None:
        if self._profile is None:
            return
        self._next_button = None
        while self.lessons_box.count():
            self.lessons_box.takeAt(0).widget().deleteLater()
        for lesson in LESSONS:
            self.lessons_box.addWidget(self._lesson_section(lesson))
        if first_unfinished(self._profile.stars) is None:
            self.continue_btn.setText("▶  Play again")
        elif all(self._profile.stars(l.step_id(i)) == 0 for l, i in ALL_STEPS):
            self.continue_btn.setText("▶  Start your first lesson!")
        else:
            self.continue_btn.setText("▶  Keep going!")
        # Wait for the layout to settle, then bring the current step into view.
        QTimer.singleShot(0, self._scroll_to_next)

    def _scroll_to_next(self) -> None:
        if self._next_button is not None:
            self.scroll.ensureWidgetVisible(self._next_button, 0, 120)

    def _lesson_section(self, lesson: Lesson) -> QWidget:
        profile = self._profile
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel(lesson.title, objectName="Heading"))
        layout.addWidget(QLabel(lesson.description, objectName="Subtitle"))
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
                btn.clicked.connect(lambda _=False, l=lesson, n=i: self.step_chosen.emit(l, n))
            grid.addWidget(btn, i // COLUMNS, i % COLUMNS)
        layout.addSpacing(6)
        layout.addLayout(grid)
        return section

    def _continue(self) -> None:
        target = first_unfinished(self._profile.stars) or ALL_STEPS[0]
        self.step_chosen.emit(*target)
