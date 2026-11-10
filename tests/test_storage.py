import json

from conftest import key_stat

from typing_tutor.storage import KEY_STATS_WINDOW, ProfileStore


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
    path.write_text(json.dumps({"profiles": [
        {"id": "x", "name": "Old", "color": "#fff", "best": {}, "history": [],
         "retired_field": 1},
    ]}))
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
