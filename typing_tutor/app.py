"""Main window and application entry point."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget

from .screens.menu import LessonMenuScreen
from .screens.practice import PracticeScreen
from .screens.profiles import ProfileScreen
from .storage import ProfileStore
from .theme import apply_theme


class MainWindow(QMainWindow):
    def __init__(self, store: ProfileStore):
        super().__init__()
        self.store = store
        self.profile_id: str | None = None
        self.setWindowTitle("Learn Typing")
        self.resize(1150, 820)
        self.setMinimumSize(900, 680)

        self.profiles = ProfileScreen(store)
        self.menu = LessonMenuScreen()
        self.practice = PracticeScreen()
        self.stack = QStackedWidget()
        for screen in (self.profiles, self.menu, self.practice):
            self.stack.addWidget(screen)
        self.setCentralWidget(self.stack)

        self.profiles.profile_chosen.connect(self.choose_profile)
        self.menu.switch_player.connect(self.show_profiles)
        self.menu.step_chosen.connect(self.start_step)
        self.practice.menu_requested.connect(self.show_menu)
        self.practice.step_completed.connect(self._record)

    def choose_profile(self, profile_id: str) -> None:
        self.profile_id = profile_id
        self.show_menu()

    def show_profiles(self) -> None:
        self.profiles.refresh()
        self.stack.setCurrentWidget(self.profiles)

    def show_menu(self) -> None:
        profile = self.store.get(self.profile_id)
        if profile is None:
            self.show_profiles()
            return
        self.menu.set_profile(profile)
        self.stack.setCurrentWidget(self.menu)

    def start_step(self, lesson, index: int) -> None:
        self.stack.setCurrentWidget(self.practice)
        self.practice.start(lesson, index)

    def _record(self, step_id: str, wpm: float, accuracy: float, stars: int) -> None:
        self.store.record_result(self.profile_id, step_id, wpm, accuracy, stars)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("learn-typing")
    apply_theme(app)
    window = MainWindow(ProfileStore(ProfileStore.default_path()))
    window.show()
    return app.exec()
