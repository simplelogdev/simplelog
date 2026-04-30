"""Unit tests for workers._read_last_n_lines and UpdateWorker helpers."""
import io
import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from workers import _read_last_n_lines, _version_tuple

# ── helpers ───────────────────────────────────────────────────────────────────

def _write_tmp(lines: list[str]) -> str:
    """Write *lines* to a temp file and return its path."""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False)
    f.write("\n".join(lines))
    if lines:
        f.write("\n")
    f.close()
    return f.name


# ── tests ─────────────────────────────────────────────────────────────────────

def test_empty_file():
    path = _write_tmp([])
    try:
        lines, pos = _read_last_n_lines(path, 100)
        assert lines == []
        assert pos == 0
    finally:
        os.unlink(path)


def test_fewer_lines_than_requested():
    path = _write_tmp(["alpha", "beta", "gamma"])
    try:
        lines, pos = _read_last_n_lines(path, 100)
        assert lines == ["alpha", "beta", "gamma"]
        assert pos > 0
    finally:
        os.unlink(path)


def test_exactly_n_lines():
    content = [f"line{i}" for i in range(10)]
    path = _write_tmp(content)
    try:
        lines, _ = _read_last_n_lines(path, 10)
        assert lines == content
    finally:
        os.unlink(path)


def test_last_n_lines_from_large_file():
    total = 500
    content = [f"line{i}" for i in range(total)]
    path = _write_tmp(content)
    try:
        lines, _ = _read_last_n_lines(path, 50)
        assert len(lines) == 50
        assert lines[0] == "line450"
        assert lines[-1] == "line499"
    finally:
        os.unlink(path)


def test_eof_position_matches_file_size():
    raw = "foo\nbar\nbaz\n"
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False)
    f.write(raw)
    f.close()
    try:
        _, pos = _read_last_n_lines(f.name, 10)
        assert pos == len(raw.encode())
    finally:
        os.unlink(f.name)


def test_n_zero_returns_empty():
    path = _write_tmp(["a", "b", "c"])
    try:
        lines, pos = _read_last_n_lines(path, 0)
        assert lines == []
        assert pos > 0
    finally:
        os.unlink(path)


def test_single_line_no_trailing_newline():
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False)
    f.write("only line")
    f.close()
    try:
        lines, _ = _read_last_n_lines(f.name, 5)
        assert lines == ["only line"]
    finally:
        os.unlink(f.name)


@pytest.mark.parametrize("n", [1, 10, 100, 1000])
def test_never_returns_more_than_n(n):
    content = [f"x{i}" for i in range(200)]
    path = _write_tmp(content)
    try:
        lines, _ = _read_last_n_lines(path, n)
        assert len(lines) <= n
    finally:
        os.unlink(path)


def test_crlf_lines_are_stripped():
    f = tempfile.NamedTemporaryFile(mode="wb", suffix=".log", delete=False)
    f.write(b"alpha\r\nbeta\r\ngamma\r\n")
    f.close()
    try:
        lines, _ = _read_last_n_lines(f.name, 10)
        assert lines == ["alpha", "beta", "gamma"]
    finally:
        os.unlink(f.name)


# ── _version_tuple ────────────────────────────────────────────────────────────

def test_version_tuple_basic():
    assert _version_tuple("1.2.3") == (1, 2, 3)


def test_version_tuple_strips_v_prefix():
    assert _version_tuple("v1.5.0") == (1, 5, 0)


def test_version_tuple_lexicographic_trap():
    # "1.10.0" > "1.9.0" must be True — would fail with string comparison
    assert _version_tuple("1.10.0") > _version_tuple("1.9.0")


def test_version_tuple_equal_versions():
    assert _version_tuple("2.0.0") == _version_tuple("v2.0.0")


def test_version_tuple_malformed_falls_back():
    assert _version_tuple("not-a-version") == (0,)


def test_version_tuple_partial():
    assert _version_tuple("3.1") == (3, 1)


# ── UpdateWorker.run() ────────────────────────────────────────────────────────

def _fake_urlopen(tag: str, html_url: str = "https://example.com"):
    """Return a context manager mock whose read() returns a release JSON."""
    payload = json.dumps({"tag_name": tag, "html_url": html_url}).encode()
    resp = MagicMock()
    resp.read.return_value = payload
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def test_update_worker_emits_update_available():
    from workers import UpdateWorker
    worker = UpdateWorker("1.0.0")
    received = []
    worker.update_available.connect(lambda tag, url: received.append(tag))

    with patch("urllib.request.urlopen", return_value=_fake_urlopen("v1.1.0")):
        worker.run()

    assert received == ["v1.1.0"]


def test_update_worker_emits_up_to_date_when_equal():
    from workers import UpdateWorker
    worker = UpdateWorker("1.5.8")
    received = []
    worker.up_to_date.connect(lambda v: received.append(v))

    with patch("urllib.request.urlopen", return_value=_fake_urlopen("v1.5.8")):
        worker.run()

    assert received == ["1.5.8"]


def test_update_worker_emits_up_to_date_when_older():
    from workers import UpdateWorker
    worker = UpdateWorker("2.0.0")
    received = []
    worker.up_to_date.connect(lambda v: received.append(v))

    with patch("urllib.request.urlopen", return_value=_fake_urlopen("v1.9.9")):
        worker.run()

    assert received == ["2.0.0"]


def test_update_worker_lexicographic_fix():
    """1.10.0 must be considered newer than 1.9.0 (not equal via string comparison)."""
    from workers import UpdateWorker
    worker = UpdateWorker("1.9.0")
    received = []
    worker.update_available.connect(lambda tag, url: received.append(tag))

    with patch("urllib.request.urlopen", return_value=_fake_urlopen("v1.10.0")):
        worker.run()

    assert received == ["v1.10.0"]


def test_update_worker_emits_error_on_network_failure():
    from workers import UpdateWorker
    worker = UpdateWorker("1.0.0")
    errors = []
    worker.error.connect(lambda e: errors.append(e))

    with patch("urllib.request.urlopen", side_effect=OSError("timeout")):
        worker.run()

    assert errors and "timeout" in errors[0]
