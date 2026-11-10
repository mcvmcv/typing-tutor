import string

import pytest
from PySide6.QtCore import QLocale

from typing_tutor.keyboard import (
    LAYOUTS,
    LEFT_SHIFT,
    RIGHT_SHIFT,
    ROW_UNITS,
    ROWS,
    SPACE,
    UK,
    US,
    char_name,
    current,
    finger_hint,
    fingers_for_char,
    keys_for_char,
    set_layout,
)
from typing_tutor.keyboard import system_layout as real_system_layout  # before conftest patches it
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


# Layouts -----------------------------------------------------------------


@pytest.fixture
def uk():
    yield set_layout("uk")
    set_layout("us")


@pytest.mark.parametrize("layout", LAYOUTS.values(), ids=lambda layout: layout.code)
def test_every_layout_is_rectangular_with_unique_keys(layout):
    for row in layout.rows:
        assert sum(k.width for k in row) == pytest.approx(ROW_UNITS)
    idents = [k.ident for row in layout.rows for k in row]
    assert len(idents) == len(set(idents))


@pytest.mark.parametrize("layout", LAYOUTS.values(), ids=lambda layout: layout.code)
def test_the_course_types_the_same_on_every_layout(layout):
    # Every taught key is in the same place with the same finger, so the
    # lessons' wording is right on both keyboards.
    taught = set().union(*KNOWN.values())
    for ch in taught:
        assert [k.fingers for k in layout.keys_for_char(ch)] == [
            k.fingers for k in US.keys_for_char(ch)
        ], ch


def test_uk_symbols(uk):
    assert current() is UK
    assert [k.ident for k in keys_for_char('"')] == ["2", "rshift"]
    assert [k.ident for k in keys_for_char("@")] == ["'", "lshift"]
    assert [k.ident for k in keys_for_char("£")] == ["3", "rshift"]
    assert [k.ident for k in keys_for_char("#")] == ["#"]
    assert [k.ident for k in keys_for_char("~")] == ["#", "lshift"]
    assert finger_hint("#") == "right pinky"
    assert finger_hint("\\") == "left pinky"
    assert finger_hint("|") == "left pinky, holding Shift with your right pinky"
    assert finger_hint("@") == "right pinky, holding Shift with your left pinky"


def test_us_symbols():
    assert current() is US
    assert [k.ident for k in keys_for_char('"')] == ["'", "lshift"]
    assert [k.ident for k in keys_for_char("@")] == ["2", "rshift"]
    assert keys_for_char("£") == []
    assert finger_hint("\\") == "right pinky"


def test_uk_has_a_tall_enter_and_a_short_left_shift():
    shapes = {k.ident: k for row in UK.rows for k in row}
    assert shapes["enter"].shape == "iso-enter"
    assert shapes["enter-below"].shape == "blank"
    assert UK.left_shift.width < US.left_shift.width


def test_an_unknown_layout_falls_back_to_us():
    assert set_layout("dvorak") is US


@pytest.mark.parametrize(
    ("locale", "code"), [("en_GB", "uk"), ("en_IE", "uk"), ("en_US", "us"), ("de_DE", "us")]
)
def test_system_layout_guesses_from_the_region(monkeypatch, locale, code):
    monkeypatch.setattr(QLocale, "system", lambda: QLocale(locale))
    assert real_system_layout() == code


@pytest.mark.parametrize(
    ("ch", "name"), [('"', '" (quote marks)'), ("#", "# (hash)"), ("\\", "\\ (backslash)")]
)
def test_symbol_names(ch, name):
    assert char_name(ch) == name
