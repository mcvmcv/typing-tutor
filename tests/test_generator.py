import random

import pytest

from typing_tutor.generator import build_lines, sentence_pool
from typing_tutor.lessons import ALL_STEPS, BOTTOM_ROW, CAPITALS, KNOWN, TOP_ROW
from typing_tutor.wordlist import WORDS

STEP_PARAMS = [pytest.param(lesson, i, id=lesson.step_id(i)) for lesson, i in ALL_STEPS]


@pytest.mark.parametrize(("lesson", "index"), STEP_PARAMS)
def test_generated_lines_only_use_taught_keys(lesson, index):
    known = KNOWN[lesson.step_id(index)]
    step = lesson.steps[index]
    for seed in range(25):
        lines = build_lines(lesson, index, random.Random(seed))
        assert len(lines) == step.line_count
        assert lines[: len(step.lines)] == list(step.lines)
        for line in lines:
            assert line and line == line.strip() and "  " not in line
            assert set(line) <= known, set(line) - known


def test_lines_vary_between_plays():
    plays = {tuple(build_lines(TOP_ROW, 0, random.Random(seed))) for seed in range(10)}
    assert len(plays) > 5


def test_same_seed_gives_same_lines():
    assert build_lines(TOP_ROW, 0, random.Random(7)) == build_lines(TOP_ROW, 0, random.Random(7))


def test_drill_steps_finish_with_real_words():
    for seed in range(10):
        last = build_lines(TOP_ROW, 0, random.Random(seed))[-1]
        assert all(word in WORDS for word in last.split())


def test_capital_drills_put_capitals_before_lowercase():
    line = build_lines(CAPITALS, 0, random.Random(1))[0]
    for token in line.split():
        if token[0].isupper() and len(token) > 1 and token[1].isalpha():
            assert token[1:].islower() or token.isupper()


def test_sentences_are_lowercased_before_shift_is_taught():
    pool = sentence_pool(KNOWN[TOP_ROW.step_id(6)])
    assert pool and all(s == s.lower() for s in pool)
    assert all("." not in s for s in pool)


def test_sentences_keep_full_stops_once_taught():
    pool = sentence_pool(KNOWN[BOTTOM_ROW.step_id(6)])
    assert any(s.endswith(".") for s in pool)
