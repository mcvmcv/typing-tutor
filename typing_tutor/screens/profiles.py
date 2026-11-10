"""'Who's typing today?' screen and the new-player dialog."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QButtonGroup, QDialog, QGridLayout, QHBoxLayout,
                               QLabel, QLineEdit, QMenu, QMessageBox, QPushButton,
                               QVBoxLayout, QWidget)

from ..storage import Profile, ProfileStore
from ..theme import AVATAR_COLORS, INK

MAX_NAME = 12
COLUMNS = 4


class ProfileScreen(QWidget):
    profile_chosen = Signal(str)

    def __init__(self, store: ProfileStore, parent=None):
        super().__init__(parent)
        self.store = store

        title = QLabel("Who's typing today?", objectName="Title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_hint = QLabel("Make a player to get started!", objectName="Subtitle")
        self.empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.grid = QGridLayout()
        self.grid.setSpacing(28)
        grid_box = QHBoxLayout()
        grid_box.addStretch()
        grid_box.addLayout(self.grid)
        grid_box.addStretch()

        new_btn = QPushButton("+  New player")
        new_btn.clicked.connect(self._new_player)
        new_row = QHBoxLayout()
        new_row.addStretch()
        new_row.addWidget(new_btn)
        new_row.addStretch()

        tip = QLabel("Tip: right-click a player to remove them.", objectName="Subtitle")
        tip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tip = tip

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 50, 40, 30)
        layout.addWidget(title)
        layout.addSpacing(30)
        layout.addWidget(self.empty_hint)
        layout.addLayout(grid_box)
        layout.addSpacing(30)
        layout.addLayout(new_row)
        layout.addStretch()
        layout.addWidget(tip)
        self.refresh()

    def refresh(self) -> None:
        while self.grid.count():
            self.grid.takeAt(0).widget().deleteLater()
        for i, profile in enumerate(self.store.profiles):
            self.grid.addWidget(self._profile_button(profile), i // COLUMNS, i % COLUMNS)
        has_profiles = bool(self.store.profiles)
        self.empty_hint.setVisible(not has_profiles)
        self.tip.setVisible(has_profiles)

    def _profile_button(self, profile: Profile) -> QPushButton:
        btn = QPushButton(profile.name)
        btn.setFixedSize(160, 160)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            f"QPushButton {{ background: {profile.color}; border-radius: 80px;"
            f" font-size: 22px; color: {INK}; border: 4px solid white; }}"
            f"QPushButton:hover {{ border: 4px solid {INK}; }}")
        btn.clicked.connect(lambda: self.profile_chosen.emit(profile.id))
        btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        btn.customContextMenuRequested.connect(
            lambda pos: self._context_menu(btn, pos, profile))
        return btn

    def _context_menu(self, btn: QPushButton, pos, profile: Profile) -> None:
        menu = QMenu(self)
        remove = menu.addAction(f"Remove {profile.name}…")
        if menu.exec(btn.mapToGlobal(pos)) is remove:
            answer = QMessageBox.question(
                self, "Remove player",
                f"Remove {profile.name} and all their progress?\nThis can't be undone.")
            if answer == QMessageBox.StandardButton.Yes:
                self.store.delete(profile.id)
                self.refresh()

    def _new_player(self) -> None:
        dlg = NewPlayerDialog(self.store, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            profile = self.store.add(dlg.name(), dlg.color())
            self.refresh()
            self.profile_chosen.emit(profile.id)


class NewPlayerDialog(QDialog):
    def __init__(self, store: ProfileStore, parent=None):
        super().__init__(parent)
        self.store = store
        self.setWindowTitle("New player")
        self.setMinimumWidth(460)

        heading = QLabel("What's your name?", objectName="Heading")
        self.name_edit = QLineEdit(placeholderText="Your name", maxLength=MAX_NAME)
        self.name_edit.textChanged.connect(self._validate)
        self.error = QLabel("", objectName="Subtitle")

        color_heading = QLabel("Pick your colour", objectName="Heading")
        self.colors = QButtonGroup(self)
        swatches = QHBoxLayout()
        for i, color in enumerate(AVATAR_COLORS):
            sw = QPushButton()
            sw.setCheckable(True)
            sw.setFixedSize(44, 44)
            sw.setStyleSheet(
                f"QPushButton {{ background: {color}; border-radius: 22px;"
                f" border: 3px solid white; padding: 0; }}"
                f"QPushButton:checked {{ border: 4px solid {INK}; }}")
            self.colors.addButton(sw, i)
            swatches.addWidget(sw)
        used = {p.color for p in store.profiles}
        first_free = next((i for i, c in enumerate(AVATAR_COLORS) if c not in used), 0)
        self.colors.button(first_free).setChecked(True)

        self.ok = QPushButton("Let's go!")
        self.ok.setDefault(True)
        self.ok.clicked.connect(self.accept)
        cancel = QPushButton("Cancel", objectName="cancel")
        cancel.setProperty("role", "secondary")
        cancel.clicked.connect(self.reject)
        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(cancel)
        buttons.addWidget(self.ok)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.addWidget(heading)
        layout.addWidget(self.name_edit)
        layout.addWidget(self.error)
        layout.addSpacing(8)
        layout.addWidget(color_heading)
        layout.addLayout(swatches)
        layout.addSpacing(16)
        layout.addLayout(buttons)
        self._validate()

    def _validate(self) -> None:
        name = self.name_edit.text().strip()
        taken = bool(name) and self.store.name_taken(name)
        self.error.setText("Someone already has that name." if taken else "")
        self.ok.setEnabled(bool(name) and not taken)

    def name(self) -> str:
        return self.name_edit.text().strip()

    def color(self) -> str:
        return AVATAR_COLORS[self.colors.checkedId()]
