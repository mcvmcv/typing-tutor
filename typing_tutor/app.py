"""Main window and application entry point."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QDialog, QMainWindow, QStackedWidget

from . import keyboard
from .game import game_words
from .lessons import Lesson
from .plays import known_keys, lesson_play, review_play
from .screens.game_screen import GameScreen
from .screens.menu import LessonMenuScreen
from .screens.parents import ParentScreen
from .screens.practice import PracticeScreen, StepResult
from .screens.profiles import ProfileScreen, SettingsDialog
from .screens.progress_screen import ProgressScreen
from .sounds import SoundPlayer
from .storage import Profile, ProfileStore
from .theme import apply_theme, text_scale
from .updates import UpdateChecker


class MainWindow(QMainWindow):
    def __init__(self, store: ProfileStore, sound_folder: Path | None = None):
        super().__init__()
        self.store = store
        keyboard.set_layout(store.keyboard or keyboard.system_layout())
        self.profile_id: str | None = None
        self._from_parents = False  # progress screen was opened from the grown-ups' view
        self.setWindowTitle("Learn Typing")
        self.resize(1150, 820)
        self.setMinimumSize(900, 680)

        self.profiles = ProfileScreen(store)
        self.menu = LessonMenuScreen()
        self.sounds = SoundPlayer(sound_folder, parent=self)
        self.practice = PracticeScreen(self.sounds)
        self.progress = ProgressScreen()
        self.updates = UpdateChecker(self)
        self.parents = ParentScreen(store, self.updates)
        self.game = GameScreen(self.sounds)
        self.game.record_game = self._record_game
        self.stack = QStackedWidget()
        screens = (self.profiles, self.menu, self.practice, self.progress, self.game, self.parents)
        for screen in screens:
            self.stack.addWidget(screen)
        self.setCentralWidget(self.stack)

        self.profiles.profile_chosen.connect(self.choose_profile)
        self.menu.switch_player.connect(self.show_profiles)
        self.menu.step_chosen.connect(self.start_step)
        self.menu.review_requested.connect(self.start_review)
        self.menu.settings_requested.connect(self.open_settings)
        self.menu.progress_requested.connect(self.show_progress)
        self.progress.back_requested.connect(self._progress_back)
        self.profiles.parents_requested.connect(self.show_parents)
        self.parents.back_requested.connect(self.show_profiles)
        self.parents.details_requested.connect(self.show_player_progress)
        self.menu.game_requested.connect(self.show_game)
        self.game.menu_requested.connect(self.show_menu)
        self.practice.menu_requested.connect(self.show_menu)
        self.practice.step_completed.connect(self._record)
        self.practice.sound_toggled.connect(lambda on: self.store.set_sound(self.profile.id, on))
        if store.check_updates:
            self.updates.check()

    @property
    def profile(self) -> Profile:
        """The player currently using the app. Only valid after choose_profile()."""
        profile = self.store.get(self.profile_id) if self.profile_id else None
        if profile is None:
            raise RuntimeError("no player chosen")
        return profile

    def choose_profile(self, profile_id: str) -> None:
        self.profile_id = profile_id
        self._apply_settings()
        self.show_menu()

    def _apply_settings(self) -> None:
        self.sounds.enabled = self.profile.sound
        self.sounds.key_clicks = self.profile.key_clicks
        self.practice.typing.space_dots = self.profile.space_dots
        self.practice.set_text_scale(text_scale(self.profile.text_size))

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
        self._from_parents = False
        self.stack.setCurrentWidget(self.progress)

    def show_parents(self) -> None:
        self.parents.refresh()
        self.stack.setCurrentWidget(self.parents)

    def show_player_progress(self, profile_id: str) -> None:
        """A player's progress opened from the grown-ups' view (doesn't switch player)."""
        profile = self.store.get(profile_id)
        if profile is None:
            return
        self.progress.set_profile(profile, back_text="←  Grown-ups")
        self._from_parents = True
        self.stack.setCurrentWidget(self.progress)

    def _progress_back(self) -> None:
        if self._from_parents:
            self.show_parents()
        else:
            self.show_menu()

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
            self.store.set_space_dots(profile.id, dlg.space_dots_on())
            self.store.set_text_size(profile.id, dlg.text_size())
            self._apply_settings()
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


ICON = Path(__file__).parent / "assets" / "icon.png"


def app_icon() -> QIcon:
    return QIcon(str(ICON))


def main() -> int:  # pragma: no cover - starts the real app
    app = QApplication(sys.argv)
    app.setApplicationName("learn-typing")
    app.setWindowIcon(app_icon())
    apply_theme(app)
    if "--smoke-test" in sys.argv:
        from . import smoke

        return smoke.run(app)
    window = MainWindow(ProfileStore(ProfileStore.default_path()))
    window.show()
    return app.exec()
