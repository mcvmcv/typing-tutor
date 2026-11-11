"""Make the README and website screenshots from made-up demo players.

    make screenshots          # writes docs/screenshots/*.png

Runs offscreen with a throwaway save file, so real progress is never touched.
The demo players and practice line are seeded, so the content is the same each
run (animations such as the cursor blink and drifting clouds may differ a little).
"""

from __future__ import annotations

import os
import random
import sys
import tempfile
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QEvent, QStandardPaths, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication, QWidget

from typing_tutor.app import MainWindow
from typing_tutor.generator import build_lines
from typing_tutor.lessons import ALL_STEPS, KNOWN, TOP_ROW
from typing_tutor.plays import lesson_play
from typing_tutor.storage import Profile, ProfileStore
from typing_tutor.theme import AVATAR_COLORS, apply_theme

OUT = Path(__file__).resolve().parent.parent / "docs" / "screenshots"
SIZE = (1150, 800)
NOW = datetime(2026, 11, 10, 17, 30)


def _practice(
    profile: Profile,
    rng: random.Random,
    *,
    steps: int,
    days: int,
    wpm: tuple[float, float],
    accuracy: tuple[float, float],
    tricky: str,
) -> None:
    """Fill a profile with `steps` finished steps spread over the last `days` days."""
    ids = [lesson.step_id(i) for lesson, i in ALL_STEPS]
    practice_days = sorted(rng.sample(range(days), k=max(1, days * 2 // 3)), reverse=True)
    plays = []
    step = 0
    attempts = steps + steps // 3  # some steps get played twice
    for n in range(attempts):
        day = practice_days[min(n * len(practice_days) // attempts, len(practice_days) - 1)]
        when = (NOW - timedelta(days=day)).replace(hour=16 + n % 3, minute=rng.randrange(60))
        t = n / max(1, attempts - 1)
        speed = wpm[0] + (wpm[1] - wpm[0]) * t + rng.uniform(-1.5, 1.5)
        acc = min(100.0, accuracy[0] + (accuracy[1] - accuracy[0]) * t + rng.uniform(-3, 2))
        stars = 3 if acc >= 95 else 2 if acc >= 85 else 1
        plays.append((ids[min(step, len(ids) - 1)], when, speed, acc, stars))
        if rng.random() > 0.25 or n >= attempts - (steps - step):
            step += 1
        if step >= steps:
            break
    for step_id, when, speed, acc, stars in plays:
        profile.history.append(
            {
                "step": step_id,
                "wpm": round(max(speed, 1.0), 1),
                "accuracy": round(acc, 1),
                "stars": stars,
                "when": when.isoformat(timespec="seconds"),
            }
        )
        best = profile.best.setdefault(step_id, {"stars": 0, "wpm": 0.0, "accuracy": 0.0})
        best["stars"] = max(best["stars"], stars)
        best["wpm"] = max(best["wpm"], round(speed, 1))
        best["accuracy"] = max(best["accuracy"], round(acc, 1))

    known = KNOWN[ids[steps - 1]]
    for key in sorted(known):
        if key == " ":
            continue
        hits = rng.randrange(40, 120)
        hard = key in tricky
        misses = int(hits * (rng.uniform(0.08, 0.15) if hard else rng.uniform(0.0, 0.02)))
        seconds = hits * (rng.uniform(0.7, 0.9) if hard else rng.uniform(0.35, 0.5))
        profile.key_stats[key] = {"h": hits, "m": misses, "t": seconds, "n": hits}


def demo_store(path: Path) -> ProfileStore:
    store = ProfileStore(path)
    store.keyboard = "us"  # not guessed from this computer's region
    rng = random.Random(4)
    mia = store.add("Mia", AVATAR_COLORS[6])
    _practice(mia, rng, steps=14, days=20, wpm=(6, 15), accuracy=(88, 97), tricky="ri")
    mia.game_best = {"easy": 420, "medium": 260}
    leo = store.add("Leo", AVATAR_COLORS[4])
    _practice(leo, rng, steps=4, days=4, wpm=(3, 6), accuracy=(84, 93), tricky="")
    sam = store.add("Sam", AVATAR_COLORS[3], speed_goal=20)
    _practice(sam, rng, steps=31, days=30, wpm=(14, 26), accuracy=(92, 98), tricky="qz;")
    sam.game_best = {"easy": 980, "medium": 1340, "hard": 610}
    store.save()
    return store


def _settle(app: QApplication, rounds: int = 5) -> None:
    for _ in range(rounds):
        app.processEvents()


def _save(widget: QWidget, name: str, out: Path) -> Path:
    path = out / f"{name}.png"
    widget.grab().save(str(path))
    return path


def _type(widget: QWidget, text: str) -> None:
    for ch in text:
        key = QKeyEvent(QEvent.Type.KeyPress, 0, Qt.KeyboardModifier.NoModifier, ch)
        QCoreApplication.sendEvent(widget, key)


def main(out: Path = OUT) -> list[Path]:
    QStandardPaths.setTestModeEnabled(True)
    app = QApplication.instance() or QApplication(sys.argv)
    assert isinstance(app, QApplication)
    apply_theme(app)
    out.mkdir(parents=True, exist_ok=True)
    saved = []
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        store = demo_store(folder / "profiles.json")
        window = MainWindow(store, sound_folder=folder / "sounds")
        window.sounds.play = lambda name: None  # keep the demo silent
        window.resize(*SIZE)
        window.show()
        mia, _leo, sam = store.profiles

        window.show_profiles()
        _settle(app)
        saved.append(_save(window, "players", out))

        window.choose_profile(mia.id)
        _settle(app)
        saved.append(_save(window, "lessons", out))

        play = lesson_play(TOP_ROW, 5, mia)
        seeded = replace(play, make_lines=lambda: build_lines(TOP_ROW, 5, random.Random(3)))
        window.stack.setCurrentWidget(window.practice)
        window.practice.start(seeded)
        line = window.practice._current()[0].current
        _type(window.practice, line.text[:9])
        _type(window.practice, "x")  # one mistake, to show the friendly hint
        assert line.started_at is not None
        line.started_at -= 5.5  # as if those keys took a few seconds, so speed shows
        window.practice._update_stats()
        _settle(app)
        saved.append(_save(window, "practice", out))

        window.show_menu()
        window.show_game()
        game = window.game
        game.start_game("easy")
        game._timer.stop()
        state = game.state
        assert state is not None
        state.rng = random.Random(8)
        for _ in range(200):
            game._handle(state.update(0.05))
        target = next(b for b in sorted(state.balloons, key=lambda b: b.y) if b.active)
        for ch in target.word[:2]:
            game._handle(state.type(ch))
        state.score, state.popped, state.level = 180, 6, 1
        game._shake = 0
        _settle(app)
        saved.append(_save(window, "balloon-pop", out))

        window.show_menu()
        window.show_race()
        race = window.race
        race.rng = random.Random(2)
        race.start_race("medium")
        race._timer.stop()
        r = race.state
        assert r is not None
        r.update(3.0)
        for ch in r.text[:24]:
            r.update(0.42)
            r.type(ch)
        r.type("#")  # a slip, so the cursor shows red
        race._wiggle = 0
        _settle(app)
        saved.append(_save(window, "snail-race", out))

        window.show_menu()
        window.choose_profile(sam.id)
        window.show_progress()
        _settle(app)
        saved.append(_save(window, "progress", out))

        window.show_parents()
        window.parents.refresh(NOW)
        _settle(app)
        saved.append(_save(window, "grown-ups", out))
        window.close()
    return saved


if __name__ == "__main__":
    for path in main():
        print(path)
