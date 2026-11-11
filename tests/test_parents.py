"""The grown-ups' view: every player's progress side by side."""

from __future__ import annotations

from datetime import datetime

import pytest
from conftest import finish_steps, key_stat
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox

from typing_tutor import keyboard
from typing_tutor.app import MainWindow
from typing_tutor.progress import overview
from typing_tutor.screens.parents import STATS, import_summary, stat_values
from typing_tutor.storage import ImportPlan, Profile, ProfileStore, read_backup

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


def test_grown_ups_button_shows_even_with_no_players(qtbot, store):
    # A fresh install on a new computer needs it to load a backup.
    w = MainWindow(store)
    qtbot.addWidget(w)
    w.show()
    assert w.profiles.parents_btn.isVisible()
    w.show_parents()
    assert not w.parents.save_btn.isEnabled()


def test_shows_a_card_for_each_player(qtbot, window, store, player):
    mia = store.add("Mia", "#f06292")
    finish_steps(store, mia, 9, wpm=14, accuracy=92)
    mia.key_stats = {c: key_stat(30) for c in "asdfghjl;"} | {"k": key_stat(30, misses=10)}
    mia.game_best = {"easy": 420}

    qtbot.mouseClick(window.profiles.parents_btn, LEFT)
    assert window.stack.currentWidget() is window.parents
    window.parents.refresh(NOW)
    sam_card, mia_card = window.parents.cards
    assert sam_card.values["Steps done"] == "0 of 44"
    assert sam_card.values["Last practised"] == "Not yet"
    assert sam_card.tricky_text == "not enough typing yet to tell"
    assert mia_card.values["Steps done"] == "9 of 44"
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


# Backups ---------------------------------------------------------------------


class Boxes:
    """Records message boxes instead of showing them, and answers questions."""

    def __init__(self, monkeypatch, answer=QMessageBox.StandardButton.Yes):
        self.shown: list[tuple[str, str, str]] = []
        self.answer = answer
        for kind in ("information", "warning"):
            monkeypatch.setattr(QMessageBox, kind, self._recorder(kind))
        monkeypatch.setattr(QMessageBox, "question", self._question)

    def _recorder(self, kind):
        def record(parent, title, text, *args):
            self.shown.append((kind, title, text))
            return QMessageBox.StandardButton.Ok

        return record

    def _question(self, parent, title, text, *args):
        self.shown.append(("question", title, text))
        return self.answer


@pytest.fixture
def boxes(monkeypatch):
    return Boxes(monkeypatch)


def test_save_a_backup(qtbot, window, store, player, tmp_path, monkeypatch, boxes):
    target = tmp_path / "backup.json"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(target), ""))
    window.show_parents()
    qtbot.mouseClick(window.parents.save_btn, LEFT)
    assert read_backup(target) == store.profiles
    kind, _, text = boxes.shown[-1]
    assert kind == "information" and "1 player" in text and str(target) in text


def test_cancelling_the_save_dialog_does_nothing(window, monkeypatch, boxes):
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: ("", ""))
    window.show_parents()
    window.parents.save_backup()
    assert boxes.shown == []


def test_a_failed_save_is_explained(window, tmp_path, boxes):
    blocker = tmp_path / "file"
    blocker.write_text("")
    window.show_parents()
    assert not window.parents.export_to(blocker / "backup.json")
    assert boxes.shown[-1][:2] == ("warning", "Backup not saved")


def make_backup(tmp_path, *names):
    other = ProfileStore(tmp_path / "other.json")
    for name in names:
        other.add(name, "#64b5f6")
    path = tmp_path / "backup.json"
    other.export_backup(path)
    return path


def test_load_a_backup(qtbot, window, store, tmp_path, monkeypatch, boxes):
    backup = make_backup(tmp_path, "Leo", "Sam")
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: (str(backup), ""))
    window.show_parents()
    qtbot.mouseClick(window.parents.load_btn, LEFT)
    kind, _, question = boxes.shown[-1]
    assert kind == "question"
    assert "New players: Leo and Sam 2." in question
    assert "already a Sam here" in question
    assert [p.name for p in store.profiles] == ["Sam", "Leo", "Sam 2"]
    assert len(window.parents.cards) == 3


def test_saying_no_loads_nothing(window, store, tmp_path, monkeypatch):
    Boxes(monkeypatch, answer=QMessageBox.StandardButton.No)
    window.show_parents()
    assert not window.parents.import_from(make_backup(tmp_path, "Leo"))
    assert [p.name for p in store.profiles] == ["Sam"]


def test_replacing_players_warns_first(window, store, player, tmp_path, boxes):
    path = tmp_path / "mine.json"
    store.export_backup(path)
    window.show_parents()
    assert window.parents.import_from(path)
    question = boxes.shown[-1][2]
    assert "Sam is already here" in question and "can't be undone" in question


def test_a_bad_backup_is_explained(window, store, tmp_path, boxes):
    path = tmp_path / "junk.json"
    path.write_text("hello", encoding="utf-8")
    window.show_parents()
    assert not window.parents.import_from(path)
    assert boxes.shown == [("warning", "Can't load this backup", boxes.shown[0][2])]
    assert [p.name for p in store.profiles] == ["Sam"]


def test_a_failed_import_save_is_explained(window, store, tmp_path, monkeypatch, boxes):
    def fail(*args):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(store, "import_profiles", fail)
    window.show_parents()
    assert not window.parents.import_from(make_backup(tmp_path, "Leo"))
    assert boxes.shown[-1][:2] == ("warning", "Backup not loaded")


def test_cancelling_the_load_dialog_does_nothing(window, monkeypatch, boxes):
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: ("", ""))
    window.show_parents()
    window.parents.load_backup()
    assert boxes.shown == []


def test_import_summary_for_one_new_player():
    plan = ImportPlan(added=[Profile(id="a", name="Leo", color="#fff")], replaced=[], renamed={})
    assert import_summary(plan) == "New players: Leo.\n\nLoad the backup?"


# Keyboard layout -----------------------------------------------------------


def test_keyboard_buttons_show_the_current_layout(window):
    window.show_parents()
    assert window.parents.layout_buttons["us"].isChecked()
    assert "@" in window.parents.layout_note.text()


def test_choosing_uk_switches_and_remembers(qtbot, window, store):
    window.show_parents()
    qtbot.mouseClick(window.parents.layout_buttons["uk"], LEFT)
    assert keyboard.current() is keyboard.UK
    assert window.parents.layout_buttons["uk"].isChecked()
    assert "# key" in window.parents.layout_note.text()
    assert ProfileStore(store.path).keyboard == "uk"


def test_the_window_starts_on_the_saved_keyboard(qtbot, store):
    store.set_keyboard("uk")
    qtbot.addWidget(MainWindow(store))
    assert keyboard.current() is keyboard.UK


def test_with_no_choice_the_window_guesses_from_the_region(qtbot, store, monkeypatch):
    monkeypatch.setattr(keyboard, "system_layout", lambda: "uk")
    qtbot.addWidget(MainWindow(store))
    assert keyboard.current() is keyboard.UK
    assert store.keyboard is None  # a guess, not a choice


# Earlier copies ----------------------------------------------------------------


def test_earlier_copies_button_needs_a_copy(window, store, player):
    window.show_parents()
    assert not window.parents.copies_btn.isEnabled()
    store.snapshot("Before something")
    window.show_parents()
    assert window.parents.copies_btn.isEnabled()


def test_going_back_to_an_earlier_copy(window, store, player, monkeypatch, boxes):
    from typing_tutor.screens.parents import EarlierCopiesDialog

    store.delete(player.id)
    seen = []

    def choose(dialog):
        seen.extend(dialog.list.item(i).text() for i in range(dialog.list.count()))
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(EarlierCopiesDialog, "exec", choose)
    window.show_parents()
    assert window.parents.cards == []
    window.parents.copies_btn.click()
    assert "Before removing Sam" in seen[0] and "Sam" in seen[0].splitlines()[1]
    kind, _title, text = boxes.shown[0]
    assert kind == "question" and "copy of how things are now is kept" in text
    assert [c.values for c in window.parents.cards]  # Sam is back
    assert store.get(player.id) is not None


def test_saying_no_keeps_things_as_they_are(window, store, player, monkeypatch):
    Boxes(monkeypatch, answer=QMessageBox.StandardButton.No)
    store.snapshot("kept")
    store.delete(player.id)
    assert window.parents.restore_snapshot(store.snapshots()[0]) is False
    assert store.profiles == []


def test_cancelling_the_copies_dialog_does_nothing(window, store, player, monkeypatch, boxes):
    from typing_tutor.screens.parents import EarlierCopiesDialog

    store.snapshot("kept")
    monkeypatch.setattr(EarlierCopiesDialog, "exec", lambda d: QDialog.DialogCode.Rejected)
    window.parents.open_earlier_copies()
    assert boxes.shown == []


def test_a_damaged_copy_is_explained(window, store, player, boxes):
    store.snapshot("kept")
    snap = store.snapshots()[0]
    snap.path.write_text('{"profiles": [{"id": 1}]}')
    assert window.parents.restore_snapshot(snap) is False
    assert boxes.shown[-1][0] == "warning"


def test_a_failed_restore_save_is_explained(window, store, player, monkeypatch, boxes):
    store.snapshot("kept")

    def fail(*a):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(store, "save", fail)
    assert window.parents.restore_snapshot(store.snapshots()[0]) is False
    assert "Permission denied" in boxes.shown[-1][2]


def test_copies_dialog_lists_and_picks(qtbot, store, player):
    from typing_tutor.screens.parents import EarlierCopiesDialog

    store.snapshot("first")
    snaps = store.snapshots()
    dialog = EarlierCopiesDialog(snaps)
    qtbot.addWidget(dialog)
    assert dialog.chosen() == snaps[0]
    dialog.list.setCurrentRow(-1)
    assert dialog.chosen() is None


@pytest.mark.parametrize(
    ("made", "text"),
    [
        (datetime(2026, 11, 10, 9, 5), "Today, 9:05"),
        (datetime(2026, 11, 9, 17, 30), "Yesterday, 17:30"),
        (datetime(2026, 11, 2, 8, 0), "Monday 2 November, 8:00"),
    ],
)
def test_when_text(made, text):
    from typing_tutor.screens.parents import when_text

    assert when_text(made, NOW) == text


# New-version check ---------------------------------------------------------------


@pytest.fixture
def github(monkeypatch):
    from test_updates import FakeGitHub

    return FakeGitHub(monkeypatch)


def test_update_check_is_off_and_offline_by_default(window, store, github):
    window.show_parents()
    assert not window.parents.updates_box.isChecked()
    assert github.requests == []


def test_turning_on_update_checks_asks_github(window, store, github):
    window.show_parents()
    window.parents.updates_box.setChecked(True)
    assert store.check_updates and len(github.requests) == 1
    assert window.parents.update_note.text() == "Checking…"
    github.answer("v99.0.0")
    note = window.parents.update_note.text()
    assert "Version 99.0.0 is out!" in note and "Download it" in note


def test_already_up_to_date(window, github):
    from typing_tutor import __version__

    window.parents.updates_box.setChecked(True)
    github.answer(f"v{__version__}")
    assert "latest version" in window.parents.update_note.text()


def test_a_failed_check_says_so(window, github):
    from PySide6.QtNetwork import QNetworkReply

    window.parents.updates_box.setChecked(True)
    github.answer(error=QNetworkReply.NetworkError.TimeoutError)
    assert "Couldn't check" in window.parents.update_note.text()


def test_turning_update_checks_off_clears_the_note(window, store, github):
    window.parents.updates_box.setChecked(True)
    github.answer("v99.0.0")
    window.parents.updates_box.setChecked(False)
    assert not store.check_updates and window.parents.update_note.text() == ""


def test_checks_at_start_when_turned_on(qtbot, store, github):
    store.set_check_updates(True)
    w = MainWindow(store)
    qtbot.addWidget(w)
    assert len(github.requests) == 1
    github.answer("v99.0.0")
    w.show_parents()  # the news is waiting on the grown-ups' screen
    assert w.parents.updates_box.isChecked()
    assert "99.0.0 is out" in w.parents.update_note.text()


def test_parent_screen_works_without_a_checker(qtbot, store, player):
    from typing_tutor.screens.parents import ParentScreen

    screen = ParentScreen(store)
    qtbot.addWidget(screen)
    screen.refresh()
    store.check_updates = True
    screen.set_check_updates(True)
    assert screen.update_note.text() == ""
