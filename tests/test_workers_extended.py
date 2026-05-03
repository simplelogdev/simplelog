"""Tests for workers.py pure helpers and FileWorker QThread."""
import sys
import tempfile
import time

from workers import _parse_docker_ts, _parse_k8s_line  # noqa: E402

# ── _parse_docker_ts ───────────────────────────────────────────────────────────

def test_parse_docker_ts_valid_rfc3339():
    line = "2023-11-14T12:00:00.123456789Z Hello from container"
    ts_ms, msg = _parse_docker_ts(line)
    assert msg == "Hello from container"
    assert ts_ms > 0


def test_parse_docker_ts_invalid_ts_falls_back():
    line = "not-a-timestamp some message"
    ts_ms, msg = _parse_docker_ts(line)
    assert msg == line
    assert ts_ms > 0


def test_parse_docker_ts_empty_string():
    ts_ms, msg = _parse_docker_ts("")
    assert isinstance(ts_ms, int)
    assert msg == ""


def test_parse_docker_ts_preserves_message_with_spaces():
    line = "2023-11-14T12:00:00Z message with   spaces"
    _, msg = _parse_docker_ts(line)
    assert msg == "message with   spaces"


def test_parse_docker_ts_only_timestamp_no_message():
    line = "2023-11-14T12:00:00Z"
    ts_ms, msg = _parse_docker_ts(line)
    assert isinstance(ts_ms, int)


# ── _parse_k8s_line ────────────────────────────────────────────────────────────

def test_parse_k8s_line_with_valid_ts():
    line = "2023-11-14T12:00:00.123456789Z INFO application started"
    ts_ms, msg = _parse_k8s_line(line, fallback_ms=0)
    assert ts_ms > 0
    assert "INFO application started" in msg


def test_parse_k8s_line_invalid_ts_uses_fallback():
    line = "not-ts INFO something"
    fallback = 9999999
    ts_ms, msg = _parse_k8s_line(line, fallback_ms=fallback)
    assert ts_ms == fallback
    assert msg == line


def test_parse_k8s_line_empty_string_uses_fallback():
    ts_ms, msg = _parse_k8s_line("", fallback_ms=12345)
    assert ts_ms == 12345


# ── FileWorker ─────────────────────────────────────────────────────────────────

def test_file_worker_emits_initial_lines():
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QApplication

    from workers import FileWorker

    QApplication.instance() or QApplication(sys.argv)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
        f.write("line1\nline2\nline3\n")
        path = f.name

    received: list = []
    statuses: list = []

    worker = FileWorker(path, tail_lines=10, interval_ms=50)
    worker.new_lines.connect(received.extend, Qt.ConnectionType.DirectConnection)

    def on_status(msg: str):
        statuses.append(msg)
        if "Tailing" in msg:
            worker.stop()

    worker.status.connect(on_status, Qt.ConnectionType.DirectConnection)
    worker.start()
    assert worker.wait(5000), "FileWorker did not finish in time"

    messages = [msg for _, msg in received]
    assert "line1" in messages
    assert "line2" in messages
    assert "line3" in messages


def test_file_worker_emits_error_for_missing_file():
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QApplication

    from workers import FileWorker

    QApplication.instance() or QApplication(sys.argv)

    errors: list = []
    worker = FileWorker("/nonexistent/path/file.log", tail_lines=10, interval_ms=50)
    worker.error.connect(errors.append, Qt.ConnectionType.DirectConnection)
    worker.start()
    assert worker.wait(5000)
    assert len(errors) == 1


