from conftest import finish_steps, key_stat

from typing_tutor.lessons import ALL_STEPS, HOME_ROW, KNOWN, TOP_ROW
from typing_tutor.plays import (
    DRILL_SPEED_SHARE,
    REVIEW_LINES,
    known_keys,
    lesson_play,
    review_play,
    weak_keys,
)

HOME_ROW_KEYS = "asdfghjkl;"


def give_key_stats(store, profile, stats):
    store.record_result(profile.id, "review", 10, 90, 2, stats)


def test_known_keys_follow_the_furthest_finished_step(store, player):
    assert known_keys(player) == KNOWN[HOME_ROW.step_id(0)]
    finish_steps(store, player, 11)
    lesson, i = ALL_STEPS[10]
    assert known_keys(player) == KNOWN[lesson.step_id(i)]


def test_no_tricky_keys_without_enough_data(store, player):
    finish_steps(store, player, 9)
    give_key_stats(store, player, {"a": key_stat(3, 3)})
    assert weak_keys(player) == []
    assert review_play(player) is None


def test_finds_keys_that_are_missed_or_slow(store, player):
    finish_steps(store, player, 9)
    stats = {c: key_stat(30) for c in HOME_ROW_KEYS}
    stats["k"] = key_stat(30, misses=8)  # often missed
    stats[";"] = key_stat(30, seconds_per_key=0.9)  # three times slower
    give_key_stats(store, player, stats)
    assert set(weak_keys(player)) == {"k", ";"}


def test_keys_not_yet_taught_are_ignored(store, player):
    finish_steps(store, player, 9)
    stats = {c: key_stat(30) for c in HOME_ROW_KEYS}
    stats["e"] = key_stat(30, misses=30)
    give_key_stats(store, player, stats)
    assert "e" not in weak_keys(player)


def test_review_lines_drill_the_weak_keys_with_known_keys_only(store, player):
    finish_steps(store, player, 9)
    stats = {c: key_stat(30) for c in HOME_ROW_KEYS}
    stats["k"] = key_stat(30, misses=10)
    give_key_stats(store, player, stats)
    play = review_play(player)
    assert play is not None and play.review and play.next_play is None
    lines = play.make_lines()
    assert len(lines) == REVIEW_LINES
    assert all(set(line) <= known_keys(player) for line in lines)
    assert sum(line.count("k") for line in lines) >= 8
    assert "K" in play.instruction


def test_speed_goal_is_lower_for_key_drills(store, player):
    store.set_speed_goal(player.id, 20)
    assert lesson_play(TOP_ROW, 0, player).speed_goal == round(20 * DRILL_SPEED_SHARE)
    assert lesson_play(TOP_ROW, 5, player).speed_goal == 20  # a words step


def test_no_speed_goal_by_default(player):
    assert lesson_play(TOP_ROW, 5, player).speed_goal == 0


def test_lesson_plays_chain_to_the_next_step(player):
    play = lesson_play(HOME_ROW, 0, player)
    following = play.next_play()
    assert following is not None and following.step_id == HOME_ROW.step_id(1)
    assert lesson_play(*ALL_STEPS[-1], player).next_play() is None
    assert play.header == "Home Row Heroes · step 1 of 9"
