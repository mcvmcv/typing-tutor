"""The optional new-version check. The network is never used: replies are faked."""

from __future__ import annotations

import json

import pytest
from PySide6.QtCore import QByteArray, QObject, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply

from typing_tutor import __version__, updates
from typing_tutor.updates import UpdateChecker, is_newer, latest_version, parse_version


@pytest.mark.parametrize(
    ("text", "parsed"),
    [("v0.3.0", (0, 3, 0)), ("1.10", (1, 10)), (" 2.0.1 ", (2, 0, 1)), ("v1.0-beta", None)],
)
def test_parse_version(text, parsed):
    assert parse_version(text) == parsed


def test_is_newer():
    assert is_newer("0.10.0", "0.9.9")  # numbers, not text
    assert not is_newer("0.3.0", "0.3.0")
    assert not is_newer("0.2.0", "0.3.0")
    assert not is_newer("nonsense", "0.3.0")
    assert not is_newer("0.4.0", "dev")


@pytest.mark.parametrize(
    ("body", "version"),
    [
        (b'{"tag_name": "v0.4.0"}', "0.4.0"),
        (b'{"tag_name": "0.4.1"}', "0.4.1"),
        (b'{"tag_name": "latest"}', None),
        (b'{"message": "Not Found"}', None),
        (b"[1, 2]", None),
        (b"<html>", None),
    ],
)
def test_latest_version(body, version):
    assert latest_version(body) == version


class FakeReply(QObject):
    finished = Signal()

    def __init__(self, body: bytes = b"", error=QNetworkReply.NetworkError.NoError):
        super().__init__()
        self._body, self._error = body, error

    def error(self):
        return self._error

    def readAll(self):
        return QByteArray(self._body)


class FakeGitHub:
    """Stands in for QNetworkAccessManager.get, recording requests."""

    def __init__(self, monkeypatch):
        self.requests = []
        self.reply = FakeReply()
        monkeypatch.setattr(QNetworkAccessManager, "get", self._get)

    def _get(self, request):  # replaces the class attribute, so no manager argument
        self.requests.append(request)
        return self.reply

    def answer(self, tag: str | None = None, error=QNetworkReply.NetworkError.NoError) -> None:
        body = json.dumps({"tag_name": tag}).encode() if tag else b""
        self.reply._body, self.reply._error = body, error
        self.reply.finished.emit()


@pytest.fixture
def github(monkeypatch):
    return FakeGitHub(monkeypatch)


def test_checker_asks_github_without_personal_details(qapp, github):
    checker = UpdateChecker()
    results = []
    checker.checked.connect(results.append)
    checker.check()
    checker.check()  # still waiting: no second request
    [request] = github.requests
    assert request.url().toString() == updates.LATEST_RELEASE
    agent = request.rawHeader("User-Agent").data()
    assert agent == f"learn-typing/{__version__}".encode()
    github.answer("v9.0.0")
    assert results == ["9.0.0"] and checker.latest == "9.0.0"


def test_a_failed_check_reports_nothing_found(qapp, github):
    checker = UpdateChecker()
    results = []
    checker.checked.connect(results.append)
    checker.check()
    github.answer(error=QNetworkReply.NetworkError.HostNotFoundError)
    assert results == [""] and checker.latest is None
    checker.check()  # can try again
    assert len(github.requests) == 2
