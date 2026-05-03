"""Unit tests for datadog_utils.py."""
import json
import re
from unittest.mock import MagicMock, patch

import datadog_utils


def _fake_urlopen(payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.read.return_value = json.dumps(payload).encode()
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


BASE = "https://api.datadoghq.com"
API_KEY = "api_key_123"
APP_KEY = "app_key_456"


# ── now_iso / offset_iso ───────────────────────────────────────────────────────

def test_now_iso_format():
    ts = datadog_utils.now_iso()
    assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.000Z", ts)


def test_offset_iso_format():
    ts = datadog_utils.offset_iso(1.0)
    assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.000Z", ts)


def test_offset_iso_is_before_now():
    from datetime import UTC, datetime
    ts = datadog_utils.offset_iso(1.0)
    now = datadog_utils.now_iso()
    assert ts < now


# ── verify_connection ──────────────────────────────────────────────────────────

def test_verify_connection_succeeds():
    with patch("urllib.request.urlopen", return_value=_fake_urlopen({"data": []})):
        datadog_utils.verify_connection(BASE, API_KEY, APP_KEY)  # must not raise


def test_verify_connection_raises_on_error():
    import urllib.error
    err = urllib.error.HTTPError(url="", code=403, msg="Forbidden", hdrs={}, fp=MagicMock())
    err.read = lambda: b'{"errors": ["Forbidden"]}'
    with patch("urllib.request.urlopen", side_effect=err):
        try:
            datadog_utils.verify_connection(BASE, API_KEY, APP_KEY)
            assert False
        except RuntimeError as e:
            assert "403" in str(e)


# ── fetch_logs ─────────────────────────────────────────────────────────────────

def test_fetch_logs_returns_sorted_tuples():
    payload = {
        "data": [
            {"attributes": {"timestamp": "2023-11-14T12:00:02Z", "message": "second", "service": "", "status": ""}},
            {"attributes": {"timestamp": "2023-11-14T12:00:01Z", "message": "first", "service": "", "status": ""}},
        ]
    }
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        result = datadog_utils.fetch_logs(BASE, "*", "from", "to", API_KEY, APP_KEY)
    assert len(result) == 2
    assert result[0][1] == "first"
    assert result[1][1] == "second"


def test_fetch_logs_includes_service_and_status():
    payload = {
        "data": [
            {"attributes": {
                "timestamp": "2023-11-14T12:00:00Z",
                "message": "hello",
                "service": "my-svc",
                "status": "error",
            }}
        ]
    }
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        result = datadog_utils.fetch_logs(BASE, "*", "from", "to", API_KEY, APP_KEY)
    ts, msg = result[0]
    assert "[error]" in msg
    assert "my-svc" in msg
    assert "hello" in msg


def test_fetch_logs_status_only_no_service():
    payload = {
        "data": [
            {"attributes": {"timestamp": "2023-11-14T12:00:00Z", "message": "warn", "service": "", "status": "warn"}}
        ]
    }
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        result = datadog_utils.fetch_logs(BASE, "*", "from", "to", API_KEY, APP_KEY)
    assert result[0][1].startswith("[warn]")


def test_fetch_logs_empty_data():
    with patch("urllib.request.urlopen", return_value=_fake_urlopen({"data": []})):
        result = datadog_utils.fetch_logs(BASE, "*", "from", "to", API_KEY, APP_KEY)
    assert result == []


def test_fetch_logs_bad_timestamp_falls_back_to_zero():
    payload = {
        "data": [
            {"attributes": {"timestamp": "not-a-date", "message": "msg", "service": "", "status": ""}}
        ]
    }
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        result = datadog_utils.fetch_logs(BASE, "*", "from", "to", API_KEY, APP_KEY)
    assert result[0][0] == 0


def test_fetch_logs_sends_api_keys_in_headers():
    with patch("urllib.request.urlopen", return_value=_fake_urlopen({"data": []})) as mock_open:
        datadog_utils.fetch_logs(BASE, "*", "from", "to", API_KEY, APP_KEY)
    req = mock_open.call_args[0][0]
    assert req.get_header("Dd-api-key") == API_KEY
    assert req.get_header("Dd-application-key") == APP_KEY
