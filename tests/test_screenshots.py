import importlib.util
from pathlib import Path

from PySide6.QtGui import QImage

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "screenshots.py"


def load_script():
    spec = importlib.util.spec_from_file_location("screenshots", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_screenshot_script_makes_every_picture(qapp, tmp_path, monkeypatch):
    script = load_script()
    monkeypatch.setattr("typing_tutor.sounds.SoundPlayer.play", lambda self, name: None)
    saved = script.main(tmp_path)
    names = {p.stem for p in saved}
    assert names == {
        "players",
        "lessons",
        "practice",
        "balloon-pop",
        "snail-race",
        "progress",
        "grown-ups",
    }
    for path in saved:
        image = QImage(str(path))
        assert (image.width(), image.height()) == script.SIZE, path.name


def test_demo_players_look_believable(tmp_path):
    store = load_script().demo_store(tmp_path / "profiles.json")
    assert [p.name for p in store.profiles] == ["Mia", "Leo", "Sam"]
    assert all(p.history and p.best and p.key_stats for p in store.profiles)
