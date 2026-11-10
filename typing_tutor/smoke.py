"""Self-check for built apps: ``LearnTyping --smoke-test``.

A frozen build can start yet be missing pieces that only fail at runtime, such
as a Qt plugin the sounds need. This builds the real window with throwaway data,
types a key in a lesson, waits for the sounds to load, plays one silently and
prints a report. It exits non-zero if anything failed, so CI can check each
build on each OS.
"""

from __future__ import annotations

import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtMultimedia import QMediaDevices, QSoundEffect
from PySide6.QtWidgets import QApplication

from .lessons import HOME_ROW
from .storage import ProfileStore


def _wait_for_sounds(app: QApplication, effects: list[QSoundEffect], timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline and any(
        fx.status() in (QSoundEffect.Status.Null, QSoundEffect.Status.Loading) for fx in effects
    ):
        app.processEvents()
        time.sleep(0.02)


def _plays(app: QApplication, effect: QSoundEffect, timeout: float = 3.0) -> bool:
    """Play an effect silently and report whether Qt actually started playing it."""
    effect.setVolume(0.0)
    effect.play()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if effect.isPlaying():
            effect.stop()
            return True
        time.sleep(0.01)
    return False


def run(app: QApplication, timeout: float = 10.0) -> int:
    from .app import MainWindow  # here, not at the top: app.py imports this module

    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        window = MainWindow(ProfileStore(folder / "profiles.json"), sound_folder=folder / "sounds")
        window.show()
        player = window.store.add("Smoke Test", "#4a90d9")
        window.choose_profile(player.id)
        window.start_step(HOME_ROW, 0)
        line = window.practice._current()[0].current
        first = line.text[0]
        key = QKeyEvent(QEvent.Type.KeyPress, 0, Qt.KeyboardModifier.NoModifier, first)
        QCoreApplication.sendEvent(window.practice, key)
        app.processEvents()

        effects = window.sounds.effects()
        created = len(effects) > 0
        # Without a sound card (most CI machines) every effect ends in Error,
        # so loading and playback can only be checked when there is one.
        has_output = bool(QMediaDevices.audioOutputs())
        if has_output:
            _wait_for_sounds(app, effects, timeout)
        statuses = Counter(fx.status().name for fx in effects)
        loaded = created and statuses.get("Ready", 0) == len(effects)
        played = has_output and loaded and _plays(app, effects[0])
        typed = line.pos
        window.close()

    def verdict(ok: bool) -> str:
        return "skipped (no audio output)" if not has_output else "ok" if ok else "FAILED"

    report = [
        f"window:   ok (Qt platform: {app.platformName()})",
        f"typing:   {'ok' if typed == 1 else 'FAILED'} (typed {typed} of 1 key)",
        f"sounds:   {'ok' if created else 'FAILED'} ({len(effects)} effects created)",
        f"loading:  {verdict(loaded)} ({dict(statuses)})",
        f"playback: {verdict(played)}",
    ]
    _show("\n".join(report))
    sound_ok = created and (played or not has_output)
    return 0 if typed == 1 and sound_ok else 1


def _show(text: str) -> None:
    # Windowed Windows builds have no console (sys.stdout is None), so the
    # report goes to a file in the current folder instead.
    if sys.stdout is not None:
        print(text)
    else:  # pragma: no cover - only in windowed builds
        Path("smoke-test.txt").write_text(text + "\n")
