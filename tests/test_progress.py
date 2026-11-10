from datetime import datetime

import pytest
from conftest import finish_steps, key_stat

from typing_tutor.lessons import ALL_STEPS
from typing_tutor.progress import (
    MAX_ATTEMPT_POINTS,
    days_ago,
    overview,
    points_by_attempt,
    points_by_day,
    recent_attempts,
    step_title,
    summary,
)


def add_attempt(profile, step, wpm, accuracy, when, stars=3):
    profile.history.append(
        {"step": step, "wpm": wpm, "accuracy": accuracy, "stars": stars, "when": when}
    )


def test_points_by_day_average_each_day(player):
    add_attempt(player, "home-row/fj", 10, 90, "2026-11-01T16:00:00")
    add_attempt(player, "home-row/dk", 20, 100, "2026-11-01T16:10:00")
    add_attempt(player, "home-row/sl", 12, 95, "2026-11-03T16:00:00")
    points = points_by_day(player)
    assert [p.label for p in points] == ["1 Nov", "3 Nov"]
    assert points[0].wpm == pytest.approx(15) and points[0].accuracy == pytest.approx(95)
    assert points[0].detail == "2 steps" and points[1].detail == "1 step"


def test_untimed_attempts_are_left_off_the_chart(player):
    add_attempt(player, "home-row/fj", 0, 100, "2026-11-01T16:00:00")
    assert points_by_day(player) == [] and points_by_attempt(player) == []


def test_points_by_attempt_show_the_latest_ones(player):
    for i in range(MAX_ATTEMPT_POINTS + 5):
        add_attempt(player, "home-row/fj", i + 1, 90, "2026-11-01T16:00:00")
    points = points_by_attempt(player)
    assert len(points) == MAX_ATTEMPT_POINTS
    assert points[-1].wpm == MAX_ATTEMPT_POINTS + 5
    assert points[0].detail == "Home Row Heroes: F and J"


def test_summary(store, player):
    first, second = (lesson.step_id(i) for lesson, i in ALL_STEPS[:2])
    store.record_result(player.id, first, 10, 90, 2)
    store.record_result(player.id, second, 14, 98, 3)
    store.record_result(player.id, "review", 30, 100, 3)  # reviews aren't course steps
    s = summary(player)
    assert s.best_wpm == 14
    assert s.stars == 5 and s.max_stars == 120
    assert s.steps_done == 2 and s.total_steps == 40
    assert s.practice_days == 1
    assert s.recent_accuracy == pytest.approx((90 + 98 + 100) / 3)


def test_summary_for_a_new_player(player):
    s = summary(player)
    assert s.best_wpm == 0 and s.recent_accuracy is None and s.practice_days == 0


def test_recent_attempts_are_newest_first(player):
    for i in range(15):
        add_attempt(player, "home-row/fj", i, 90, "2026-11-01T16:00:00")
    rows = recent_attempts(player)
    assert len(rows) == 12 and rows[0]["wpm"] == 14


def test_step_titles():
    assert step_title("review") == "Tricky keys practice"
    assert step_title("unknown/step") == "unknown/step"


# Grown-ups' overview ---------------------------------------------------------

NOW = datetime(2026, 11, 10, 18, 0)


def test_overview_of_a_new_player(player):
    o = overview(player, NOW)
    assert o.up_to == step_title(ALL_STEPS[0][0].step_id(0))
    assert o.last_practised is None and o.steps_this_week == 0
    assert o.tricky_keys is None and o.game_best == 0


def test_overview_counts_this_weeks_steps_and_last_practice(player):
    add_attempt(player, "home-row/fj", 10, 90, "2026-10-20T16:00:00")
    add_attempt(player, "home-row/fj", 10, 90, "2026-11-05T16:00:00")
    add_attempt(player, "home-row/dk", 10, 90, "2026-11-09T16:30:00")
    player.game_best = {"easy": 300, "hard": 120}
    o = overview(player, NOW)
    assert o.steps_this_week == 2
    assert o.last_practised == datetime(2026, 11, 9, 16, 30)
    assert o.game_best == 300


def test_overview_names_the_next_step(store, player):
    finish_steps(store, player, 3)
    lesson, i = ALL_STEPS[3]
    assert overview(player, NOW).up_to == step_title(lesson.step_id(i))


def test_overview_after_the_whole_course(store, player):
    finish_steps(store, player, len(ALL_STEPS))
    assert overview(player, NOW).up_to == "Finished the whole course!"


def test_overview_tricky_keys(store, player):
    finish_steps(store, player, 9)
    player.key_stats = {c: key_stat(30) for c in "asdfghjl;"}
    assert overview(player, NOW).tricky_keys == []
    player.key_stats["k"] = key_stat(30, misses=10)
    assert overview(player, NOW).tricky_keys == ["k"]


@pytest.mark.parametrize(
    ("when", "text"),
    [
        (None, "Not yet"),
        (datetime(2026, 11, 10, 7, 0), "Today"),
        (datetime(2026, 11, 9, 23, 59), "Yesterday"),
        (datetime(2026, 11, 7, 12, 0), "3 days ago"),
        (datetime(2026, 10, 20, 12, 0), "3 weeks ago"),
        (datetime(2026, 8, 1, 12, 0), "1 Aug"),
        (datetime(2025, 8, 1, 12, 0), "1 Aug 2025"),
    ],
)
def test_days_ago(when, text):
    assert days_ago(when, NOW) == text
