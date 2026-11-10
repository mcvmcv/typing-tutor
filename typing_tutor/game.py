"""Balloon Pop: the game rules, independent of drawing.

Balloons carrying words rise from the bottom (y=1) to the top (y=0). Typing a
word's first letter targets that balloon; finishing the word pops it. A balloon
that floats off the top costs a life.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from .session import MAX_KEY_GAP
from .wordlist import WORDS

LIVES = 3
POPS_PER_LEVEL = 8
MAX_BALLOONS = 6
MIN_WORDS = 8  # the game needs this many typeable words to unlock
START_Y, ESCAPE_Y = 1.15, -0.12


@dataclass(frozen=True)
class Difficulty:
    key: str
    label: str
    rise_seconds: float  # time to cross the screen at level 1
    spawn_seconds: float  # time between balloons at level 1
    max_word_len: int


DIFFICULTIES = {
    "easy": Difficulty("easy", "Easy", 14.0, 3.4, 4),
    "medium": Difficulty("medium", "Medium", 10.0, 2.5, 6),
    "hard": Difficulty("hard", "Hard", 7.0, 1.8, 99),
}


@dataclass
class Balloon:
    word: str
    x: float  # 0..1 across the screen
    y: float  # 0 top .. 1 bottom
    speed: float  # screen heights per second
    color: int  # index into the drawing palette
    typed: int = 0
    popped_at: float | None = None

    @property
    def active(self) -> bool:
        return self.popped_at is None


@dataclass
class Event:
    kind: str  # "hit", "miss", "pop", "escape", "level", "over"
    balloon: Balloon | None = None
    points: int = 0


@dataclass
class GameState:
    difficulty: Difficulty
    words: list[str]
    rng: random.Random = field(default_factory=random.Random)
    time: float = 0.0
    score: int = 0
    lives: int = LIVES
    level: int = 1
    popped: int = 0
    combo: int = 0
    correct_keys: int = 0
    balloons: list[Balloon] = field(default_factory=list)
    target: Balloon | None = None
    over: bool = False
    key_stats: dict[str, dict[str, float]] = field(default_factory=dict)
    _next_spawn: float = 0.5
    _last_ok_at: float | None = None
    _color_turn: int = 0

    # Difficulty curve ---------------------------------------------------

    def rise_seconds(self) -> float:
        return max(3.5, self.difficulty.rise_seconds * 0.92 ** (self.level - 1))

    def spawn_seconds(self) -> float:
        return max(0.8, self.difficulty.spawn_seconds * 0.92 ** (self.level - 1))

    # Spawning -----------------------------------------------------------

    def _pick_word(self) -> str:
        short = [w for w in self.words if len(w) <= self.difficulty.max_word_len]
        pool = short if len(short) >= MIN_WORDS else self.words
        taken = {b.word[0] for b in self.balloons if b.active}
        fresh = [w for w in pool if w[0] not in taken]
        return self.rng.choice(fresh or pool)

    def _pick_x(self) -> float:
        # Choose the spot farthest from balloons still low on the screen.
        low = [b.x for b in self.balloons if b.active and b.y > 0.6]
        candidates = [0.1 + 0.8 * self.rng.random() for _ in range(8)]
        if not low:
            return candidates[0]
        return max(candidates, key=lambda x: min(abs(x - o) for o in low))

    def spawn(self) -> Balloon:
        balloon = Balloon(
            word=self._pick_word(),
            x=self._pick_x(),
            y=START_Y,
            speed=(START_Y - ESCAPE_Y) / self.rise_seconds() * self.rng.uniform(0.9, 1.1),
            color=self._color_turn,
        )
        self._color_turn += 1
        self.balloons.append(balloon)
        return balloon

    # Time ---------------------------------------------------------------

    def update(self, dt: float) -> list[Event]:
        if self.over:
            return []
        events: list[Event] = []
        self.time += dt
        self._next_spawn -= dt
        if self._next_spawn <= 0 and sum(b.active for b in self.balloons) < MAX_BALLOONS:
            self.spawn()
            self._next_spawn = self.spawn_seconds()
        for b in self.balloons:
            if not b.active:
                continue
            b.y -= b.speed * dt
            if b.y < ESCAPE_Y:
                b.popped_at = self.time
                self.lives -= 1
                self.combo = 0
                if self.target is b:
                    self.target = None
                events.append(Event("escape", b))
                if self.lives <= 0:
                    self.over = True
                    events.append(Event("over"))
                    break
        # Forget balloons whose pop or escape has finished animating.
        self.balloons = [b for b in self.balloons if not self._finished_animating(b)]
        return events

    def _finished_animating(self, b: Balloon) -> bool:
        return b.popped_at is not None and self.time - b.popped_at >= 0.6

    # Typing -------------------------------------------------------------

    def _stats(self, ch: str) -> dict[str, float]:
        return self.key_stats.setdefault(ch, {"h": 0, "m": 0, "t": 0.0, "n": 0})

    def type(self, ch: str) -> list[Event]:
        if self.over:
            return []
        target = self.target
        if target is None:
            # The highest balloon is the most urgent one.
            matches = [b for b in self.balloons if b.active and b.word.startswith(ch)]
            if not matches:
                self.combo = 0
                return [Event("miss")]
            target = self.target = min(matches, key=lambda b: b.y)
            self._last_ok_at = None  # don't time the hunt for a new word
        expected = target.word[target.typed]
        stats = self._stats(expected)
        if ch != expected:
            stats["m"] += 1
            self.combo = 0
            return [Event("miss", target)]
        stats["h"] += 1
        if self._last_ok_at is not None and self.time - self._last_ok_at <= MAX_KEY_GAP:
            stats["t"] += self.time - self._last_ok_at
            stats["n"] += 1
        self._last_ok_at = self.time
        self.correct_keys += 1
        target.typed += 1
        if target.typed < len(target.word):
            return [Event("hit", target)]
        return self._pop(target)

    def _pop(self, balloon: Balloon) -> list[Event]:
        balloon.popped_at = self.time
        self.target = None
        self.popped += 1
        self.combo += 1
        points = 10 * len(balloon.word) + 5 * min(self.combo - 1, 10)
        self.score += points
        events = [Event("pop", balloon, points)]
        if self.popped % POPS_PER_LEVEL == 0:
            self.level += 1
            events.append(Event("level"))
        return events

    def wpm(self) -> float:
        minutes = self.time / 60
        return (self.correct_keys / 5) / minutes if minutes > 1 / 60 else 0.0


def game_words(known: frozenset[str]) -> list[str]:
    """Lowercase words the player can type with the keys they've learned."""
    return [w for w in WORDS if len(w) >= 2 and set(w) <= known]
