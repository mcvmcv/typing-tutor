"""Grown-ups' view: every player's progress side by side."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from PySide6.QtCore import QStandardPaths, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..keyboard import fingers_for_char
from ..progress import Overview, days_ago, overview
from ..storage import BackupError, ImportPlan, Profile, ProfileStore, read_backup
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


def _names(names: list[str]) -> str:
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def import_summary(plan: ImportPlan) -> str:
    """What loading a backup will do, for the confirmation question."""
    lines = []
    if plan.added:
        added = [plan.renamed.get(p.name, p.name) for p in plan.added]
        lines.append(f"New players: {_names(added)}.")
    for old, new in plan.renamed.items():
        lines.append(f"There's already a {old} here, so the one from the backup will be {new}.")
    if plan.replaced:
        names = _names([p.name for p in plan.replaced])
        verb = "is" if len(plan.replaced) == 1 else "are"
        lines.append(
            f"{names} {verb} already here. Their progress will be replaced with the "
            "backup's, which can't be undone."
        )
    return "\n\n".join([*lines, "Load the backup?"])


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
        self.save_btn = QPushButton("Save a backup…")
        self.save_btn.setProperty("role", "secondary")
        self.save_btn.setToolTip("Save everyone's progress to a file, to keep safe or move")
        self.save_btn.clicked.connect(self.save_backup)
        self.load_btn = QPushButton("Load a backup…")
        self.load_btn.setProperty("role", "secondary")
        self.load_btn.setToolTip("Bring in players from a backup file, e.g. from another computer")
        self.load_btn.clicked.connect(self.load_backup)
        top.addWidget(self.save_btn, 0, Qt.AlignmentFlag.AlignTop)
        top.addWidget(self.load_btn, 0, Qt.AlignmentFlag.AlignTop)

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
            self.cards_box.addWidget(
                label(
                    "No players yet. Moving from another computer? "
                    "Use \u201cLoad a backup\u2026\u201d to bring everyone's progress across.",
                    "Subtitle",
                    wrap=True,
                )
            )
        self.save_btn.setEnabled(bool(self.cards))

    # Backups -------------------------------------------------------------

    def save_backup(self) -> None:
        folder = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
        suggested = Path(folder) / f"learn-typing-backup-{date.today().isoformat()}.json"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save a backup", str(suggested), "Learn Typing backup (*.json)"
        )
        if path:
            self.export_to(Path(path))

    def export_to(self, path: Path) -> bool:
        try:
            self.store.export_backup(path)
        except OSError as e:
            QMessageBox.warning(
                self, "Backup not saved", f"The backup couldn't be saved:\n{e.strerror or e}"
            )
            return False
        count = len(self.store.profiles)
        players = "1 player" if count == 1 else f"{count} players"
        QMessageBox.information(
            self,
            "Backup saved",
            f"Saved {players} to:\n{path}\n\n"
            "To move to another computer, copy this file across, then use "
            "\u201cLoad a backup\u2026\u201d there.",
        )
        return True

    def load_backup(self) -> None:
        folder = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
        path, _ = QFileDialog.getOpenFileName(
            self, "Load a backup", folder, "Learn Typing backup (*.json);;All files (*)"
        )
        if path:
            self.import_from(Path(path))

    def import_from(self, path: Path) -> bool:
        """Check a backup, ask before replacing anyone, then load it."""
        try:
            incoming = read_backup(path)
        except BackupError as e:
            QMessageBox.warning(self, "Can't load this backup", str(e))
            return False
        plan = self.store.plan_import(incoming)
        if not self.confirm_import(plan):
            return False
        try:
            self.store.import_profiles(incoming)
        except OSError as e:
            QMessageBox.warning(
                self, "Backup not loaded", f"Progress couldn't be saved:\n{e.strerror or e}"
            )
            return False
        self.refresh()
        return True

    def confirm_import(self, plan: ImportPlan) -> bool:
        answer = QMessageBox.question(self, "Load this backup?", import_summary(plan))
        return answer == QMessageBox.StandardButton.Yes
