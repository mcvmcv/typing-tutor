"""Shared fixtures. Tests never touch the real save file or ~/.cache."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

import pytest
from PySide6.QtCore import QStandardPaths

from typing_tutor import sounds
from typing_tutor.lessons import ALL_STEPS
from typing_tutor.storage import Profile, ProfileStore

# Anything that still asks Qt for a standard path gets a throwaway test folder.
QStandardPaths.setTestModeEnabled(True)


class FakeClock:
    """A controllable stand-in for time.monotonic."""

    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture(scope="session", autouse=True)
def themed_app(qapp):
    """Test the screens with the real stylesheet and palette."""
    from typing_tutor.theme import apply_theme

    apply_theme(qapp)
    return qapp


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture(scope="session")
def sound_folder(tmp_path_factory) -> Path:
    # Generating the sounds takes ~0.5s, so do it once per test run.
    folder = tmp_path_factory.mktemp("sounds")
    sounds.ensure_sound_files(folder)
    return folder


@pytest.fixture(autouse=True)
def isolated_sounds(monkeypatch, sound_folder):
    monkeypatch.setattr(sounds, "sound_dir", lambda: sound_folder)


@pytest.fixture
def store(tmp_path) -> ProfileStore:
    return ProfileStore(tmp_path / "profiles.json")


@pytest.fixture
def player(store) -> Profile:
    return store.add("Sam", "#64b5f6")


def finish_steps(
    store: ProfileStore,
    profile: Profile,
    count: int,
    wpm: float = 12,
    accuracy: float = 96,
    stars: int = 3,
) -> None:
    """Mark the first `count` course steps as finished."""
    for lesson, i in ALL_STEPS[:count]:
        store.record_result(profile.id, lesson.step_id(i), wpm, accuracy, stars)


def key_stat(hits: float, misses: float = 0, seconds_per_key: float = 0.3) -> dict:
    return {"h": hits, "m": misses, "t": hits * seconds_per_key, "n": hits}
