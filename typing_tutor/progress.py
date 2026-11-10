"""Turns a player's saved history into chart points and summary numbers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from .lessons import ALL_STEPS, first_unfinished
from .plays import REVIEW_ID, key_scores, weak_keys
from .storage import Profile

MAX_ATTEMPT_POINTS = 60

STEP_TITLES = {
    lesson.step_id(i): f"{lesson.title}: {lesson.steps[i].title}" for lesson, i in ALL_STEPS
}
STEP_TITLES[REVIEW_ID] = "Tricky keys practice"


@dataclass(frozen=True)
class Point:
    label: str  # short x-axis label, e.g. "10 Nov"
    wpm: float
    accuracy: float
    detail: str  # extra tooltip line


@dataclass(frozen=True)
class Summary:
    best_wpm: float
    recent_accuracy: float | None
    stars: int
    max_stars: int
    steps_done: int
    total_steps: int
    practice_days: int


def step_title(step_id: str) -> str:
    return STEP_TITLES.get(step_id, step_id)


def _when(entry: dict) -> datetime:
    return datetime.fromisoformat(entry["when"])


def _short_date(d: datetime) -> str:
    return f"{d.day} {d.strftime('%b')}"


def _timed(profile: Profile) -> list[dict]:
    # Very short attempts record 0 WPM; they'd only drag the chart down.
    return [h for h in profile.history if h.get("wpm", 0) > 0]


def points_by_attempt(profile: Profile) -> list[Point]:
    entries = _timed(profile)[-MAX_ATTEMPT_POINTS:]
    return [
        Point(_short_date(_when(h)), h["wpm"], h["accuracy"], step_title(h["step"]))
        for h in entries
    ]


def points_by_day(profile: Profile) -> list[Point]:
    days: dict[str, list[dict]] = {}
    for h in _timed(profile):
        days.setdefault(h["when"][:10], []).append(h)
    points = []
    for day in sorted(days):
        entries = days[day]
        n = len(entries)
        wpm = sum(h["wpm"] for h in entries) / n
        acc = sum(h["accuracy"] for h in entries) / n
        detail = "1 step" if n == 1 else f"{n} steps"
        points.append(Point(_short_date(datetime.fromisoformat(day)), wpm, acc, detail))
    return points


def summary(profile: Profile) -> Summary:
    course_ids = [lesson.step_id(i) for lesson, i in ALL_STEPS]
    best = [profile.best[s]["wpm"] for s in course_ids if s in profile.best]
    timed = _timed(profile)
    recent = timed[-10:]
    return Summary(
        best_wpm=max(best, default=0.0),
        recent_accuracy=(sum(h["accuracy"] for h in recent) / len(recent)) if recent else None,
        stars=sum(profile.stars(s) for s in course_ids),
        max_stars=3 * len(course_ids),
        steps_done=sum(1 for s in course_ids if profile.stars(s) > 0),
        total_steps=len(course_ids),
        practice_days=len({h["when"][:10] for h in profile.history}),
    )


def recent_attempts(profile: Profile, limit: int = 12) -> list[dict]:
    return list(reversed(profile.history[-limit:]))


@dataclass(frozen=True)
class Overview:
    """One player's line in the parent view."""

    summary: Summary
    up_to: str  # the next step to play, or a note that the course is done
    last_practised: datetime | None
    steps_this_week: int
    tricky_keys: list[str] | None  # None: not enough typing yet to tell
    game_best: int  # best Balloon Pop score on any difficulty


def overview(profile: Profile, now: datetime | None = None) -> Overview:
    now = now or datetime.now()
    upcoming = first_unfinished(profile.stars)
    if upcoming is None:
        up_to = "Finished the whole course!"
    else:
        lesson, i = upcoming
        up_to = step_title(lesson.step_id(i))
    times = [_when(h) for h in profile.history]
    week_ago = now - timedelta(days=7)
    return Overview(
        summary=summary(profile),
        up_to=up_to,
        last_practised=max(times, default=None),
        steps_this_week=sum(1 for t in times if t > week_ago),
        tricky_keys=weak_keys(profile) if key_scores(profile) else None,
        game_best=max(profile.game_best.values(), default=0),
    )


def days_ago(when: datetime | None, now: datetime | None = None) -> str:
    """'Today', 'Yesterday', '3 days ago'... by calendar day."""
    if when is None:
        return "Not yet"
    now = now or datetime.now()
    days = (now.date() - when.date()).days
    if days <= 0:
        return "Today"
    if days == 1:
        return "Yesterday"
    if days < 14:
        return f"{days} days ago"
    if days < 60:
        return f"{days // 7} weeks ago"
    return _short_date(when) + (f" {when.year}" if when.year != now.year else "")
