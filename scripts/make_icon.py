"""Draw the app icon and write it in every format the builds and website need.

    make icon

Writes:
  typing_tutor/assets/icon.png   window icon (512 px)
  packaging/icon.ico             Windows app icon (16-256 px)
  packaging/icon.icns            macOS app icon (16-1024 px)
  docs/icon.png                  website favicon and header (192 px)

The design: a big friendly F key, the key the left pointer finger rests on,
with its little bump, on the app's sunny yellow, with a gold star (left off
below 32 px, where it would just be a smudge).
"""

from __future__ import annotations

import math
import os
import struct
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QBuffer, QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QGuiApplication,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)

ROOT = Path(__file__).resolve().parent.parent
INK = QColor("#2b2b2b")
POINTER = QColor("#8ec5ff")  # the pointer-finger colour from the on-screen keyboard


def _star(cx: float, cy: float, outer: float, inner: float) -> QPainterPath:
    path = QPainterPath()
    for i in range(10):
        r = outer if i % 2 == 0 else inner
        a = -math.pi / 2 + i * math.pi / 5
        point = QPointF(cx + r * math.cos(a), cy + r * math.sin(a))
        if i == 0:
            path.moveTo(point)
        else:
            path.lineTo(point)
    path.closeSubpath()
    return path


def draw_icon(size: int) -> QImage:
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.scale(size / 100, size / 100)  # draw on a 100 x 100 grid

    # Background: a rounded square in the app's yellow.
    bg = QLinearGradient(0, 0, 0, 100)
    bg.setColorAt(0, QColor("#ffdb7a"))
    bg.setColorAt(1, QColor("#ffb938"))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(bg)
    p.drawRoundedRect(QRectF(4, 4, 92, 92), 22, 22)

    # The key: a darker base for depth, then the cap on top.
    p.setBrush(QColor("#5a8fc4"))
    p.drawRoundedRect(QRectF(19, 23, 62, 62), 14, 14)
    cap = QLinearGradient(0, 18, 0, 76)
    cap.setColorAt(0, POINTER.lighter(112))
    cap.setColorAt(1, POINTER)
    p.setBrush(cap)
    p.drawRoundedRect(QRectF(19, 16, 62, 62), 14, 14)

    # The letter and the homing bump under it.
    font = QFont("DejaVu Sans")
    font.setPixelSize(42)
    font.setBold(True)
    p.setFont(font)
    p.setPen(INK)
    p.drawText(QRectF(19, 14, 62, 56), Qt.AlignmentFlag.AlignCenter, "F")
    p.setPen(QPen(INK, 4.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawLine(QPointF(42, 67), QPointF(58, 67))

    # A gold star, like the ones earned for each step. Too fiddly for tiny sizes.
    if size < 32:
        p.end()
        return image
    p.setPen(
        QPen(
            QColor("white"),
            3.5,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
            Qt.PenJoinStyle.RoundJoin,
        )
    )
    p.setBrush(QColor("#ffb300"))
    p.drawPath(_star(78, 22, 15, 6.5))
    p.end()
    return image


def png_bytes(image: QImage) -> bytes:
    buffer = QBuffer()
    buffer.open(QBuffer.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(buffer.data().data())


def ico_bytes(sizes: list[int]) -> bytes:
    """A Windows .ico holding one PNG per size (supported since Windows Vista)."""
    images = [png_bytes(draw_icon(s)) for s in sizes]
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = len(header) + 16 * len(images)
    entries, data = b"", b""
    for size, png in zip(sizes, images, strict=True):
        dim = 0 if size >= 256 else size  # 0 means 256
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(png), offset)
        offset += len(png)
        data += png
    return header + entries + data


ICNS_TYPES = {
    16: b"icp4",
    32: b"icp5",
    64: b"icp6",
    128: b"ic07",
    256: b"ic08",
    512: b"ic09",
    1024: b"ic10",
}


def icns_bytes(sizes: list[int]) -> bytes:
    """A macOS .icns holding one PNG per size."""
    body = b""
    for size in sizes:
        png = png_bytes(draw_icon(size))
        body += ICNS_TYPES[size] + struct.pack(">I", len(png) + 8) + png
    return b"icns" + struct.pack(">I", len(body) + 8) + body


def main(root: Path = ROOT) -> list[Path]:
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    assert app is not None
    outputs = {
        root / "typing_tutor" / "assets" / "icon.png": png_bytes(draw_icon(512)),
        root / "packaging" / "icon.ico": ico_bytes([16, 24, 32, 48, 64, 128, 256]),
        root / "packaging" / "icon.icns": icns_bytes([16, 32, 64, 128, 256, 512, 1024]),
        root / "docs" / "icon.png": png_bytes(draw_icon(192)),
    }
    for path, data in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return list(outputs)


if __name__ == "__main__":
    for path in main():
        print(path.relative_to(ROOT))
