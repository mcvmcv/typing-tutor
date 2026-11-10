"""Sound effects, synthesised at startup so there are no audio files to ship.

Sounds are written as small WAV files to the cache folder and played with
QSoundEffect, which has low enough latency for key clicks. If there's no
audio device, everything quietly does nothing.
"""

from __future__ import annotations

import math
import random
import struct
import wave
from pathlib import Path

from PySide6.QtCore import QObject, QStandardPaths, QUrl
from PySide6.QtMultimedia import QSoundEffect

RATE = 44100
CLICK_VOICES = 4  # overlapping copies so fast typing never cuts clicks off
SOUND_VERSION = 3  # bump to regenerate cached files after changing a sound

# Note frequencies (Hz).
C5, E5, G5, C6, E6, G6, C7 = 523.25, 659.25, 783.99, 1046.5, 1318.5, 1568.0, 2093.0


def _bell(freq: float, dur: float, volume: float = 0.5, decay: float = 6.0) -> list[float]:
    """A soft bell-like tone: a sine plus a quiet octave, fading out."""
    n = int(RATE * dur)
    out = []
    for i in range(n):
        t = i / RATE
        attack = min(1.0, t / 0.005)
        env = attack * math.exp(-decay * t)
        s = math.sin(2 * math.pi * freq * t) + 0.3 * math.sin(4 * math.pi * freq * t)
        out.append(volume * env * s / 1.3)
    return out


def _mix(*parts: tuple[float, list[float]]) -> list[float]:
    """Overlay (start_seconds, samples) parts into one track."""
    length = max(int(start * RATE) + len(s) for start, s in parts)
    track = [0.0] * length
    for start, samples in parts:
        offset = int(start * RATE)
        for i, v in enumerate(samples):
            track[offset + i] += v
    peak = max(1.0, max(abs(v) for v in track))
    return [v / peak for v in track]


def _click() -> list[float]:
    """A short, soft wooden tick."""
    rng = random.Random(1)
    n = int(RATE * 0.03)
    out = []
    for i in range(n):
        t = i / RATE
        env = math.exp(-180 * t)
        tone = math.sin(2 * math.pi * 1250 * t)
        noise = rng.uniform(-1, 1) * math.exp(-400 * t)
        out.append(0.35 * env * (0.7 * tone + 0.3 * noise))
    return out


def _oops() -> list[float]:
    """A gentle low 'bonk' that slides down. Not a harsh buzzer."""
    n = int(RATE * 0.16)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / RATE
        freq = 260 - 500 * t
        phase += 2 * math.pi * freq / RATE
        env = min(1.0, t / 0.004) * math.exp(-14 * t)
        s = math.sin(phase) + 0.25 * math.sin(2 * phase)
        out.append(0.45 * env * s)
    return out


def _line_done() -> list[float]:
    return _mix((0.0, _bell(C6, 0.25, decay=10)), (0.08, _bell(E6, 0.35, decay=8)))


def _fanfare(stars: int) -> list[float]:
    notes = {1: [C5, E5, G5], 2: [C5, E5, G5, C6], 3: [C5, E5, G5, C6, E6, G6]}[stars]
    parts = [(i * 0.11, _bell(f, 0.5, volume=0.5, decay=5)) for i, f in enumerate(notes)]
    end = len(notes) * 0.11
    # Finish on a held chord, with a sparkle on top for 3 stars.
    for f in (C5, E5, G5) if stars < 3 else (C6, E6, G6):
        parts.append((end, _bell(f, 1.0, volume=0.35, decay=3)))
    if stars == 3:
        for k in range(4):
            parts.append(
                (end + 0.1 + k * 0.07, _bell(C7 * (1 + 0.12 * k), 0.2, volume=0.15, decay=14))
            )
    return [0.7 * v for v in _mix(*parts)]  # celebratory, not startling


def _pop() -> list[float]:
    """A balloon pop: a quick bright burst with a little pitch drop."""
    rng = random.Random(7)
    n = int(RATE * 0.12)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / RATE
        phase += 2 * math.pi * (900 - 4000 * t) / RATE
        noise = rng.uniform(-1, 1) * math.exp(-60 * t)
        tone = math.sin(phase) * math.exp(-35 * t)
        out.append(0.5 * (0.6 * noise + 0.4 * tone))
    return out


def _whoosh() -> list[float]:
    """A balloon floating away: a soft falling whistle."""
    n = int(RATE * 0.5)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / RATE
        phase += 2 * math.pi * (900 - 900 * t) / RATE
        env = min(1.0, t / 0.05) * math.exp(-5 * t)
        out.append(0.3 * env * math.sin(phase))
    return out


def _game_over() -> list[float]:
    notes = [G5, E5, C5]
    parts = [(i * 0.2, _bell(f, 0.6, volume=0.4, decay=4)) for i, f in enumerate(notes)]
    return [0.7 * v for v in _mix(*parts)]


SOUNDS = {
    "pop": _pop,
    "whoosh": _whoosh,
    "gameover": _game_over,
    "click": _click,
    "oops": _oops,
    "line": _line_done,
    "stars1": lambda: _fanfare(1),
    "stars2": lambda: _fanfare(2),
    "stars3": lambda: _fanfare(3),
}


def _write_wav(path: Path, samples: list[float]) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, s)) * 32000)) for s in samples))


def sound_dir() -> Path:
    base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.CacheLocation)
    return Path(base) / f"sounds-v{SOUND_VERSION}"


def ensure_sound_files(folder: Path) -> dict[str, Path]:
    folder.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name, make in SOUNDS.items():
        path = folder / f"{name}.wav"
        if not path.exists():
            tmp = path.with_suffix(".tmp")
            _write_wav(tmp, make())
            tmp.replace(path)
        paths[name] = path
    return paths


class SoundPlayer(QObject):
    """Plays the app's sound effects, respecting the current player's settings."""

    def __init__(self, folder: Path | None = None, volume: float = 0.6, parent=None):
        super().__init__(parent)
        self.enabled = True
        self.key_clicks = True
        self._effects: dict[str, list[QSoundEffect]] = {}
        self._next_voice: dict[str, int] = {}
        try:
            paths = ensure_sound_files(folder or sound_dir())
        except OSError:
            return  # can't write the cache: run silently
        for name, path in paths.items():
            voices = CLICK_VOICES if name in ("click", "oops", "pop") else 1
            effects = []
            for _ in range(voices):
                fx = QSoundEffect(self)
                fx.setSource(QUrl.fromLocalFile(str(path)))
                fx.setVolume(volume)
                effects.append(fx)
            self._effects[name] = effects
            self._next_voice[name] = 0

    def play(self, name: str) -> None:
        if not self.enabled or (name == "click" and not self.key_clicks):
            return
        voices = self._effects.get(name)
        if not voices:
            return
        i = self._next_voice[name]
        self._next_voice[name] = (i + 1) % len(voices)
        voices[i].play()

    def stars(self, count: int) -> None:
        self.play(f"stars{max(1, min(3, count))}")
