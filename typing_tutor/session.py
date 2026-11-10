"""Typing logic for one step, independent of the UI."""
from __future__ import annotations

import time
from enum import Enum


MAX_KEY_GAP = 3.0   # seconds; slower keystrokes aren't counted toward key speed


class CharState(Enum):
    PENDING = 0
    CORRECT = 1     # typed right on the first try
    CORRECTED = 2   # typed right after at least one mistake


class TypingSession:
    """Tracks progress through a line of text.

    The cursor only moves forward on the correct key, which suits beginners:
    mistakes are counted, but they never pile up and need deleting.
    """

    def __init__(self, text: str, clock=time.monotonic):
        self.text = text
        self._clock = clock
        self.pos = 0
        self.states = [CharState.PENDING] * len(text)
        self.mistakes = 0
        self.error_at_cursor = False
        self._missed: set[int] = set()
        self.started_at: float | None = None
        self.finished_at: float | None = None
        # Per expected character: h=hits, m=misses, t=seconds over n timed hits.
        self.key_stats: dict[str, dict[str, float]] = {}
        self._last_ok_at: float | None = None

    @property
    def finished(self) -> bool:
        return self.pos >= len(self.text)

    @property
    def expected(self) -> str | None:
        return None if self.finished else self.text[self.pos]

    def press(self, ch: str) -> bool:
        """Handle a typed character. Returns True if it was correct."""
        if self.finished:
            return False
        now = self._clock()
        if self.started_at is None:
            self.started_at = now
        expected = self.text[self.pos]
        stats = self.key_stats.setdefault(expected, {"h": 0, "m": 0, "t": 0.0, "n": 0})
        if ch == expected:
            stats["h"] += 1
            if self._last_ok_at is not None:
                # Long pauses (looking away, chatting) would skew the timing.
                gap = now - self._last_ok_at
                if gap <= MAX_KEY_GAP:
                    stats["t"] += gap
                    stats["n"] += 1
            self._last_ok_at = now
            missed = self.pos in self._missed
            self.states[self.pos] = CharState.CORRECTED if missed else CharState.CORRECT
            self.pos += 1
            self.error_at_cursor = False
            if self.finished:
                self.finished_at = now
            return True
        stats["m"] += 1
        self._missed.add(self.pos)
        self.mistakes += 1
        self.error_at_cursor = True
        return False

    def accuracy(self) -> float:
        """Percentage of keystrokes that were correct."""
        total = self.pos + self.mistakes
        return 100.0 if total == 0 else 100.0 * self.pos / total

    def wpm(self) -> float:
        """Words per minute, using the standard 5 characters per word."""
        if self.started_at is None:
            return 0.0
        end = self.finished_at if self.finished_at is not None else self._clock()
        minutes = (end - self.started_at) / 60
        if minutes < 1 / 60:
            return 0.0
        return (self.pos / 5) / minutes


def stars_for(accuracy: float, wpm: float = 0.0, speed_goal: float = 0.0) -> int:
    """Stars from accuracy, capped by speed when a speed goal is set."""
    if accuracy >= 95:
        stars = 3
    elif accuracy >= 85:
        stars = 2
    else:
        stars = 1
    if speed_goal > 0:
        if wpm >= speed_goal:
            speed_stars = 3
        elif wpm >= speed_goal * 0.7:
            speed_stars = 2
        else:
            speed_stars = 1
        stars = min(stars, speed_stars)
    return stars


def merge_key_stats(into: dict, new: dict) -> dict:
    for ch, s in new.items():
        dest = into.setdefault(ch, {"h": 0, "m": 0, "t": 0.0, "n": 0})
        for field in ("h", "m", "t", "n"):
            dest[field] += s[field]
    return into


class StepRun:
    """One play of a step: several lines typed one after another."""

    def __init__(self, lines: list[str], clock=time.monotonic):
        self.lines = lines
        self.sessions = [TypingSession(line, clock) for line in lines]
        self.index = 0
        self._clock = clock

    @property
    def current(self) -> TypingSession:
        return self.sessions[self.index]

    @property
    def finished(self) -> bool:
        return all(s.finished for s in self.sessions)

    @property
    def on_last_line(self) -> bool:
        return self.index == len(self.sessions) - 1

    def advance(self) -> bool:
        if self.on_last_line:
            return False
        self.index += 1
        return True

    @property
    def total_chars(self) -> int:
        return sum(len(s.text) for s in self.sessions)

    @property
    def typed_chars(self) -> int:
        return sum(s.pos for s in self.sessions)

    @property
    def mistakes(self) -> int:
        return sum(s.mistakes for s in self.sessions)

    def accuracy(self) -> float:
        total = self.typed_chars + self.mistakes
        return 100.0 if total == 0 else 100.0 * self.typed_chars / total

    def wpm(self) -> float:
        """Speed across all lines, not counting pauses between lines."""
        seconds = 0.0
        for s in self.sessions:
            if s.started_at is not None:
                end = s.finished_at if s.finished_at is not None else self._clock()
                seconds += end - s.started_at
        if seconds < 1:
            return 0.0
        return (self.typed_chars / 5) / (seconds / 60)

    def key_stats(self) -> dict[str, dict[str, float]]:
        merged: dict = {}
        for s in self.sessions:
            merge_key_stats(merged, s.key_stats)
        return merged
