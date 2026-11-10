import pytest

from typing_tutor.session import CharState, StepRun, TypingSession, merge_key_stats, stars_for


def type_text(session, text, clock=None, gap=0.0):
    for ch in text:
        if clock is not None:
            clock.advance(gap)
        session.press(ch)


def test_correct_keys_advance_and_wrong_keys_do_not():
    s = TypingSession("ab")
    assert s.press("a") is True
    assert s.press("x") is False
    assert s.pos == 1 and s.error_at_cursor
    assert s.press("b") is True
    assert s.finished and s.expected is None
    assert s.press("b") is False  # typing after the end is ignored


def test_char_states_record_first_try_versus_corrected():
    s = TypingSession("ab")
    s.press("a")
    s.press("z")
    s.press("b")
    assert s.states == [CharState.CORRECT, CharState.CORRECTED]


def test_accuracy_counts_every_keystroke():
    s = TypingSession("abcd")
    type_text(s, "axbcd")
    assert s.mistakes == 1
    assert s.accuracy() == pytest.approx(100 * 4 / 5)


def test_accuracy_is_full_before_typing():
    assert TypingSession("abc").accuracy() == 100.0


def test_wpm_uses_five_characters_per_word(clock):
    s = TypingSession("a" * 11, clock)
    s.press("a")  # starts the timer
    type_text(s, "a" * 10, clock, gap=1.2)
    # 11 chars in 12 seconds = 2.2 words in 0.2 minutes
    assert s.wpm() == pytest.approx(11.0)


def test_wpm_is_zero_for_under_a_second(clock):
    s = TypingSession("abc", clock)
    type_text(s, "abc", clock, gap=0.1)
    assert s.wpm() == 0.0


def test_key_stats_track_hits_misses_and_timing(clock):
    s = TypingSession("fj", clock)
    s.press("f")
    clock.advance(0.4)
    s.press("k")
    clock.advance(0.2)
    s.press("j")
    assert s.key_stats["f"] == {"h": 1, "m": 0, "t": 0.0, "n": 0}  # first key isn't timed
    assert s.key_stats["j"]["h"] == 1 and s.key_stats["j"]["m"] == 1
    assert s.key_stats["j"]["t"] == pytest.approx(0.6)


def test_long_pauses_are_not_counted_as_slow_keys(clock):
    s = TypingSession("ab", clock)
    s.press("a")
    clock.advance(10)
    s.press("b")
    assert s.key_stats["b"]["n"] == 0


def test_step_run_moves_through_lines_and_totals_stats(clock):
    run = StepRun(["ab", "cd"], clock)
    type_text(run.current, "ab", clock, gap=0.5)
    assert run.advance() and run.index == 1 and run.on_last_line
    type_text(run.current, "xcd", clock, gap=0.5)
    assert run.advance() is False
    assert run.finished
    assert (run.typed_chars, run.total_chars, run.mistakes) == (4, 4, 1)
    assert run.accuracy() == pytest.approx(80.0)
    assert run.key_stats()["c"]["m"] == 1


def test_step_run_speed_ignores_the_pause_between_lines(clock):
    run = StepRun(["aaaaa", "aaaaa"], clock)
    type_text(run.current, "aaaaa", clock, gap=1.0)
    run.advance()
    clock.advance(60)  # a long break between lines
    type_text(run.current, "aaaaa", clock, gap=1.0)
    # 10 chars over 8 seconds of actual typing (first key of each line starts its timer)
    assert run.wpm() == pytest.approx((10 / 5) / (8 / 60))


@pytest.mark.parametrize(
    ("accuracy", "wpm", "goal", "stars"),
    [
        (98, 0, 0, 3),
        (95, 0, 0, 3),
        (90, 0, 0, 2),
        (85, 0, 0, 2),
        (70, 0, 0, 1),
        (98, 25, 20, 3),  # goal reached
        (98, 14, 20, 2),  # at least 70% of the goal
        (98, 13, 20, 1),
        (80, 50, 20, 1),  # speed can't make up for accuracy
    ],
)
def test_stars(accuracy, wpm, goal, stars):
    assert stars_for(accuracy, wpm, goal) == stars


def test_merge_key_stats_adds_fields():
    into = {"a": {"h": 1, "m": 1, "t": 0.5, "n": 1}}
    merge_key_stats(
        into, {"a": {"h": 2, "m": 0, "t": 1.0, "n": 2}, "b": {"h": 1, "m": 0, "t": 0.0, "n": 0}}
    )
    assert into["a"] == {"h": 3, "m": 1, "t": 1.5, "n": 3}
    assert into["b"]["h"] == 1
