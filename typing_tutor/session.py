"""Typing logic for one step, independent of the UI."""
from __future__ import annotations

import time
from enum import Enum


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
        if ch == self.text[self.pos]:
            missed = self.pos in self._missed
            self.states[self.pos] = CharState.CORRECTED if missed else CharState.CORRECT
            self.pos += 1
            self.error_at_cursor = False
            if self.finished:
                self.finished_at = now
            return True
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


def stars_for(accuracy: float) -> int:
    if accuracy >= 95:
        return 3
    if accuracy >= 85:
        return 2
    return 1
