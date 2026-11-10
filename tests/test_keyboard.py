import string

import pytest

from typing_tutor.keyboard import (
    LEFT_SHIFT,
    RIGHT_SHIFT,
    ROW_UNITS,
    ROWS,
    SPACE,
    char_name,
    finger_hint,
    fingers_for_char,
    keys_for_char,
)
from typing_tutor.lessons import KNOWN


def test_every_row_is_the_same_width():
    for row in ROWS:
        assert sum(k.width for k in row) == pytest.approx(ROW_UNITS)


def test_key_idents_are_unique():
    idents = [k.ident for row in ROWS for k in row]
    assert len(idents) == len(set(idents))


def test_every_character_in_the_course_can_be_typed():
    taught = set().union(*KNOWN.values())
    assert all(keys_for_char(ch) for ch in taught), taught


@pytest.mark.parametrize("ch", string.ascii_letters + string.digits + ".,;'/?")
def test_common_characters_have_a_key_and_finger(ch):
    assert keys_for_char(ch)
    assert fingers_for_char(ch)


def test_capitals_use_shift_on_the_other_hand():
    assert keys_for_char("J")[1] is LEFT_SHIFT  # J is right hand
    assert keys_for_char("F")[1] is RIGHT_SHIFT  # F is left hand
    assert fingers_for_char("J") == ("R2", "L5")


def test_space_is_for_thumbs():
    assert keys_for_char(" ") == [SPACE]
    assert finger_hint(" ") == "thumb"


def test_finger_hints():
    assert finger_hint("f") == "left pointer finger"
    assert finger_hint(";") == "right pinky"
    assert finger_hint("J") == "right pointer finger, holding Shift with your left pinky"
    assert finger_hint("€") == ""


@pytest.mark.parametrize(
    ("ch", "name"),
    [
        ("f", "F"),
        ("F", "capital F"),
        (" ", "SPACE"),
        (";", "; (semicolon)"),
        ("7", "7"),
    ],
)
def test_char_names(ch, name):
    assert char_name(ch) == name
