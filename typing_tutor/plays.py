"""What the practice screen plays: a course step or a tricky-keys review."""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass

from . import keyboard
from .generator import build_lines, drill_line, words_line
from .keyboard import char_name
from .lessons import ALL_STEPS, KNOWN, Lesson, next_step
from .storage import Profile

REVIEW_ID = "review"
DRILL_SPEED_SHARE = 0.75  # random letter groups are slower than real words
MIN_KEY_SAMPLES = 8  # keystrokes needed before judging a key
WEAK_THRESHOLD = 0.12  # scores below this aren't worth drilling
REVIEW_LINES = 4


@dataclass
class Play:
    step_id: str
    title: str
    instruction: str
    header: str  # e.g. "Home Row Heroes · step 3 of 9"
    make_lines: Callable[[], list[str]]  # called again for each retry
    speed_goal: float = 0.0  # WPM for full stars; 0 = accuracy only
    next_play: Callable[[], Play | None] | None = None
    review: bool = False


def lesson_play(lesson: Lesson, index: int, profile: Profile) -> Play:
    step = lesson.steps[index]
    goal = float(profile.speed_goal)
    if step.kind == "drill":
        goal *= DRILL_SPEED_SHARE

    def upcoming() -> Play | None:
        following = next_step(lesson, index)
        return lesson_play(*following, profile) if following else None

    return Play(
        step_id=lesson.step_id(index),
        title=step.title,
        instruction=step.instruction_for(keyboard.current().code),
        header=f"{lesson.title} · step {index + 1} of {len(lesson.steps)}",
        make_lines=lambda: build_lines(lesson, index),
        speed_goal=round(goal),
        next_play=upcoming,
    )


def known_keys(profile: Profile) -> frozenset[str]:
    """Every key taught up to the furthest step the player has finished."""
    known = KNOWN[ALL_STEPS[0][0].step_id(ALL_STEPS[0][1])]
    for lesson, i in ALL_STEPS:
        if profile.stars(lesson.step_id(i)) > 0:
            known = KNOWN[lesson.step_id(i)]
    return known


def key_scores(profile: Profile) -> dict[str, float]:
    """How tricky each key is: higher means more misses or slower presses."""
    known = known_keys(profile)
    stats = {
        k: v
        for k, v in profile.key_stats.items()
        if k in known and k != " " and v["h"] + v["m"] >= MIN_KEY_SAMPLES
    }
    if len(stats) < 3:
        return {}
    total_t = sum(v["t"] for v in stats.values())
    total_n = sum(v["n"] for v in stats.values())
    avg = total_t / total_n if total_n else 0.0
    scores = {}
    for k, v in stats.items():
        miss_rate = v["m"] / (v["h"] + v["m"])
        slowness = 0.0
        if avg > 0 and v["n"] >= 3:
            slowness = max(0.0, (v["t"] / v["n"]) / avg - 1)
        # A miss matters more than being a bit slow.
        scores[k] = miss_rate * 4 + slowness
    return scores


def weak_keys(profile: Profile, limit: int = 5) -> list[str]:
    scores = key_scores(profile)
    ranked = sorted(scores, key=lambda k: scores[k], reverse=True)
    return [k for k in ranked if scores[k] >= WEAK_THRESHOLD][:limit]


def review_lines(
    weak: list[str], known: frozenset[str], rng: random.Random | None = None
) -> list[str]:
    rng = rng or random.Random()
    lines: list[str] = []
    makers = [drill_line, words_line] * (REVIEW_LINES // 2)
    for make in makers:
        for _ in range(10):
            line = make(weak, known, rng)
            if line not in lines:
                break
        lines.append(line)
    return lines


def review_play(profile: Profile) -> Play | None:
    weak = weak_keys(profile)
    if not weak:
        return None
    known = known_keys(profile)
    key_names = [char_name(k) for k in weak]
    names = (
        key_names[0]
        if len(key_names) == 1
        else (", ".join(key_names[:-1]) + " and " + key_names[-1])
    )
    return Play(
        step_id=REVIEW_ID,
        title="Tricky keys",
        instruction=f"Extra practice for your tricky keys: {names}. Slow and careful wins!",
        header="Tricky keys practice",
        make_lines=lambda: review_lines(weak, known),
        speed_goal=round(profile.speed_goal * DRILL_SPEED_SHARE),
        review=True,
    )
