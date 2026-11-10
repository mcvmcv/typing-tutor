"""Main window and application entry point."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QDialog, QMainWindow, QStackedWidget

from .game import game_words
from .lessons import Lesson
from .plays import known_keys, lesson_play, review_play
from .screens.game_screen import GameScreen
from .screens.menu import LessonMenuScreen
from .screens.practice import PracticeScreen, StepResult
from .screens.profiles import ProfileScreen, SettingsDialog
from .screens.progress_screen import ProgressScreen
from .sounds import SoundPlayer
from .storage import Profile, ProfileStore
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
        self.game = GameScreen(self.sounds)
        self.game.record_game = self._record_game
        self.stack = QStackedWidget()
        for screen in (self.profiles, self.menu, self.practice, self.progress, self.game):
            self.stack.addWidget(screen)
        self.setCentralWidget(self.stack)

        self.profiles.profile_chosen.connect(self.choose_profile)
        self.menu.switch_player.connect(self.show_profiles)
        self.menu.step_chosen.connect(self.start_step)
        self.menu.review_requested.connect(self.start_review)
        self.menu.settings_requested.connect(self.open_settings)
        self.menu.progress_requested.connect(self.show_progress)
        self.progress.back_requested.connect(self.show_menu)
        self.menu.game_requested.connect(self.show_game)
        self.game.menu_requested.connect(self.show_menu)
        self.practice.menu_requested.connect(self.show_menu)
        self.practice.step_completed.connect(self._record)
        self.practice.sound_toggled.connect(lambda on: self.store.set_sound(self.profile.id, on))

    @property
    def profile(self) -> Profile:
        """The player currently using the app. Only valid after choose_profile()."""
        profile = self.store.get(self.profile_id) if self.profile_id else None
        if profile is None:
            raise RuntimeError("no player chosen")
        return profile

    def choose_profile(self, profile_id: str) -> None:
        self.profile_id = profile_id
        self._apply_sound_settings()
        self.show_menu()

    def _apply_sound_settings(self) -> None:
        self.sounds.enabled = self.profile.sound
        self.sounds.key_clicks = self.profile.key_clicks

    def show_profiles(self) -> None:
        self.profiles.refresh()
        self.stack.setCurrentWidget(self.profiles)

    def show_menu(self) -> None:
        if self.profile_id is None or self.store.get(self.profile_id) is None:
            self.show_profiles()
            return
        self.menu.set_profile(self.profile)
        self.stack.setCurrentWidget(self.menu)

    def start_step(self, lesson: Lesson, index: int) -> None:
        self.stack.setCurrentWidget(self.practice)
        self.practice.start(lesson_play(lesson, index, self.profile))

    def show_progress(self) -> None:
        self.progress.set_profile(self.profile)
        self.stack.setCurrentWidget(self.progress)

    def show_game(self) -> None:
        profile = self.profile
        self.stack.setCurrentWidget(self.game)
        self.game.open(game_words(known_keys(profile)), profile.game_best)

    def _record_game(self, difficulty: str, score: int, key_stats: dict) -> tuple[bool, int]:
        is_best = self.store.record_game(self.profile.id, difficulty, score, key_stats)
        return is_best, self.profile.game_best.get(difficulty, 0)

    def start_review(self) -> None:
        play = review_play(self.profile)
        if play is not None:
            self.stack.setCurrentWidget(self.practice)
            self.practice.start(play)

    def open_settings(self) -> None:
        profile = self.profile
        dlg = SettingsDialog(profile, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.store.set_speed_goal(profile.id, dlg.speed_goal())
            self.store.set_sound(profile.id, dlg.sound_on(), dlg.key_clicks_on())
            self._apply_sound_settings()
            self.menu.refresh()

    def _record(self, result: StepResult) -> None:
        self.store.record_result(
            self.profile.id,
            result.step_id,
            result.wpm,
            result.accuracy,
            result.stars,
            result.key_stats,
        )


def main() -> int:  # pragma: no cover - starts the real app
    app = QApplication(sys.argv)
    app.setApplicationName("learn-typing")
    apply_theme(app)
    window = MainWindow(ProfileStore(ProfileStore.default_path()))
    window.show()
    return app.exec()
