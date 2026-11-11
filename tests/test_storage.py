import json
from dataclasses import asdict
from datetime import datetime, timedelta

import pytest
from conftest import finish_steps, key_stat

from typing_tutor.storage import (
    DAILY_COPIES,
    EVENT_COPIES,
    KEY_STATS_WINDOW,
    BackupError,
    Profile,
    ProfileStore,
    read_backup,
)


def test_profiles_survive_a_reload(store, player):
    store.record_result(player.id, "home-row/fj", 10.0, 97.5, 3)
    reloaded = ProfileStore(store.path)
    profile = reloaded.get(player.id)
    assert profile is not None
    assert profile.name == "Sam" and profile.stars("home-row/fj") == 3
    assert profile.history[0]["step"] == "home-row/fj"


def test_new_players_get_defaults(store):
    profile = store.add("  Ava ", "#fff176", speed_goal=20)
    assert profile.name == "Ava"
    assert profile.speed_goal == 20 and profile.sound and profile.key_clicks
    assert profile.best == {} and profile.game_best == {}


def test_names_are_compared_ignoring_case(store, player):
    assert store.name_taken("sam") and store.name_taken(" SAM ")
    assert not store.name_taken("Sammy")


def test_best_results_keep_the_maximum(store, player):
    store.record_result(player.id, "s", 20, 90, 2)
    store.record_result(player.id, "s", 15, 99, 3)
    store.record_result(player.id, "s", 10, 80, 1)
    assert player.best["s"] == {"stars": 3, "wpm": 20, "accuracy": 99}
    assert len(player.history) == 3


def test_key_stats_are_halved_once_a_key_has_plenty_of_samples(store, player):
    store.record_result(player.id, "s", 10, 90, 2, {"k": key_stat(KEY_STATS_WINDOW + 10)})
    assert player.key_stats["k"]["h"] == (KEY_STATS_WINDOW + 10) / 2


def test_delete(store, player):
    store.delete(player.id)
    assert store.get(player.id) is None
    assert ProfileStore(store.path).profiles == []


def test_settings_are_saved(store, player):
    store.set_speed_goal(player.id, 30)
    store.set_sound(player.id, False, key_clicks=False)
    profile = ProfileStore(store.path).get(player.id)
    assert profile.speed_goal == 30 and not profile.sound and not profile.key_clicks


def test_game_best_only_goes_up(store, player):
    assert store.record_game(player.id, "easy", 100, {}) is True
    assert store.record_game(player.id, "easy", 50, {}) is False
    assert store.record_game(player.id, "easy", 120, {"a": key_stat(3)}) is True
    assert player.game_best == {"easy": 120}
    assert player.key_stats["a"]["h"] == 3


def test_unknown_player_ids_are_ignored(store):
    store.record_result("nobody", "s", 1, 1, 1)
    assert store.record_game("nobody", "easy", 1, {}) is False


def test_files_from_older_versions_load_with_defaults(tmp_path):
    path = tmp_path / "profiles.json"
    path.write_text(
        json.dumps(
            {
                "profiles": [
                    {
                        "id": "x",
                        "name": "Old",
                        "color": "#fff",
                        "best": {},
                        "history": [],
                        "retired_field": 1,
                    },
                ]
            }
        )
    )
    profile = ProfileStore(path).get("x")
    assert profile is not None
    assert profile.key_stats == {} and profile.speed_goal == 0 and profile.sound


def test_unreadable_files_are_kept_aside_not_overwritten(tmp_path):
    path = tmp_path / "profiles.json"
    path.write_text("{ not json")
    store = ProfileStore(path)
    assert store.profiles == []
    broken = list(tmp_path.glob("profiles.broken-*.json"))
    assert len(broken) == 1 and broken[0].read_text() == "{ not json"


def test_saving_leaves_no_temporary_file(store, player):
    assert store.path.exists()
    assert not store.path.with_suffix(".tmp").exists()


# Backups ---------------------------------------------------------------------


def test_backup_round_trip(tmp_path, store, player):
    finish_steps(store, player, 3)
    player.key_stats = {"f": key_stat(20)}
    player.game_best = {"easy": 120}
    store.export_backup(tmp_path / "backup.json")
    (loaded,) = read_backup(tmp_path / "backup.json")
    assert loaded == player


def test_a_copied_save_file_works_as_a_backup(store, player):
    finish_steps(store, player, 2)
    assert read_backup(store.path) == [player]


def write_json(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def good_player(**changes):
    data = {"id": "abc", "name": "Mia", "color": "#f06292", "history": [], "best": {}}
    return data | changes


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("not json at all", "isn't a Learn Typing backup"),
        ("[1, 2, 3]", "isn't a Learn Typing backup"),
        ('{"profiles": "nope"}', "isn't a Learn Typing backup"),
        ('{"version": "one", "profiles": []}', "isn't a Learn Typing backup"),
        ('{"version": 2, "profiles": []}', "newer version"),
        ('{"version": 1, "profiles": []}', "doesn't have any players"),
    ],
)
def test_unreadable_backups_are_refused(tmp_path, content, message):
    path = tmp_path / "backup.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(BackupError, match=message):
        read_backup(path)


@pytest.mark.parametrize(
    ("player", "message"),
    [
        ("Mia", "isn't in the right format"),
        (good_player(name=""), "missing their name"),
        (good_player(id=7), "missing their id"),
        (good_player(best={"home-row/fj": {"stars": "lots"}}), "stars"),
        (good_player(history=[{"step": "x"}]), "practice history"),
        (
            good_player(
                history=[{"step": "x", "wpm": 1, "accuracy": 1, "stars": 1, "when": "soon"}]
            ),
            "date",
        ),
        (good_player(key_stats={"f": {"h": 1}}), "key stats"),
        (good_player(key_stats={"f": {"h": True, "m": 0, "t": 0, "n": 0}}), "key stats"),
        (good_player(game_best={"easy": "high"}), "Balloon Pop"),
    ],
)
def test_backups_with_broken_players_are_refused(tmp_path, player, message):
    path = write_json(tmp_path / "backup.json", {"profiles": [player]})
    with pytest.raises(BackupError, match=message):
        read_backup(path)


def test_duplicate_players_are_refused(tmp_path):
    path = write_json(tmp_path / "backup.json", {"profiles": [good_player(), good_player()]})
    with pytest.raises(BackupError, match="twice"):
        read_backup(path)


def test_missing_backup_file(tmp_path):
    with pytest.raises(BackupError, match="couldn't be opened"):
        read_backup(tmp_path / "nowhere.json")


def test_import_adds_replaces_and_renames(tmp_path, store, player):
    other = ProfileStore(tmp_path / "other.json")
    other.add("Leo", "#64b5f6")
    other.add("Sam", "#81c784")  # a different Sam from the one already here
    newer_player = Profile.from_dict(asdict(player))
    newer_player.speed_goal = 25
    incoming = [*other.profiles, newer_player]

    plan = store.import_profiles(incoming)
    assert [p.name for p in plan.added] == ["Leo", "Sam 2"]
    assert plan.renamed == {"Sam": "Sam 2"}
    assert plan.replaced == [newer_player]
    assert [p.name for p in store.profiles] == ["Sam", "Leo", "Sam 2"]
    assert store.get(player.id).speed_goal == 25
    assert [p.name for p in ProfileStore(store.path).profiles] == ["Sam", "Leo", "Sam 2"]


def test_renaming_skips_names_already_used(store, player):
    store.add("Sam 2", "#81c784")
    stranger = Profile(id="new", name="Sam", color="#ffb74d")
    assert store.plan_import([stranger]).renamed == {"Sam": "Sam 3"}


def test_planning_changes_nothing(store, player):
    store.plan_import([Profile(id="new", name="Leo", color="#64b5f6")])
    assert [p.name for p in store.profiles] == ["Sam"]


# Keyboard layout -----------------------------------------------------------


def test_no_keyboard_chosen_by_default(store):
    store.save()
    assert store.keyboard is None
    assert "keyboard" not in json.loads(store.path.read_text())


def test_keyboard_choice_is_saved(store, tmp_path):
    store.set_keyboard("uk")
    assert ProfileStore(store.path).keyboard == "uk"


def test_a_strange_keyboard_value_is_ignored(tmp_path):
    path = tmp_path / "profiles.json"
    path.write_text(json.dumps({"version": 1, "profiles": [], "keyboard": 5}))
    assert ProfileStore(path).keyboard is None


def test_backups_leave_the_keyboard_behind(store, player, tmp_path):
    # The keyboard belongs to the computer, not the players.
    store.set_keyboard("uk")
    backup = tmp_path / "backup.json"
    store.export_backup(backup)
    assert "keyboard" not in json.loads(backup.read_text())
    other = ProfileStore(tmp_path / "other.json")
    other.import_profiles(read_backup(backup))
    assert other.keyboard is None


# Automatic copies -----------------------------------------------------------


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 11, 10, 17, 0)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **kwargs) -> None:
        self.now += timedelta(**kwargs)


@pytest.fixture
def clocked(tmp_path):
    store = ProfileStore(tmp_path / "profiles.json")
    store.clock = Clock()
    return store


def test_no_copy_before_anything_is_saved(clocked):
    clocked.add("Sam", "#64b5f6")  # the very first save: nothing to keep yet
    assert clocked.snapshots() == []


def test_one_copy_a_day_of_the_progress_before_the_days_first_change(clocked):
    sam = clocked.add("Sam", "#64b5f6")
    clocked.clock.advance(days=1)
    clocked.record_result(sam.id, "home-row/fj", 10, 95, 3)
    clocked.record_result(sam.id, "home-row/dk", 10, 95, 3)  # same day: no new copy
    [snap] = clocked.snapshots()
    assert snap.reason == "Start of the day" and snap.names == ["Sam"]
    assert snap.made == clocked.clock.now
    assert read_backup(snap.path)[0].best == {}  # as it was before today's practice


def test_only_a_week_of_daily_copies_is_kept(clocked):
    sam = clocked.add("Sam", "#64b5f6")
    for _ in range(DAILY_COPIES + 3):
        clocked.clock.advance(days=1)
        clocked.set_speed_goal(sam.id, 10)
    snaps = clocked.snapshots()
    assert len(snaps) == DAILY_COPIES
    assert snaps[0].made == clocked.clock.now  # the newest are kept


def test_removing_a_player_keeps_a_copy_first(clocked):
    sam = clocked.add("Sam", "#64b5f6")
    clocked.add("Ava", "#ffb74d")
    clocked.delete(sam.id)
    snap = next(s for s in clocked.snapshots() if s.reason == "Before removing Sam")
    assert snap.names == ["Sam", "Ava"]
    clocked.restore(snap)
    assert [p.name for p in clocked.profiles] == ["Sam", "Ava"]
    assert clocked.snapshots()[0].reason == "Before going back to an earlier copy"


def test_loading_a_backup_keeps_a_copy_first(clocked, tmp_path):
    clocked.add("Sam", "#64b5f6")
    other = ProfileStore(tmp_path / "other.json")
    other.add("Ava", "#ffb74d")
    clocked.import_profiles(other.profiles)
    assert any(s.reason == "Before loading a backup" for s in clocked.snapshots())


def test_only_the_last_few_event_copies_are_kept(clocked):
    for i in range(EVENT_COPIES + 3):
        clocked.add(f"P{i}", "#64b5f6")
        clocked.clock.advance(seconds=1)
        clocked.snapshot(f"event {i}")
    events = [s for s in clocked.snapshots() if s.reason.startswith("event")]
    assert len(events) == EVENT_COPIES
    assert events[0].reason == f"event {EVENT_COPIES + 2}"


def test_strange_files_in_the_backups_folder_are_ignored(clocked):
    clocked.add("Sam", "#64b5f6")
    clocked.snapshot("kept")
    (clocked.snapshot_dir / "notes.json").write_text("not json")
    (clocked.snapshot_dir / "other.json").write_text(json.dumps({"profiles": []}))
    assert [s.reason for s in clocked.snapshots()] == ["kept"]


def test_a_damaged_copy_is_not_restored(clocked):
    sam = clocked.add("Sam", "#64b5f6")
    clocked.snapshot("kept")
    [snap] = clocked.snapshots()
    data = json.loads(snap.path.read_text())
    data["profiles"][0]["history"] = "broken"
    snap.path.write_text(json.dumps(data))
    clocked.delete(sam.id)
    with pytest.raises(BackupError):
        clocked.restore(snap)
    assert clocked.profiles == []


def test_a_copy_that_cant_be_written_doesnt_stop_saving(clocked):
    sam = clocked.add("Sam", "#64b5f6")
    clocked.snapshot_dir.write_text("a file where the folder should be")
    clocked.clock.advance(days=1)
    clocked.set_speed_goal(sam.id, 15)
    assert ProfileStore(clocked.path).get(sam.id).speed_goal == 15
