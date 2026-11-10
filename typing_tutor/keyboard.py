"""US QWERTY layout and which finger presses each key.

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
    "R5": "0-=p[]\\;'/",
}
_FINGER_BY_CHAR = {c: f for f, chars in _FINGER_CHARS.items() for c in chars}
_SHIFTED = dict(zip("`1234567890-=[]\\;',./", '~!@#$%^&*()_+{}|:"<>?', strict=True))


@dataclass(frozen=True)
class Key:
    ident: str
    label: str
    normal: str | None = None
    shifted: str | None = None
    width: float = 1.0
    fingers: tuple[str, ...] = ()
    bump: bool = False


def _char(c: str, width: float = 1.0) -> Key:
    return Key(
        ident=c,
        label=c.upper() if c.isalpha() else c,
        normal=c,
        shifted=_SHIFTED.get(c, c.upper()),
        width=width,
        fingers=(_FINGER_BY_CHAR[c],),
        bump=c in "fj",
    )


def _special(ident: str, label: str, width: float, fingers: tuple[str, ...] = ()) -> Key:
    return Key(ident=ident, label=label, width=width, fingers=fingers)


LEFT_SHIFT = _special("lshift", "Shift", 2.25, ("L5",))
RIGHT_SHIFT = _special("rshift", "Shift", 2.75, ("R5",))
SPACE = Key(ident="space", label="", normal=" ", width=6.25, fingers=("LT", "RT"))

ROWS: tuple[tuple[Key, ...], ...] = (
    (*map(_char, "`1234567890-="), _special("backspace", "Backspace", 2.0, ("R5",))),
    (_special("tab", "Tab", 1.5, ("L5",)), *map(_char, "qwertyuiop[]"), _char("\\", 1.5)),
    (
        _special("caps", "Caps Lock", 1.75, ("L5",)),
        *map(_char, "asdfghjkl;'"),
        _special("enter", "Enter", 2.25, ("R5",)),
    ),
    (LEFT_SHIFT, *map(_char, "zxcvbnm,./"), RIGHT_SHIFT),
    (
        _special("lctrl", "Ctrl", 1.25),
        _special("lsuper", "", 1.25),
        _special("lalt", "Alt", 1.25),
        SPACE,
        _special("ralt", "Alt", 1.25),
        _special("rsuper", "", 1.25),
        _special("menu", "", 1.25),
        _special("rctrl", "Ctrl", 1.25),
    ),
)
ROW_UNITS = 15.0


def keys_for_char(ch: str) -> list[Key]:
    """The key(s) to press for a character, including Shift when needed."""
    for row in ROWS:
        for key in row:
            if key.normal == ch:
                return [key]
            if key.shifted == ch:
                # Shift goes on the opposite hand from the key.
                shift = RIGHT_SHIFT if key.fingers[0].startswith("L") else LEFT_SHIFT
                return [key, shift]
    return []


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
    }
    if ch in names:
        return names[ch]
    if ch.isalpha():
        return f"capital {ch}" if ch.isupper() else ch.upper()
    return ch
