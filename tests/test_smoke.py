import pytest
from PySide6.QtMultimedia import QSoundEffect

from typing_tutor import smoke
from typing_tutor.sounds import SoundPlayer


class Outputs:
    """Stands in for QMediaDevices so tests don't depend on the machine's sound card."""

    def __init__(self, devices):
        self._devices = devices

    def audioOutputs(self):
        return self._devices


@pytest.fixture
def no_sound_card(monkeypatch):
    monkeypatch.setattr(smoke, "QMediaDevices", Outputs([]))


def test_passes_on_a_working_app(themed_app, no_sound_card, capsys):
    assert smoke.run(themed_app) == 0
    out = capsys.readouterr().out
    assert "FAILED" not in out
    assert "loading:  skipped" in out and "playback: skipped" in out


def test_fails_when_sounds_are_missing(themed_app, no_sound_card, monkeypatch, capsys):
    monkeypatch.setattr(SoundPlayer, "effects", lambda self: [])
    assert smoke.run(themed_app) == 1
    assert "sounds:   FAILED" in capsys.readouterr().out


@pytest.fixture
def sound_card(monkeypatch):
    monkeypatch.setattr(smoke, "QMediaDevices", Outputs(["speakers"]))


def test_checks_loading_and_playback_when_there_is_a_sound_card(
    themed_app, sound_card, monkeypatch, capsys
):
    monkeypatch.setattr(SoundPlayer, "effects", lambda self: [FakeEffect(starts=True)])
    assert smoke.run(themed_app) == 0
    out = capsys.readouterr().out
    assert "loading:  ok" in out and "playback: ok" in out


def test_fails_if_a_sound_wont_load(themed_app, sound_card, monkeypatch, capsys):
    broken = FakeEffect(starts=True, status=QSoundEffect.Status.Error)
    monkeypatch.setattr(SoundPlayer, "effects", lambda self: [FakeEffect(starts=True), broken])
    assert smoke.run(themed_app) == 1
    assert "loading:  FAILED" in capsys.readouterr().out


def test_fails_if_nothing_plays(themed_app, sound_card, monkeypatch, capsys):
    monkeypatch.setattr(SoundPlayer, "effects", lambda self: [FakeEffect(starts=False)])
    monkeypatch.setattr(smoke, "_plays", lambda app, effect: False)
    assert smoke.run(themed_app) == 1
    assert "playback: FAILED" in capsys.readouterr().out


class FakeEffect:
    def __init__(self, starts, status=QSoundEffect.Status.Ready):
        self.starts = starts
        self._status = status
        self.volume = None
        self.playing = False

    def setVolume(self, volume):
        self.volume = volume

    def play(self):
        self.playing = self.starts

    def isPlaying(self):
        return self.playing

    def stop(self):
        self.playing = False

    def status(self):
        return self._status


def test_playback_check_is_silent_and_stops_the_sound(qapp):
    effect = FakeEffect(starts=True)
    assert smoke._plays(qapp, effect)
    assert effect.volume == 0.0 and not effect.playing


def test_playback_check_gives_up_if_nothing_plays(qapp):
    assert not smoke._plays(qapp, FakeEffect(starts=False), timeout=0.05)
