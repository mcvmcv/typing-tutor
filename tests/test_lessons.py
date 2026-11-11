import random

import pytest

from typing_tutor.generator import build_lines
from typing_tutor.lessons import (
    ALL_STEPS,
    HOME_ROW,
    KNOWN,
    LESSONS,
    PUNCTUATION,
    first_unfinished,
    is_unlocked,
    next_step,
)


def stars_from(done: set[str]):
    return lambda step_id: 3 if step_id in done else 0


def test_course_shape():
    assert len(LESSONS) == 7
    assert len(ALL_STEPS) == 44


def test_step_ids_are_unique():
    ids = [lesson.step_id(i) for lesson, i in ALL_STEPS]
    assert len(ids) == len(set(ids))


def test_known_keys_only_grow():
    previous = frozenset()
    for lesson, i in ALL_STEPS:
        known = KNOWN[lesson.step_id(i)]
        assert previous <= known
        previous = known
    assert {"a", "z", "A", "Z", "0", "9", "?", "'"} <= previous


def test_every_step_introduces_keys_or_practises_them():
    for lesson, i in ALL_STEPS:
        step = lesson.steps[i]
        assert step.title and step.instruction
        assert step.kind in {"drill", "words", "sentences", "numbers", "story"}
        assert step.line_count >= len(step.lines) >= (step.kind == "story")


def test_hand_written_lines_only_use_known_keys():
    for lesson, i in ALL_STEPS:
        known = KNOWN[lesson.step_id(i)]
        for line in lesson.steps[i].lines:
            assert set(line) <= known, (lesson.step_id(i), set(line) - known)


def test_only_the_first_step_starts_unlocked():
    nothing = stars_from(set())
    assert is_unlocked(nothing, HOME_ROW, 0)
    assert not is_unlocked(nothing, HOME_ROW, 1)


def test_finishing_a_step_unlocks_the_next_one_across_lessons():
    last_home = HOME_ROW.step_id(len(HOME_ROW.steps) - 1)
    lesson, index = ALL_STEPS[len(HOME_ROW.steps)]
    assert is_unlocked(stars_from({last_home}), lesson, index)


def test_a_step_with_stars_is_never_locked():
    assert is_unlocked(stars_from({HOME_ROW.step_id(5)}), HOME_ROW, 5)


def test_next_step_and_first_unfinished():
    assert next_step(HOME_ROW, 0) == (HOME_ROW, 1)
    assert next_step(*ALL_STEPS[-1]) is None
    done = {lesson.step_id(i) for lesson, i in ALL_STEPS[:3]}
    assert first_unfinished(stars_from(done)) == ALL_STEPS[3]
    everything = {lesson.step_id(i) for lesson, i in ALL_STEPS}
    assert first_unfinished(stars_from(everything)) is None


def test_punctuation_lesson_comes_before_the_stories():
    keys = [lesson.key for lesson in LESSONS]
    assert keys.index("punctuation") == keys.index("stories") - 1


def test_quote_marks_are_explained_for_each_keyboard():
    quotes = PUNCTUATION.steps[1]
    assert "press '" in quotes.instruction_for("us")
    assert "press 2" in quotes.instruction_for("uk")
    assert quotes.instruction_for("dvorak") == quotes.instruction


@pytest.mark.parametrize("index", range(len(PUNCTUATION.steps)))
def test_punctuation_steps_practise_their_new_marks(index):
    step = PUNCTUATION.steps[index]
    lines = build_lines(PUNCTUATION, index, random.Random(index))
    assert len(lines) == step.line_count
    assert all(set(line) <= KNOWN[PUNCTUATION.step_id(index)] for line in lines)
    assert set(step.new) <= set("".join(lines))


def test_new_marks_never_appear_before_they_are_taught():
    for lesson, i in ALL_STEPS:
        if lesson is PUNCTUATION:
            break
        for line in build_lines(lesson, i, random.Random(i)):
            assert not set(line) & set('!"-:'), (lesson.key, line)
