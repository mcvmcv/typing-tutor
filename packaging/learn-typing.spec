# PyInstaller build for a double-click app (no Python needed to run it).
#
#   pyinstaller packaging/learn-typing.spec
#
# Windows and Linux get one self-contained file (dist/LearnTyping[.exe]).
# macOS gets an app bundle (dist/Learn Typing.app), since one-file builds
# start slowly there and PyInstaller discourages them for .app bundles.

import re
import sys
from pathlib import Path

ROOT = Path(SPECPATH).parent
MAC = sys.platform == "darwin"

a = Analysis(
    [str(ROOT / "packaging" / "launch.py")],
    pathex=[str(ROOT)],  # find typing_tutor even when it's installed in editable mode
    excludes=["tkinter"],
)

# Qt plugins the app never uses, and the libraries only they need: the media
# player backend (FFmpeg; QSoundEffect doesn't use it), the on-screen virtual
# keyboard (Qt Quick and QML) and PDF image loading. Dropping them shrinks
# the build by about a fifth. `--smoke-test` checks the result still works.
UNUSED = re.compile(
    r"plugins[/\\]multimedia|virtualkeyboard|qpdf|qt6?(quick|qml|pdf)"
    r"|(avcodec|avformat|avutil|swresample|swscale)",
    re.IGNORECASE,
)
a.binaries = [b for b in a.binaries if not UNUSED.search(b[0])]
a.datas = [d for d in a.datas if not UNUSED.search(d[0])]

pyz = PYZ(a.pure)

if MAC:
    exe = EXE(
        pyz,
        a.scripts,
        exclude_binaries=True,
        name="LearnTyping",
        console=False,
    )
    coll = COLLECT(exe, a.binaries, a.datas, name="LearnTyping")
    app = BUNDLE(
        coll,
        name="Learn Typing.app",
        bundle_identifier="io.github.mcvmcv.typing-tutor",
        info_plist={"NSHighResolutionCapable": True},
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        name="LearnTyping",
        console=False,
        upx=False,
    )
