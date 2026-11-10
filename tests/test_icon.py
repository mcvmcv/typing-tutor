import importlib.util
from pathlib import Path

from PySide6.QtGui import QImageReader

from typing_tutor.app import ICON, app_icon

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "make_icon.py"


def load_script():
    spec = importlib.util.spec_from_file_location("make_icon", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sizes_in(path: Path) -> list[int]:
    reader = QImageReader(str(path))
    sizes = []
    for i in range(reader.imageCount()):
        reader.jumpToImage(i)
        sizes.append(reader.read().width())
    return sorted(sizes)


def test_icon_script_writes_every_format(qapp, tmp_path):
    written = load_script().main(tmp_path)
    by_name = {p.name: p for p in written}
    assert sizes_in(by_name["icon.ico"]) == [16, 24, 32, 48, 64, 128, 256]
    assert sizes_in(by_name["icon.icns"]) == [16, 32, 64, 128, 256, 512, 1024]
    pngs = [p for p in written if p.suffix == ".png"]
    assert {QImageReader(str(p)).size().width() for p in pngs} == {512, 192}


def test_the_app_ships_its_icon(qapp):
    assert ICON.exists()
    assert not app_icon().isNull()
