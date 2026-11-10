"""Main window and application entry point."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QDialog, QMainWindow, QStackedWidget

from .plays import lesson_play, review_play
from .screens.menu import LessonMenuScreen
from .screens.practice import PracticeScreen, StepResult
from .screens.profiles import ProfileScreen, SettingsDialog
from .screens.progress_screen import ProgressScreen
from .sounds import SoundPlayer
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
        self.sounds = SoundPlayer(parent=self)
        self.practice = PracticeScreen(self.sounds)
        self.progress = ProgressScreen()
        self.stack = QStackedWidget()
        for screen in (self.profiles, self.menu, self.practice, self.progress):
            self.stack.addWidget(screen)
        self.setCentralWidget(self.stack)

        self.profiles.profile_chosen.connect(self.choose_profile)
        self.menu.switch_player.connect(self.show_profiles)
        self.menu.step_chosen.connect(self.start_step)
        self.menu.review_requested.connect(self.start_review)
        self.menu.settings_requested.connect(self.open_settings)
        self.menu.progress_requested.connect(self.show_progress)
        self.progress.back_requested.connect(self.show_menu)
        self.practice.menu_requested.connect(self.show_menu)
        self.practice.step_completed.connect(self._record)
        self.practice.sound_toggled.connect(
            lambda on: self.store.set_sound(self.profile_id, on))

    def choose_profile(self, profile_id: str) -> None:
        self.profile_id = profile_id
        self._apply_sound_settings()
        self.show_menu()

    def _apply_sound_settings(self) -> None:
        profile = self.store.get(self.profile_id)
        if profile is not None:
            self.sounds.enabled = profile.sound
            self.sounds.key_clicks = profile.key_clicks

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
        profile = self.store.get(self.profile_id)
        self.stack.setCurrentWidget(self.practice)
        self.practice.start(lesson_play(lesson, index, profile))

    def show_progress(self) -> None:
        self.progress.set_profile(self.store.get(self.profile_id))
        self.stack.setCurrentWidget(self.progress)

    def start_review(self) -> None:
        play = review_play(self.store.get(self.profile_id))
        if play is not None:
            self.stack.setCurrentWidget(self.practice)
            self.practice.start(play)

    def open_settings(self) -> None:
        profile = self.store.get(self.profile_id)
        dlg = SettingsDialog(profile, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.store.set_speed_goal(profile.id, dlg.speed_goal())
            self.store.set_sound(profile.id, dlg.sound_on(), dlg.key_clicks_on())
            self._apply_sound_settings()
            self.menu.refresh()

    def _record(self, result: StepResult) -> None:
        self.store.record_result(self.profile_id, result.step_id, result.wpm,
                                 result.accuracy, result.stars, result.key_stats)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("learn-typing")
    apply_theme(app)
    window = MainWindow(ProfileStore(ProfileStore.default_path()))
    window.show()
    return app.exec()
