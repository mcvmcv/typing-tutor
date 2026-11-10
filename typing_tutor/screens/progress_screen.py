"""A player's progress: summary tiles, speed chart and recent practice."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..progress import points_by_attempt, points_by_day, recent_attempts, step_title, summary
from ..storage import Profile
from ..ui import label
from ..widgets.wpm_chart import WpmChart

MIN_DAYS_FOR_DAY_VIEW = 3


class Tile(QFrame):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("Tile")
        self.value = label("", "TileValue")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 12, 18, 12)
        layout.setSpacing(2)
        layout.addWidget(label(title, "Stat"))
        layout.addWidget(self.value)


class ProgressScreen(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._profile: Profile | None = None

        back = QPushButton("←  Lessons")
        back.setProperty("role", "secondary")
        back.clicked.connect(self.back_requested)
        self.title = label("", "Title")
        top = QHBoxLayout()
        top.addWidget(back)
        top.addSpacing(16)
        top.addWidget(self.title)
        top.addStretch()

        self.best = Tile("Best speed")
        self.accuracy = Tile("Recent accuracy")
        self.stars = Tile("Stars")
        self.steps = Tile("Steps finished")
        self.days = Tile("Practice days")
        tiles = QHBoxLayout()
        tiles.setSpacing(14)
        for tile in (self.best, self.accuracy, self.stars, self.steps, self.days):
            tiles.addWidget(tile)

        chart_title = label("Typing speed", "Heading")
        self.chart_sub = label("", "Subtitle")
        self.by_day = QPushButton("By day")
        self.by_attempt = QPushButton("Every step")
        self.mode = QButtonGroup(self)
        for btn in (self.by_day, self.by_attempt):
            btn.setCheckable(True)
            btn.setProperty("role", "segment")
            self.mode.addButton(btn)
        self.mode.buttonClicked.connect(lambda _: self._update_chart())
        chart_head = QHBoxLayout()
        heading_box = QVBoxLayout()
        heading_box.setSpacing(0)
        heading_box.addWidget(chart_title)
        heading_box.addWidget(self.chart_sub)
        chart_head.addLayout(heading_box)
        chart_head.addStretch()
        chart_head.addWidget(self.by_day)
        chart_head.addWidget(self.by_attempt)
        self.chart = WpmChart()

        recent_title = label("Recent practice", "Heading")
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["When", "What", "Speed", "Accuracy", "Stars"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setShowGrid(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 24, 40, 24)
        layout.setSpacing(12)
        layout.addLayout(top)
        layout.addSpacing(6)
        layout.addLayout(tiles)
        layout.addSpacing(8)
        layout.addLayout(chart_head)
        layout.addWidget(self.chart, 3)
        layout.addSpacing(4)
        layout.addWidget(recent_title)
        layout.addWidget(self.table, 2)

    @property
    def profile(self) -> Profile:
        if self._profile is None:
            raise RuntimeError("set_profile() must be called first")
        return self._profile

    def set_profile(self, profile: Profile) -> None:
        self._profile = profile
        self.title.setText(f"{profile.name}'s progress")
        s = summary(profile)
        self.best.value.setText(f"{s.best_wpm:.0f} WPM" if s.best_wpm else "–")
        self.accuracy.value.setText(
            f"{s.recent_accuracy:.0f}%" if s.recent_accuracy is not None else "–"
        )
        self.stars.value.setText(f"{s.stars} of {s.max_stars}")
        self.steps.value.setText(f"{s.steps_done} of {s.total_steps}")
        self.days.value.setText(str(s.practice_days))

        day_view = len(points_by_day(profile)) >= MIN_DAYS_FOR_DAY_VIEW
        (self.by_day if day_view else self.by_attempt).setChecked(True)
        self._update_chart()
        self._fill_table()

    def _update_chart(self) -> None:
        profile = self.profile
        goal = float(profile.speed_goal)
        if self.by_day.isChecked():
            points = points_by_day(profile)
            self.chart_sub.setText("Words per minute, average for each practice day")
        else:
            points = points_by_attempt(profile)
            self.chart_sub.setText("Words per minute for each step played, latest 60")
        self.chart.set_data(points, goal, "Finish a few steps to see your speed chart here!")

    def _fill_table(self) -> None:
        rows = recent_attempts(self.profile)
        self.table.setRowCount(len(rows))
        for r, h in enumerate(rows):
            when = datetime.fromisoformat(h["when"])
            cells = [
                f"{when.day} {when.strftime('%b')}, {when.strftime('%H:%M')}",
                step_title(h["step"]),
                f"{h['wpm']:.0f} WPM",
                f"{h['accuracy']:.0f}%",
                "★" * h["stars"] + "☆" * (3 - h["stars"]),
            ]
            for c, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if c == 4:
                    item.setForeground(Qt.GlobalColor.darkYellow)
                self.table.setItem(r, c, item)
