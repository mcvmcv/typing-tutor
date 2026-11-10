import wave

import pytest

from typing_tutor import sounds


class SpyEffect:
    def __init__(self):
        self.plays = 0

    def play(self):
        self.plays += 1


def wav_seconds(path):
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


def test_sound_files_are_generated_once(tmp_path):
    paths = sounds.ensure_sound_files(tmp_path)
    assert set(paths) == set(sounds.SOUNDS)
    assert wav_seconds(paths["click"]) < 0.05        # clicks must be very short
    assert 1.0 < wav_seconds(paths["stars3"]) < 2.5
    mtimes = {name: p.stat().st_mtime_ns for name, p in paths.items()}
    sounds.ensure_sound_files(tmp_path)
    assert mtimes == {name: p.stat().st_mtime_ns for name, p in paths.items()}


@pytest.fixture
def player_with_spies(qapp, sound_folder):
    player = sounds.SoundPlayer(sound_folder)
    spies = {name: SpyEffect() for name in sounds.SOUNDS}
    player._effects = {name: [spy] for name, spy in spies.items()}
    player._next_voice = dict.fromkeys(spies, 0)
    return player, spies


def test_plays_sounds_when_enabled(player_with_spies):
    player, spies = player_with_spies
    player.play("click")
    player.stars(3)
    player.stars(7)        # clamped to 3
    assert spies["click"].plays == 1 and spies["stars3"].plays == 2


def test_mute_and_no_key_clicks(player_with_spies):
    player, spies = player_with_spies
    player.key_clicks = False
    player.play("click")
    player.play("oops")
    assert spies["click"].plays == 0 and spies["oops"].plays == 1
    player.enabled = False
    player.play("oops")
    assert spies["oops"].plays == 1


def test_unknown_sounds_are_ignored(player_with_spies):
    player, _ = player_with_spies
    player.play("trumpet")


def test_runs_silently_if_the_cache_cannot_be_written(qapp, tmp_path):
    blocker = tmp_path / "not-a-folder"
    blocker.write_text("")
    player = sounds.SoundPlayer(blocker)
    player.play("click")   # no error
    assert player._effects == {}


def test_real_effects_load(qtbot, sound_folder):
    player = sounds.SoundPlayer(sound_folder)
    effect = player._effects["click"][0]
    qtbot.waitUntil(lambda: effect.status() != effect.Status.Loading, timeout=3000)
    assert effect.status() in (effect.Status.Ready, effect.Status.Error)
