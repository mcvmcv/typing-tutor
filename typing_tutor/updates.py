"""Optional check for a newer version, for the grown-ups' screen.

Off unless a grown-up turns it on. When on, the app asks GitHub for the latest
release once each time it starts. The request carries no information about the
players, only the app's name and version (GitHub requires a User-Agent).
"""

from __future__ import annotations

import json

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from . import __version__

LATEST_RELEASE = "https://api.github.com/repos/mcvmcv/typing-tutor/releases/latest"
DOWNLOAD_PAGE = "https://mcvmcv.github.io/typing-tutor/#download"
TIMEOUT_MS = 10_000


def parse_version(text: str) -> tuple[int, ...] | None:
    """'v0.3.0' or '0.3.0' -> (0, 3, 0); None if it isn't a plain version."""
    parts = text.strip().removeprefix("v").split(".")
    if not all(p.isdigit() for p in parts):
        return None
    return tuple(int(p) for p in parts)


def latest_version(body: bytes) -> str | None:
    """The version in GitHub's latest-release reply, e.g. '0.4.0'."""
    try:
        data = json.loads(body)
    except ValueError:
        return None
    tag = data.get("tag_name") if isinstance(data, dict) else None
    if not isinstance(tag, str) or parse_version(tag) is None:
        return None
    return tag.strip().removeprefix("v")


def is_newer(latest: str, current: str = __version__) -> bool:
    new, now = parse_version(latest), parse_version(current)
    return new is not None and now is not None and new > now


class UpdateChecker(QObject):
    """Asks GitHub for the latest release. Emits `checked` with its version, or "" on failure."""

    checked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._network = QNetworkAccessManager(self)
        self._reply: QNetworkReply | None = None
        self.latest: str | None = None  # from the last successful check

    def check(self) -> None:
        if self._reply is not None:
            return  # already asking
        request = QNetworkRequest(QUrl(LATEST_RELEASE))
        request.setRawHeader(b"User-Agent", f"learn-typing/{__version__}".encode())
        request.setRawHeader(b"Accept", b"application/vnd.github+json")
        request.setTransferTimeout(TIMEOUT_MS)
        reply = self._network.get(request)
        self._reply = reply
        reply.finished.connect(lambda: self._finished(reply))

    def _finished(self, reply) -> None:
        self._reply = None
        version = None
        if reply.error() == QNetworkReply.NetworkError.NoError:
            version = latest_version(bytes(reply.readAll().data()))
        reply.deleteLater()
        if version:
            self.latest = version
        self.checked.emit(version or "")
