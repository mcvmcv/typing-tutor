"""Grown-ups' view: every player's progress side by side."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..keyboard import fingers_for_char
from ..progress import Overview, days_ago, overview
from ..storage import Profile, ProfileStore
from ..theme import INK, finger_color
from ..ui import clear_layout, label
from .menu import chip_text

STATS = (
    "Steps done",
    "Stars",
    "Best speed",
    "Accuracy",
    "Last practised",
    "This week",
    "Balloon Pop",
)


def stat_values(o: Overview, now: datetime | None = None) -> list[str]:
    """The numbers under each heading in STATS."""
    s = o.summary
    return [
        f"{s.steps_done} of {s.total_steps}",
        f"{s.stars} of {s.max_stars}",
        f"{s.best_wpm:.0f} WPM" if s.best_wpm else "–",
        f"{s.recent_accuracy:.0f}%" if s.recent_accuracy is not None else "–",
        days_ago(o.last_practised, now),
        "1 step" if o.steps_this_week == 1 else f"{o.steps_this_week} steps",
        str(o.game_best) if o.game_best else "–",
    ]


def avatar(profile: Profile, size: int = 52) -> QLabel:
    dot = label(profile.name[:1].upper())
    dot.setFixedSize(size, size)
    dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
    dot.setStyleSheet(
        f"background: {profile.color}; color: {INK}; border-radius: {size // 2}px;"
        f" font-size: {size // 2}px; font-weight: bold; border: 3px solid white;"
    )
    return dot


class PlayerCard(QFrame):
    details_requested = Signal(str)

    def __init__(self, profile: Profile, now: datetime | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("Tile")
        o = overview(profile, now)

        name = label(profile.name, "Heading")
        self.up_to = label(f"Up to: {o.up_to}", "Subtitle", wrap=True)
        names = QVBoxLayout()
        names.setSpacing(0)
        names.addWidget(name)
        names.addWidget(self.up_to)
        details = QPushButton("See progress →")
        details.setProperty("role", "secondary")
        details.clicked.connect(lambda: self.details_requested.emit(profile.id))
        top = QHBoxLayout()
        top.setSpacing(14)
        top.addWidget(avatar(profile))
        top.addLayout(names, 1)
        top.addWidget(details, 0, Qt.AlignmentFlag.AlignTop)

        stats = QGridLayout()
        stats.setHorizontalSpacing(24)
        stats.setVerticalSpacing(0)
        self.values: dict[str, str] = {}
        for col, (title, value) in enumerate(zip(STATS, stat_values(o, now), strict=True)):
            self.values[title] = value
            stats.addWidget(label(title, "Stat"), 0, col)
            stats.addWidget(label(value, "CardValue"), 1, col)
            stats.setColumnStretch(col, 1)

        tricky = QHBoxLayout()
        tricky.setSpacing(8)
        tricky.addWidget(label("Tricky keys:", "Stat"))
        self.tricky_text = ""
        if o.tricky_keys is None:
            self.tricky_text = "not enough typing yet to tell"
        elif not o.tricky_keys:
            self.tricky_text = "none right now"
        if self.tricky_text:
            tricky.addWidget(label(self.tricky_text, "Stat"))
        for key in o.tricky_keys or []:
            chip = label(chip_text(key), "SmallChip")
            fingers = fingers_for_char(key)
            color = finger_color(fingers[0]) if fingers else QColor("#ddd5c6")
            chip.setStyleSheet(f"background: {color.name()};")
            tricky.addWidget(chip)
        tricky.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)
        layout.addLayout(top)
        layout.addLayout(stats)
        layout.addLayout(tricky)


class ParentScreen(QWidget):
    back_requested = Signal()
    details_requested = Signal(str)

    def __init__(self, store: ProfileStore, parent=None):
        super().__init__(parent)
        self.store = store

        back = QPushButton("←  Players")
        back.setProperty("role", "secondary")
        back.clicked.connect(self.back_requested)
        titles = QVBoxLayout()
        titles.setSpacing(0)
        titles.addWidget(label("For grown-ups", "Title"))
        titles.addWidget(label("How everyone is getting on", "Subtitle"))
        top = QHBoxLayout()
        top.addWidget(back, 0, Qt.AlignmentFlag.AlignTop)
        top.addSpacing(16)
        top.addLayout(titles)
        top.addStretch()

        self.cards_box = QVBoxLayout()
        self.cards_box.setSpacing(14)
        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(0, 0, 8, 0)
        inner_layout.addLayout(self.cards_box)
        inner_layout.addStretch()
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(inner)
        inner.setAutoFillBackground(False)
        self.scroll_area.viewport().setAutoFillBackground(False)

        note = label(
            "Accuracy is the average of the last 10 steps. Tricky keys are the ones "
            "that are missed most or take longest, from recent typing.",
            "Subtitle",
            wrap=True,
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 24, 40, 24)
        layout.setSpacing(16)
        layout.addLayout(top)
        layout.addWidget(self.scroll_area, 1)
        layout.addWidget(note)
        self.cards: list[PlayerCard] = []

    def refresh(self, now: datetime | None = None) -> None:
        clear_layout(self.cards_box)
        self.cards = []
        for profile in self.store.profiles:
            card = PlayerCard(profile, now)
            card.details_requested.connect(self.details_requested)
            self.cards_box.addWidget(card)
            self.cards.append(card)
        if not self.cards:
            self.cards_box.addWidget(label("No players yet.", "Subtitle"))
