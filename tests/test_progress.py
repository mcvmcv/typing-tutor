import pytest

from typing_tutor.lessons import ALL_STEPS
from typing_tutor.progress import (
    MAX_ATTEMPT_POINTS,
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
