"""Small widget helpers.

PySide6 accepts Qt properties as constructor keywords (``QLabel(objectName=...)``)
but its type stubs don't, so these helpers set them explicitly and keep the
screens tidy and type-checked.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QFrame, QLabel, QLayout, QWidget


def label(text: str = "", name: str = "", *, wrap: bool = False) -> QLabel:
    """A label styled by the stylesheet rule for ``QLabel#<name>``."""
    widget = QLabel(text)
    if name:
        widget.setObjectName(name)
    widget.setWordWrap(wrap)
    return widget


def frame(name: str, parent: QWidget | None = None) -> QFrame:
    widget = QFrame(parent)
    widget.setObjectName(name)
    return widget


def timer(
    parent: QObject, interval_ms: int, callback: Callable[[], None], single_shot: bool = False
) -> QTimer:
    t = QTimer(parent)
    t.setInterval(interval_ms)
    t.setSingleShot(single_shot)
    t.timeout.connect(callback)
    return t


def clear_layout(layout: QLayout) -> None:
    """Remove and delete every widget in a layout."""
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget() if item is not None else None
        if widget is not None:
            widget.deleteLater()
