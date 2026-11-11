"""Keyboard layouts (US and UK QWERTY) and which finger presses each key.

Finger codes: L/R for the hand, then 5=pinky, 4=ring, 3=middle, 2=pointer,
T=thumb.
"""

from __future__ import annotations

from dataclasses import dataclass

FINGER_NAMES = {
    "L5": "left pinky",
    "L4": "left ring finger",
    "L3": "left middle finger",
    "L2": "left pointer finger",
    "LT": "left thumb",
    "RT": "right thumb",
    "R2": "right pointer finger",
    "R3": "right middle finger",
    "R4": "right ring finger",
    "R5": "right pinky",
}

HOME_KEYS = {"L5": "a", "L4": "s", "L3": "d", "L2": "f", "R2": "j", "R3": "k", "R4": "l", "R5": ";"}

_FINGER_CHARS = {
    "L5": "`1qaz",
    "L4": "2wsx",
    "L3": "3edc",
    "L2": "45rtfgvb",
    "R2": "67yuhjnm",
    "R3": "8ik,",
    "R4": "9ol.",
    "R5": "0-=p[];'/#",
}
_FINGER_BY_CHAR = {c: f for f, chars in _FINGER_CHARS.items() for c in chars}


@dataclass(frozen=True)
class Key:
    ident: str
    label: str
    normal: str | None = None
    shifted: str | None = None
    width: float = 1.0
    fingers: tuple[str, ...] = ()
    bump: bool = False
    # "iso-enter": the tall L-shaped Enter that drops into the row below,
    # where a "blank" key holds its place.
    shape: str = "rect"


def _char(c: str, shifted: str, width: float = 1.0, finger: str | None = None) -> Key:
    return Key(
        ident=c,
        label=c.upper() if c.isalpha() else c,
        normal=c,
        shifted=shifted,
        width=width,
        fingers=(finger or _FINGER_BY_CHAR[c],),
        bump=c in "fj",
    )


def _chars(normal: str, shifted: str) -> list[Key]:
    return [_char(c, s) for c, s in zip(normal, shifted, strict=True)]


def _special(ident: str, label: str, width: float, fingers: tuple[str, ...] = ()) -> Key:
    return Key(ident=ident, label=label, width=width, fingers=fingers)


SPACE = Key(ident="space", label="", normal=" ", width=6.25, fingers=("LT", "RT"))
_BOTTOM_ROW = (
    _special("lctrl", "Ctrl", 1.25),
    _special("lsuper", "", 1.25),
    _special("lalt", "Alt", 1.25),
    SPACE,
    _special("ralt", "Alt", 1.25),
    _special("rsuper", "", 1.25),
    _special("menu", "", 1.25),
    _special("rctrl", "Ctrl", 1.25),
)
_BACKSPACE = _special("backspace", "Backspace", 2.0, ("R5",))
_TAB = _special("tab", "Tab", 1.5, ("L5",))
_CAPS = _special("caps", "Caps Lock", 1.75, ("L5",))
LETTERS = "qwertyuiopasdfghjklzxcvbnm"


@dataclass(frozen=True)
class Layout:
    code: str
    name: str  # what grown-ups pick from, e.g. "UK"
    description: str
    rows: tuple[tuple[Key, ...], ...]
    left_shift: Key
    right_shift: Key

    def keys_for_char(self, ch: str) -> list[Key]:
        """The key(s) to press for a character, including Shift when needed."""
        for row in self.rows:
            for key in row:
                if key.normal == ch:
                    return [key]
                if key.shifted == ch:
                    # Shift goes on the opposite hand from the key.
                    left = key.fingers[0].startswith("L")
                    return [key, self.right_shift if left else self.left_shift]
        return []


# US (ANSI): a wide one-row Enter and \ above it.
LEFT_SHIFT = _special("lshift", "Shift", 2.25, ("L5",))
RIGHT_SHIFT = _special("rshift", "Shift", 2.75, ("R5",))
US = Layout(
    code="us",
    name="US",
    description="Shift+2 is @ and Shift+' is \"",
    rows=(
        (*_chars("`1234567890-=", "~!@#$%^&*()_+"), _BACKSPACE),
        (_TAB, *_chars("qwertyuiop[]", "QWERTYUIOP{}"), _char("\\", "|", 1.5, "R5")),
        (_CAPS, *_chars("asdfghjkl;'", 'ASDFGHJKL:"'), _special("enter", "Enter", 2.25, ("R5",))),
        (LEFT_SHIFT, *_chars("zxcvbnm,./", "ZXCVBNM<>?"), RIGHT_SHIFT),
        _BOTTOM_ROW,
    ),
    left_shift=LEFT_SHIFT,
    right_shift=RIGHT_SHIFT,
)

# UK (ISO): a tall Enter with # beside it, \ next to a short left Shift,
# " on 2 and @ on '.
_UK_LEFT_SHIFT = _special("lshift", "Shift", 1.25, ("L5",))
UK = Layout(
    code="uk",
    name="UK",
    description="Shift+2 is \" and Shift+' is @, with a # key by Enter",
    rows=(
        (*_chars("`1234567890-=", '¬!"£$%^&*()_+'), _BACKSPACE),
        (
            _TAB,
            *_chars("qwertyuiop[]", "QWERTYUIOP{}"),
            Key(ident="enter", label="Enter", width=1.5, fingers=("R5",), shape="iso-enter"),
        ),
        (
            _CAPS,
            *_chars("asdfghjkl;'#", "ASDFGHJKL:@~"),
            Key(ident="enter-below", label="", width=1.25, shape="blank"),
        ),
        (
            _UK_LEFT_SHIFT,
            _char("\\", "|", 1.0, "L5"),
            *_chars("zxcvbnm,./", "ZXCVBNM<>?"),
            RIGHT_SHIFT,
        ),
        _BOTTOM_ROW,
    ),
    left_shift=_UK_LEFT_SHIFT,
    right_shift=RIGHT_SHIFT,
)

LAYOUTS = {layout.code: layout for layout in (US, UK)}
ROWS = US.rows
ROW_UNITS = 15.0

# The keyboard everything uses. One per computer, so it's app-wide rather than
# per player; the app sets it from the saved choice at start-up.
_current = US


def current() -> Layout:
    return _current


def set_layout(code: str) -> Layout:
    global _current
    _current = LAYOUTS.get(code, US)
    return _current


def system_layout() -> str:
    """A best guess at the keyboard from the computer's region: UK in the UK and Ireland."""
    from PySide6.QtCore import QLocale

    territory = QLocale.system().territory()
    uk = (QLocale.Country.UnitedKingdom, QLocale.Country.Ireland)
    return "uk" if territory in uk else "us"


def keys_for_char(ch: str) -> list[Key]:
    """The key(s) to press for a character on the current keyboard."""
    return _current.keys_for_char(ch)


def fingers_for_char(ch: str) -> tuple[str, ...]:
    fingers: list[str] = []
    for key in keys_for_char(ch):
        fingers.extend(f for f in key.fingers if f not in fingers)
    return tuple(fingers)


def finger_hint(ch: str) -> str:
    keys = keys_for_char(ch)
    if not keys:
        return ""
    if ch == " ":
        return "thumb"
    main = FINGER_NAMES[keys[0].fingers[0]]
    if len(keys) > 1:
        return f"{main}, holding Shift with your {FINGER_NAMES[keys[1].fingers[0]]}"
    return main


def char_name(ch: str) -> str:
    names = {
        " ": "SPACE",
        ";": "; (semicolon)",
        "'": "' (apostrophe)",
        ",": ", (comma)",
        ".": ". (full stop)",
        "/": "/ (slash)",
        "?": "? (question mark)",
        "!": "! (exclamation mark)",
        "-": "- (hyphen)",
        ":": ": (colon)",
        '"': '" (quote marks)',
        "#": "# (hash)",
        "\\": "\\ (backslash)",
    }
    if ch in names:
        return names[ch]
    if ch.isalpha():
        return f"capital {ch}" if ch.isupper() else ch.upper()
    return ch
