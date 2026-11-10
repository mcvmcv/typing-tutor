"""Builds practice lines for a step from the keys the child knows."""
from __future__ import annotations

import random

from .keyboard import HOME_KEYS, keys_for_char
from .lessons import KNOWN, Lesson, Step
from .wordlist import NAMES, SENTENCES, WORDS

LINE_LEN = 44       # target length for drill and word lines
SENTENCE_MAX = 54   # a sentence line may run a little longer
FOCUS_SHARE = 0.7   # how often to pick something featuring the new keys
MIN_FOCUS_WORDS = 6


def build_lines(lesson: Lesson, index: int, rng: random.Random | None = None) -> list[str]:
    """All the lines for one play of a step: hand-written first, then fresh ones."""
    rng = rng or random.Random()
    step = lesson.steps[index]
    known = KNOWN[lesson.step_id(index)]
    lines = list(step.lines)
    new = [c for c in step.new if c in known]
    # Drill steps finish with real words that use the new keys, when there are enough.
    words_last = step.kind == "drill" and len(_word_pools(new, known)[0]) >= MIN_FOCUS_WORDS
    attempts = 0
    while len(lines) < step.line_count:
        if words_last and len(lines) == step.line_count - 1:
            line = words_line(new, known, rng)
        else:
            line = _generate(step, known, rng)
        attempts += 1
        if line and (line not in lines or attempts > 20):
            lines.append(line)
    return lines


def _generate(step: Step, known: frozenset[str], rng: random.Random) -> str:
    new = [c for c in step.new if c in known] or sorted(known - {" "})
    if step.kind == "words":
        return words_line(new, known, rng)
    if step.kind == "sentences":
        return sentence_line(new, known, rng)
    if step.kind == "numbers":
        return numbers_line(known, rng)
    return drill_line(new, known, rng)


def _fill(make_token, rng: random.Random, length: int = LINE_LEN) -> str:
    """Join tokens with spaces up to about `length`, avoiding repeats in a row."""
    parts: list[str] = []
    size = 0
    tries = 0
    while tries < 200:
        tries += 1
        token = make_token()
        if parts and token == parts[-1]:
            continue
        extra = len(token) + (1 if parts else 0)
        if parts and size + extra > length:
            break
        parts.append(token)
        size += extra
    return " ".join(parts)


def _home_anchor(ch: str) -> str | None:
    """The home key of the finger that types ch, e.g. 'd' for 'e'."""
    keys = keys_for_char(ch)
    if not keys or not keys[0].fingers:
        return None
    home = HOME_KEYS.get(keys[0].fingers[0])
    return home if home and home != ch else None


def drill_line(new: list[str], known: frozenset[str], rng: random.Random) -> str:
    lower = [c for c in known if c.islower()] or ["f", "j"]
    if all(c.isdigit() for c in new):
        pool = new * 2 + [c for c in known if c.isdigit()]
    else:
        # New keys plus known letters; older punctuation is left out of drills.
        pool = [c for c in new if not c.isupper()] * 3 + lower

    def token() -> str:
        c = rng.choice(new)
        r = rng.random()
        if r < 0.25:
            return c * 3
        anchor = _home_anchor(c)
        if r < 0.5 and anchor:
            return anchor + c + anchor   # e.g. "ded": reach up and come back
        if c.isupper():
            return c + "".join(rng.choice(lower) for _ in range(rng.randint(1, 3)))
        group = [rng.choice(pool) for _ in range(rng.randint(2, 4))]
        if not any(g in new for g in group):
            group[rng.randrange(len(group))] = c
        return "".join(group)

    return _fill(token, rng)


def _word_pools(new: list[str], known: frozenset[str]) -> tuple[list[str], list[str]]:
    words = [w for w in WORDS if set(w) <= known]
    capitals = [c for c in new if c.isupper()]
    if capitals:
        names = [n for n in NAMES if n[0] in capitals and set(n) <= known]
        capped = [w.capitalize() for w in words if w[0].upper() in capitals]
        focus = names + capped
    else:
        focus = [w for w in words if set(w) & set(new)]
    return focus, words


def words_line(new: list[str], known: frozenset[str], rng: random.Random) -> str:
    focus, words = _word_pools(new, known)
    if not words:
        return drill_line(new, known, rng)

    def token() -> str:
        if focus and rng.random() < FOCUS_SHARE:
            return rng.choice(focus)
        return rng.choice(words)

    return _fill(token, rng)


def _adapt_sentence(sentence: str, known: frozenset[str]) -> str | None:
    """Fit a sentence to the known keys, or None if it can't be typed yet."""
    s = sentence
    if not any(c.isupper() for c in known):
        s = s.lower()
    for mark in ".,":
        if mark not in known:
            s = s.replace(mark, "")
    return s if set(s) <= known else None


def sentence_pool(known: frozenset[str]) -> list[str]:
    pool = []
    for sentence in SENTENCES:
        adapted = _adapt_sentence(sentence, known)
        if adapted and adapted not in pool:
            pool.append(adapted)
    return pool


def sentence_line(new: list[str], known: frozenset[str], rng: random.Random) -> str:
    pool = sentence_pool(known)
    if len(pool) < 4:
        return _made_up_sentence(new, known, rng)
    focus = [s for s in pool if set(s) & set(new)]

    def pick() -> str:
        if focus and rng.random() < FOCUS_SHARE:
            return rng.choice(focus)
        return rng.choice(pool)

    line = pick()
    # Add a second short sentence if there's room.
    for _ in range(10):
        extra = pick()
        if extra != line and len(line) + 1 + len(extra) <= SENTENCE_MAX:
            joiner = " " if "." in known else "; " if ";" in known else " "
            return line + joiner + extra
    return line


def _made_up_sentence(new: list[str], known: frozenset[str], rng: random.Random) -> str:
    """Strings of words for stages too early for the sentence bank."""
    focus, words = _word_pools(new, known)
    words = words or ["a"]
    groups = []
    while sum(len(g) + 2 for g in groups) < LINE_LEN - 8:
        group = " ".join(rng.choice(words if rng.random() > 0.5 or not focus else focus)
                         for _ in range(rng.randint(2, 4)))
        groups.append(group)
    sep = "; " if ";" in known else " "
    return sep.join(groups)


def numbers_line(known: frozenset[str], rng: random.Random) -> str:
    digits = [c for c in known if c.isdigit()] or ["1"]
    words = [w for w in WORDS if set(w) <= known] or ["a"]

    def token() -> str:
        if rng.random() < 0.55:
            return "".join(rng.choice(digits) for _ in range(rng.randint(1, 3)))
        return rng.choice(words)

    return _fill(token, rng)
