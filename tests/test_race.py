"""Snail Race: the rules, and the screen driven by simulated keys."""

from __future__ import annotations

import random

import pytest
from conftest import finish_steps
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent

from typing_tutor.app import MainWindow
from typing_tutor.lessons import KNOWN
from typing_tutor.race import (
    COUNTDOWN,
    DEFAULT_WPM,
    MIN_PACE,
    RACE_DIFFICULTIES,
    RACE_LEN,
    RaceState,
    race_text,
    recent_speed,
    rival_pace,
)
from typing_tutor.storage import ProfileStore, read_backup

MEDIUM = RACE_DIFFICULTIES["medium"]


def history(*speeds: float) -> list[dict]:
    return [{"wpm": s} for s in speeds]


# Rules ----------------------------------------------------------------------


def test_recent_speed_is_the_median_of_the_last_ten():
    assert recent_speed([]) == DEFAULT_WPM
    assert recent_speed(history(5, 9, 100)) == 9  # one fluke doesn't count much
    assert recent_speed(history(*([1] * 20), *([20] * 10))) == 20  # only the last 10


def test_rival_pace_scales_with_difficulty_and_has_a_floor():
    speeds = history(20, 20, 20)
    paces = [rival_pace(speeds, d) for d in RACE_DIFFICULTIES.values()]
    assert paces == sorted(paces) and paces[1] == 18
    assert rival_pace(history(1), RACE_DIFFICULTIES["easy"]) == MIN_PACE


@pytest.mark.parametrize("step", ["home-row/all", "top-row/sentences", "stories/sock"])
def test_race_text_uses_only_known_keys(step):
    known = KNOWN[step]
    for seed in range(5):
        text = race_text(known, random.Random(seed))
        assert text and set(text) <= known
        assert len(text) <= RACE_LEN + 12


def race(text="ab cd", pace=12.0) -> RaceState:
    return RaceState(MEDIUM, text, pace)


def test_counts_down_then_goes():
    s = race()
    assert s.countdown == 3 and not s.started
    assert s.type("a") == []  # no false starts
    assert [e.kind for e in s.update(1.0)] == [] and s.countdown == 2
    assert [e.kind for e in s.update(2.0)] == ["go"]
    assert s.started and s.countdown == 0


def test_typing_moves_the_player_and_mistakes_dont():
    s = race()
    s.update(COUNTDOWN)
    assert [e.kind for e in s.type("a")] == ["hit"]
    assert [e.kind for e in s.type("x")] == ["miss"]
    assert s.player_progress == pytest.approx(1 / 5)


def test_winning_before_the_rival():
    s = race("abc", pace=1.0)
    s.update(COUNTDOWN)
    s.update(1.5)
    for ch in "ab":
        s.type(ch)
    assert [e.kind for e in s.type("c")] == ["finish"]
    assert s.over and s.won
    assert s.wpm() == pytest.approx((3 / 5) / (1.5 / 60))
    assert s.update(1.0) == [] and s.type("x") == []  # nothing after the finish


def test_losing_when_the_rival_gets_there_first():
    s = race("abcde", pace=60.0)  # 5 chars a second: finishes after 1 second
    s.update(COUNTDOWN + 0.5)
    assert s.rival_progress == pytest.approx(0.5)
    assert [e.kind for e in s.update(0.8)] == ["rival-finished"]
    assert s.rival_finished_at == pytest.approx(COUNTDOWN + 1.0)
    assert not s.won  # not over yet
    for ch in "abcde":
        s.type(ch)
    assert s.over and not s.won


# Screen ---------------------------------------------------------------------


@pytest.fixture
def window(qtbot, store, player, played):
    w = MainWindow(store)
    qtbot.addWidget(w)
    w.resize(1150, 820)
    w.show()
    w.choose_profile(player.id)
    return w


@pytest.fixture
def played(monkeypatch):
    names: list[str] = []
    monkeypatch.setattr("typing_tutor.sounds.SoundPlayer.play", lambda self, n: names.append(n))
    return names


def press(widget, text: str) -> None:
    for ch in text:
        event = QKeyEvent(QEvent.Type.KeyPress, 0, Qt.KeyboardModifier.NoModifier, ch)
        widget.keyPressEvent(event)


def test_race_button_unlocks_with_balloon_pop(window, store, player):
    window.show_menu()
    assert not window.menu.race_btn.isEnabled()
    assert "unlocks" in window.menu.race_btn.text()
    finish_steps(store, player, 5)
    window.show_menu()
    assert window.menu.race_btn.isEnabled() and window.menu.race_btn.text() == "Snail Race"


def test_racing_from_start_to_finish(window, store, player, played):
    finish_steps(store, player, 14, wpm=10)
    window.show_menu()
    window.menu.race_btn.click()
    screen = window.race
    assert window.stack.currentWidget() is screen and screen.panel.isVisible()
    assert not screen.typing.isVisible()
    screen.panel.difficulty_buttons["medium"].click()
    s = screen.state
    assert s.pace_wpm == 9.0 and screen.typing.isVisible()
    assert not screen.grab().toImage().isNull()  # countdown

    screen._handle(s.update(COUNTDOWN))
    assert "line" in played  # go!
    press(screen, "#")
    assert "oops" in played and screen._wiggle > 0
    for ch in s.text:
        s.update(0.1)
        press(screen, ch)
    assert s.over and s.won
    assert screen.panel.title.text() == "You won!"
    assert "Your fastest race yet!" in screen.panel.message.text()
    best = ProfileStore(store.path).get(player.id).race_best
    assert best == {"medium": round(s.wpm(), 1)}
    assert "Best" in screen.panel.difficulty_buttons["medium"].text()
    assert s.text[0] in player.key_stats  # race keys count toward tricky keys

    screen.panel.quit.click()
    assert window.stack.currentWidget() is window.menu


def test_losing_says_who_won_and_offers_easy(window, store, player):
    finish_steps(store, player, 14, wpm=60)  # a speedy rival
    window.show_race()
    window.race.start_race("hard")
    s = window.race.state
    window.race._handle(s.update(COUNTDOWN + 60))
    for ch in s.text:
        press(window.race, ch)
    assert window.race.panel.title.text() == "Shelly won this time"
    assert "Try Easy" in window.race.panel.message.text()


def test_esc_pauses_and_resumes(qtbot, window, store, player):
    finish_steps(store, player, 14)
    window.show_race()
    window.race.start_race("easy")
    s = window.race.state
    s.update(COUNTDOWN)
    qtbot.keyClick(window.race, Qt.Key.Key_Escape)
    assert window.race._paused and window.race.panel.title.text() == "Paused"
    before = s.session.pos
    press(window.race, s.text[0])
    assert s.session.pos == before  # no typing while paused
    window.race._tick()
    assert window.race.state.time == s.time  # time stands still
    qtbot.keyClick(window.race, Qt.Key.Key_Escape)
    assert not window.race._paused


def test_keys_before_the_race_and_after_it_are_ignored(window, store, player):
    finish_steps(store, player, 14)
    window.show_race()
    press(window.race, "a")  # no race yet
    window.race.start_race("easy")
    s = window.race.state
    s.update(COUNTDOWN)
    for ch in s.text:
        press(window.race, ch)
    press(window.race, "a")  # after the finish
    assert s.over


def test_drawing_at_the_smallest_window(window, store, player):
    finish_steps(store, player, 14)
    window.resize(window.minimumSize())
    window.show_race()
    window.race.start_race("easy")
    window.race.state.update(COUNTDOWN + 2)
    window.race._wiggle = 0.2
    image = window.race.grab().toImage()
    assert image.width() == window.race.width()
    track = window.race.track_rect()
    assert track.bottom() < window.race.typing.geometry().top()


def test_race_bests_survive_a_backup(store, player, tmp_path):
    store.record_race(player.id, "easy", 12.34, {})
    assert store.record_race(player.id, "easy", 10, {}) is False
    target = tmp_path / "backup.json"
    store.export_backup(target)
    assert read_backup(target)[0].race_best == {"easy": 12.3}


def test_a_broken_race_best_is_refused(tmp_path):
    import json

    from typing_tutor.storage import BackupError

    bad = {"profiles": [{"id": "a", "name": "Mia", "color": "#fff", "race_best": {"easy": "x"}}]}
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(bad))
    with pytest.raises(BackupError, match="Snail Race"):
        read_backup(path)


def test_recording_for_an_unknown_player_does_nothing(store):
    assert store.record_race("nobody", "easy", 10, {}) is False
