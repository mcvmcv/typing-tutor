"""The grown-ups' view: every player's progress side by side."""

from __future__ import annotations

from datetime import datetime

import pytest
from conftest import finish_steps, key_stat
from PySide6.QtCore import Qt

from typing_tutor.app import MainWindow
from typing_tutor.progress import overview
from typing_tutor.screens.parents import STATS, stat_values

NOW = datetime(2026, 11, 10, 18, 0)
LEFT = Qt.MouseButton.LeftButton


@pytest.fixture
def window(qtbot, store, player, played):
    w = MainWindow(store)
    qtbot.addWidget(w)
    w.resize(1150, 820)
    w.show()
    return w


@pytest.fixture
def played(monkeypatch):
    monkeypatch.setattr("typing_tutor.sounds.SoundPlayer.play", lambda self, name: None)


def test_button_only_shows_once_there_are_players(qtbot, store):
    w = MainWindow(store)
    qtbot.addWidget(w)
    w.show()
    assert not w.profiles.parents_btn.isVisible()
    store.add("Mia", "#f06292")
    w.show_profiles()
    assert w.profiles.parents_btn.isVisible()


def test_shows_a_card_for_each_player(qtbot, window, store, player):
    mia = store.add("Mia", "#f06292")
    finish_steps(store, mia, 9, wpm=14, accuracy=92)
    mia.key_stats = {c: key_stat(30) for c in "asdfghjl;"} | {"k": key_stat(30, misses=10)}
    mia.game_best = {"easy": 420}

    qtbot.mouseClick(window.profiles.parents_btn, LEFT)
    assert window.stack.currentWidget() is window.parents
    window.parents.refresh(NOW)
    sam_card, mia_card = window.parents.cards
    assert sam_card.values["Steps done"] == "0 of 40"
    assert sam_card.values["Last practised"] == "Not yet"
    assert sam_card.tricky_text == "not enough typing yet to tell"
    assert mia_card.values["Steps done"] == "9 of 40"
    assert mia_card.values["Best speed"] == "14 WPM"
    assert mia_card.values["Balloon Pop"] == "420"
    assert mia_card.tricky_text == ""  # shown as chips instead
    assert "Up to:" in mia_card.up_to.text()


def test_refreshing_replaces_the_cards(qtbot, window, store):
    window.show_parents()
    store.add("Mia", "#f06292")
    window.parents.refresh(NOW)
    assert len(window.parents.cards) == 2


def test_see_progress_opens_that_player_and_comes_back(qtbot, window, store, player):
    window.show_parents()
    card = window.parents.cards[0]
    card.details_requested.emit(player.id)
    assert window.stack.currentWidget() is window.progress
    assert window.progress.title.text() == "Sam's progress"
    assert "Grown-ups" in window.progress.back.text()
    assert window.profile_id is None  # looking doesn't switch the active player
    qtbot.mouseClick(window.progress.back, LEFT)
    assert window.stack.currentWidget() is window.parents


def test_back_goes_to_players(qtbot, window):
    window.show_parents()
    window.parents.back_requested.emit()
    assert window.stack.currentWidget() is window.profiles


def test_progress_from_the_menu_still_goes_back_to_lessons(window, player):
    window.choose_profile(player.id)
    window.show_parents()  # visit the grown-ups' view first
    window.show_player_progress(player.id)
    window.show_menu()
    window.show_progress()
    assert "Lessons" in window.progress.back.text()
    window.progress.back_requested.emit()
    assert window.stack.currentWidget() is window.menu


def test_unknown_player_is_ignored(window):
    window.show_parents()
    window.show_player_progress("gone")
    assert window.stack.currentWidget() is window.parents


def test_stat_values_line_up_with_headings(store, player):
    finish_steps(store, player, 1)
    values = stat_values(overview(player, NOW), NOW)
    assert len(values) == len(STATS)
    assert values[STATS.index("This week")] in ("0 steps", "1 step")
