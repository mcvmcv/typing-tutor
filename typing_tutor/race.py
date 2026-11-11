"""Snail Race: the race rules, independent of drawing.

The player's snail moves along the track one correct key at a time. A friendly
rival snail sets off at the same moment and moves at a steady pace, worked out
from the player's own recent typing speed, so every child gets a close race.
Mistakes don't move the player's snail backwards; it just waits for the right
key, like the lessons do. The race ends when the player reaches the finish,
even if the rival got there first.
"""

from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass, field

from .generator import LINE_LEN, sentence_pool, words_line
from .session import TypingSession

COUNTDOWN = 3.0  # seconds of "3, 2, 1" before the snails set off
DEFAULT_WPM = 8.0  # the rival's base pace before there's any typing to go on
MIN_PACE = 4.0
RACE_LEN = 58  # the race text aims for about this many characters
RIVAL_NAME = "Shelly"


@dataclass(frozen=True)
class RaceDifficulty:
    key: str
    label: str
    pace: float  # the rival's speed as a share of the player's recent speed


RACE_DIFFICULTIES = {
    "easy": RaceDifficulty("easy", "Easy", 0.7),
    "medium": RaceDifficulty("medium", "Medium", 0.9),
    "hard": RaceDifficulty("hard", "Hard", 1.1),
}


def recent_speed(history: list[dict], count: int = 10) -> float:
    """The player's typical speed: the median WPM of their last few steps."""
    speeds = [h["wpm"] for h in history[-count:] if h.get("wpm")]
    return statistics.median(speeds) if speeds else DEFAULT_WPM


def rival_pace(history: list[dict], difficulty: RaceDifficulty) -> float:
    return round(max(MIN_PACE, recent_speed(history) * difficulty.pace), 1)


def race_text(known: frozenset[str], rng: random.Random) -> str:
    """Something to race with, using only the keys the player knows."""
    pool = sentence_pool(known)
    if len(pool) >= 4:
        text = rng.choice(pool)
        for _ in range(20):
            extra = rng.choice(pool)
            if extra != text and len(text) + 1 + len(extra) <= RACE_LEN + 12:
                text += " " + extra
            if len(text) >= RACE_LEN - 10:
                break
        return text
    letters = sorted(c for c in known if c.isalpha())
    return words_line(letters, known, rng)[:LINE_LEN].rstrip()


@dataclass
class RaceEvent:
    kind: str  # "go", "hit", "miss", "rival-finished", "finish"


@dataclass
class RaceState:
    difficulty: RaceDifficulty
    text: str
    pace_wpm: float
    time: float = 0.0  # seconds since the countdown began
    finished_at: float | None = None
    rival_finished_at: float | None = None
    session: TypingSession = field(init=False)

    def __post_init__(self) -> None:
        self.session = TypingSession(self.text, clock=lambda: self.time)

    @property
    def started(self) -> bool:
        return self.time >= COUNTDOWN

    @property
    def countdown(self) -> int:
        """3, 2, 1 before the start, then 0."""
        return 0 if self.started else math.ceil(COUNTDOWN - self.time)

    @property
    def over(self) -> bool:
        return self.finished_at is not None

    @property
    def elapsed(self) -> float:
        """Racing time so far (or in total, once over)."""
        end = self.finished_at if self.finished_at is not None else self.time
        return max(0.0, end - COUNTDOWN)

    @property
    def player_progress(self) -> float:
        return self.session.pos / len(self.text)

    def rival_progress_at(self, t: float) -> float:
        chars = self.pace_wpm * 5 / 60 * max(0.0, t - COUNTDOWN)
        return min(1.0, chars / len(self.text))

    @property
    def rival_progress(self) -> float:
        return self.rival_progress_at(self.time)

    @property
    def won(self) -> bool:
        if self.finished_at is None:
            return False
        return self.rival_finished_at is None or self.finished_at <= self.rival_finished_at

    def wpm(self) -> float:
        minutes = self.elapsed / 60
        return (self.session.pos / 5) / minutes if minutes >= 1 / 60 else 0.0

    def update(self, dt: float) -> list[RaceEvent]:
        if self.over:
            return []
        was_started = self.started
        self.time += dt
        events = []
        if self.started and not was_started:
            events.append(RaceEvent("go"))
        if self.rival_finished_at is None and self.rival_progress >= 1.0:
            # When exactly the rival crossed the line, for a fair photo finish.
            needed = len(self.text) / (self.pace_wpm * 5 / 60)
            self.rival_finished_at = COUNTDOWN + needed
            events.append(RaceEvent("rival-finished"))
        return events

    def type(self, ch: str) -> list[RaceEvent]:
        if self.over or not self.started:
            return []
        if not self.session.press(ch):
            return [RaceEvent("miss")]
        if not self.session.finished:
            return [RaceEvent("hit")]
        self.finished_at = self.time
        return [RaceEvent("finish")]
