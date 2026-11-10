"""End-to-end tests that drive the real screens with simulated key presses."""

from __future__ import annotations

import pytest
from conftest import finish_steps, key_stat
from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication, QDialog

from typing_tutor import keyboard
from typing_tutor.app import MainWindow
from typing_tutor.lessons import ALL_STEPS, CAPITALS, HOME_ROW, TOP_ROW
from typing_tutor.screens import practice as practice_module
from typing_tutor.screens.profiles import NewPlayerDialog, SettingsDialog
from typing_tutor.sounds import SoundPlayer
from typing_tutor.storage import ProfileStore
from typing_tutor.widgets.keyboard_view import KeyboardView


@pytest.fixture
def played(monkeypatch):
    """Record sounds instead of playing them."""
    names: list[str] = []

    def record(self, name):
        if self.enabled and not (name == "click" and not self.key_clicks):
            names.append(name)

    monkeypatch.setattr(SoundPlayer, "play", record)
    return names


@pytest.fixture
def results(monkeypatch):
    """Answer the end-of-step dialog automatically. Set .choice to pick a button."""

    class Recorder(list):
        choice = "menu"

    shown = Recorder()

    def fake_exec(dialog):
        shown.append(dialog)
        dialog._choose(shown.choice)
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(practice_module.ResultDialog, "exec", fake_exec)
    return shown


@pytest.fixture
def window(qtbot, store, player, played):
    w = MainWindow(store)
    qtbot.addWidget(w)
    w.resize(1150, 820)
    w.show()
    w.choose_profile(player.id)
    return w


def type_into(qtbot, widget, text):
    for ch in text:
        qtbot.keyClicks(widget, ch)


def type_whole_step(qtbot, screen):
    for line in list(screen._run.lines):
        type_into(qtbot, screen, line)


# Players ---------------------------------------------------------------------


def test_new_player_dialog_validates_names(qtbot, store, player):
    dlg = NewPlayerDialog(store)
    qtbot.addWidget(dlg)
    assert not dlg.ok.isEnabled()
    dlg.name_edit.setText("sam")
    assert not dlg.ok.isEnabled() and "already" in dlg.error.text()
    dlg.name_edit.setText("Ava")
    dlg.speed.setCurrentIndex(3)
    assert dlg.ok.isEnabled() and dlg.speed_goal() == 20
    assert dlg.color() != player.color  # suggests a colour not yet taken


def test_choosing_a_player_opens_their_menu(window, player):
    assert window.stack.currentWidget() is window.menu
    assert window.menu.greeting.text() == "Hi, Sam!"
    assert window.menu.continue_btn.text() == "▶  Start your first lesson!"


# Practice ----------------------------------------------------------------------


def test_finishing_a_step_saves_stars_and_unlocks_the_next(qtbot, window, player, results, played):
    window.start_step(HOME_ROW, 0)
    screen = window.practice
    lines = list(screen._run.lines)
    type_whole_step(qtbot, screen)
    qtbot.waitUntil(lambda: len(results) == 1)
    assert player.stars(HOME_ROW.step_id(0)) == 3
    assert window.stack.currentWidget() is window.menu
    assert played.count("click") == sum(len(line) for line in lines) - len(lines)
    assert played.count("line") == len(lines) - 1 and played[-1] == "stars3"
    assert player.key_stats["f"]["h"] > 0


def test_next_step_button_starts_the_following_step(qtbot, window, results):
    results.choice = "next"
    window.start_step(HOME_ROW, 0)
    type_whole_step(qtbot, window.practice)
    qtbot.waitUntil(lambda: window.practice._play.step_id == HOME_ROW.step_id(1))


def test_mistakes_give_friendly_hints(qtbot, window, played):
    window.start_step(HOME_ROW, 0)
    screen = window.practice
    assert screen.hint.text() == "Press F with your left pointer finger"
    qtbot.keyClicks(screen, "k")
    assert screen.hint.text() == "Oops! That was K. Try F."
    assert screen.hint.property("error") is True and played == ["oops"]
    qtbot.keyClicks(screen, "F")
    assert "Caps Lock" in screen.hint.text()
    qtbot.keyClicks(screen, "f")
    assert screen.hint.property("error") is False


def test_missing_shift_hint_names_the_right_pinky(qtbot, window):
    window.start_step(CAPITALS, 1)
    screen = window.practice
    line = screen._run.lines[0]
    cap = next(i for i, c in enumerate(line) if c.isupper())
    type_into(qtbot, screen, line[:cap])
    qtbot.keyClicks(screen, line[cap].lower())
    assert screen.hint.text() == "That needs a capital! Hold Shift with your left pinky."


def test_held_keys_do_not_repeat(qtbot, window):
    window.start_step(HOME_ROW, 0)
    screen = window.practice
    qtbot.keyPress(screen, Qt.Key.Key_K, Qt.KeyboardModifier.NoModifier)
    repeat = QKeyEvent(
        QEvent.Type.KeyPress, Qt.Key.Key_K, Qt.KeyboardModifier.NoModifier, "k", True
    )
    QApplication.sendEvent(screen, repeat)
    assert screen._run.mistakes == 1


def test_sound_button_mutes_and_is_remembered(qtbot, window, store, player, played):
    window.start_step(HOME_ROW, 0)
    screen = window.practice
    screen.sound_btn.click()
    assert screen.sound_btn.text() == "Sound: off" and not player.sound
    qtbot.keyClicks(screen, "f")
    assert played == []


def test_speed_goal_shows_next_to_live_speed(window, store, player):
    store.set_speed_goal(player.id, 20)
    window.start_step(TOP_ROW, 5)
    assert window.practice.speed_label.text() == "Speed: 0 / 20 WPM"


# Menu, review, settings ----------------------------------------------------------


def test_tricky_keys_panel_and_review(qtbot, window, store, player, results):
    finish_steps(store, player, 9)
    stats = {c: key_stat(30) for c in "asdfghjl;"}
    stats["k"] = key_stat(30, misses=10)
    store.record_result(player.id, "review", 10, 90, 2, stats)
    window.show_menu()
    menu = window.menu
    assert menu.tricky_panel.isVisible() and menu.tricky_label.text() == "Your tricky keys:"
    menu.review_btn.click()
    assert window.practice._play.review
    type_whole_step(qtbot, window.practice)
    qtbot.waitUntil(lambda: len(results) == 1)
    assert player.history[-1]["step"] == "review"


def test_tricky_keys_panel_hidden_for_new_players(window):
    assert not window.menu.tricky_panel.isVisible()


def test_settings_dialog_reflects_and_returns_choices(qtbot, store, player):
    store.set_speed_goal(player.id, 30)
    dlg = SettingsDialog(player)
    qtbot.addWidget(dlg)
    assert dlg.speed_goal() == 30 and dlg.sound_on() and dlg.key_clicks_on()
    assert dlg.space_dots_on()
    dlg.sound.setChecked(False)
    assert not dlg.clicks.isEnabled() and not dlg.sound_on()


def test_menu_locks_future_steps(window, store, player):
    finish_steps(store, player, 2)
    window.show_menu()
    texts = [w.text() for w in window.menu.findChildren(type(window.menu.continue_btn))]
    assert any(t.startswith("3. S and L\n☆☆☆") for t in texts)
    assert any(t.startswith("4. A and ;\nLocked") for t in texts)


# Progress ------------------------------------------------------------------------


def test_progress_screen(qtbot, window, store, player):
    finish_steps(store, player, 5)
    window.menu.progress_requested.emit()
    screen = window.progress
    assert window.stack.currentWidget() is screen
    assert screen.steps.value.text() == "5 of 40" and screen.stars.value.text() == "15 of 120"
    assert screen.table.rowCount() == 5
    assert screen.by_attempt.isChecked() and len(screen.chart._points) == 5
    screen.by_day.click()
    assert len(screen.chart._points) == 1
    qtbot.mouseMove(screen.chart, QPoint(screen.chart.width() // 2, 100))
    assert screen.chart._hover == 0


def test_progress_chart_empty_state(window):
    window.show_progress()
    assert window.progress.chart._points == [] and window.progress.best.value.text() == "–"


# Game ----------------------------------------------------------------------------


def test_game_button_unlocks_after_home_row_step_five(window, store, player):
    assert not window.menu.game_btn.isEnabled()
    finish_steps(store, player, 5)
    window.show_menu()
    assert window.menu.game_btn.isEnabled()


def test_playing_balloon_pop(qtbot, window, store, player, played):
    finish_steps(store, player, 14)
    window.show_menu()
    window.menu.game_btn.click()
    game = window.game
    assert window.stack.currentWidget() is game and game.panel.isVisible()
    game.panel.difficulty_buttons["easy"].click()
    state = game.state
    for _ in range(20):
        game._handle(state.update(0.1))
    balloon = min((b for b in state.balloons if b.active), key=lambda b: b.y)
    type_into(qtbot, game, balloon.word)
    assert state.popped == 1 and "pop" in played

    qtbot.keyClick(game, Qt.Key.Key_Escape)
    assert game._paused and game.panel.title.text() == "Paused"
    qtbot.keyClick(game, Qt.Key.Key_Escape)
    assert not game._paused

    while not state.over:
        game._handle(state.update(0.2))
    qtbot.waitUntil(lambda: game.panel.title.text() == "Game over", timeout=3000)
    assert "New best score!" in game.panel.message.text()
    assert player.game_best == {"easy": state.score}
    game.panel.quit.click()
    assert window.stack.currentWidget() is window.menu


def test_every_step_can_be_opened(window):
    for lesson, i in ALL_STEPS:
        window.start_step(lesson, i)
        assert window.practice.title.text() == lesson.steps[i].title


# Dialogs and drawing paths ------------------------------------------------------------


def test_saving_settings_updates_the_player(monkeypatch, window, player):
    def fake_exec(dialog):
        dialog.speed.setCurrentIndex(5)  # 30 WPM
        dialog.clicks.setChecked(False)
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(SettingsDialog, "exec", fake_exec)
    window.menu.settings_requested.emit()
    assert player.speed_goal == 30 and player.sound and not player.key_clicks
    assert window.sounds.key_clicks is False


def test_turning_space_dots_off(monkeypatch, store, window, player):
    def fake_exec(dialog):
        dialog.dots.setChecked(False)
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(SettingsDialog, "exec", fake_exec)
    assert window.practice.typing.space_dots
    window.menu.settings_requested.emit()
    assert window.practice.typing.space_dots is False
    assert ProfileStore(store.path).get(player.id).space_dots is False


def test_each_player_gets_their_own_space_dots(window, store, player):
    other = store.add("Ava", "#ffb74d")
    store.set_space_dots(other.id, False)
    window.choose_profile(other.id)
    assert window.practice.typing.space_dots is False
    window.choose_profile(player.id)
    assert window.practice.typing.space_dots is True


def test_typing_line_without_space_dots(qtbot, monkeypatch):
    from PySide6.QtGui import QPainter

    from typing_tutor.session import TypingSession
    from typing_tutor.widgets.typing_view import TypingView

    drawn: list[str] = []
    real = QPainter.drawText

    def record(painter, *args):
        drawn.append(args[-1])
        return real(painter, *args)

    monkeypatch.setattr(QPainter, "drawText", record)

    def glyphs(dots: bool) -> str:
        drawn.clear()
        view = TypingView()
        qtbot.addWidget(view)
        view.resize(600, 110)
        view.space_dots = dots
        view.set_session(TypingSession("ab cd ef"))
        view.grab()
        return "".join(drawn)

    assert glyphs(True) == "ab·cd·ef"
    assert glyphs(False) == "abcdef"


def test_creating_a_player_from_the_player_screen(monkeypatch, qtbot, store, played):
    def fake_exec(dialog):
        dialog.name_edit.setText("Ava")
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(NewPlayerDialog, "exec", fake_exec)
    w = MainWindow(store)
    qtbot.addWidget(w)
    w.show_profiles()
    assert w.profiles.empty_hint.isVisibleTo(w.profiles)
    w.profiles._new_player()
    assert w.stack.currentWidget() is w.menu and w.menu.greeting.text() == "Hi, Ava!"


def test_removing_a_player_asks_first(monkeypatch, window, store, player):
    from PySide6.QtWidgets import QMessageBox

    answers = iter([QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes])
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: next(answers))
    window.show_profiles()
    assert window.profiles.confirm_remove(player) is False
    assert store.get(player.id) is not None  # said no
    assert window.profiles.confirm_remove(player) is True
    assert store.get(player.id) is None and window.profiles.grid.count() == 0


def test_chart_draws_goal_line_and_tooltip(qtbot, window, store, player):
    store.set_speed_goal(player.id, 20)
    finish_steps(store, player, 6)
    window.show_progress()
    chart = window.progress.chart
    qtbot.mouseMove(chart, QPoint(chart.width() - 5, 60))  # tooltip flips to the left
    image = chart.grab().toImage()
    assert chart._hover == 5 and not image.isNull()
    chart.leaveEvent(None)
    assert chart._hover is None


def test_game_draws_pops_and_game_over(qtbot, window, store, player):
    finish_steps(store, player, 14)
    window.show_game()
    game = window.game
    game.start_game("medium")
    state = game.state
    for _ in range(20):
        game._handle(state.update(0.1))
    balloon = min((b for b in state.balloons if b.active), key=lambda b: b.y)
    type_into(qtbot, game, balloon.word[:1])
    assert not game.grab().toImage().isNull()  # targeted balloon
    type_into(qtbot, game, balloon.word[1:])
    for _ in range(3):
        game._tick()
    assert not game.grab().toImage().isNull()  # pop burst and points


def test_keyboard_view_draws_the_uk_layout(qtbot):
    keyboard.set_layout("uk")
    view = KeyboardView()
    qtbot.addWidget(view)
    view.resize(960, 320)
    view.set_target_char('"')
    view.flash_wrong_char("#")
    view.grab()  # paints
    drawn = {key.ident: rect for key, rect in view.placed}
    assert "enter-below" not in drawn  # the space under the tall Enter
    assert drawn["#"].top() > drawn["enter"].top()  # # sits in the row below Enter's top
    assert view._targets == {"2", "rshift"}
    assert view._wrong == "#"
    tall = view._shape(keyboard.UK.rows[1][-1], drawn["enter"], 60, 8)
    assert tall.boundingRect().height() > drawn["enter"].height() * 1.5
