"""Unit tests for flyio_utils.py."""
import json
from unittest.mock import MagicMock, patch

import flyio_utils


def _sse_lines(events: list[dict]) -> list[bytes]:
    return [f"data: {json.dumps(ev)}\n".encode() for ev in events]


def _fake_sse_urlopen(lines: list[bytes]) -> MagicMock:
    resp = MagicMock()
    resp.__iter__ = lambda s: iter(lines)
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def _fake_json_urlopen(payload) -> MagicMock:
    resp = MagicMock()
    resp.read.return_value = json.dumps(payload).encode()
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


# ── list_apps ──────────────────────────────────────────────────────────────────

def test_list_apps_returns_named_apps():
    payload = {"apps": [
        {"id": "a1", "name": "my-app", "status": "running"},
        {"id": "a2", "name": "", "status": "stopped"},
    ]}
    with patch("urllib.request.urlopen", return_value=_fake_json_urlopen(payload)):
        result = flyio_utils.list_apps("token")
    assert len(result) == 1
    assert result[0]["name"] == "my-app"


def test_list_apps_accepts_bare_list():
    payload = [{"id": "x", "name": "app", "status": "running"}]
    with patch("urllib.request.urlopen", return_value=_fake_json_urlopen(payload)):
        result = flyio_utils.list_apps("token")
    assert result[0]["name"] == "app"


def test_list_apps_raises_on_http_error():
    import urllib.error
    err = urllib.error.HTTPError(url="", code=401, msg="Unauthorized", hdrs={}, fp=MagicMock())
    err.read = lambda: b'{"error": "bad token"}'
    with patch("urllib.request.urlopen", side_effect=err):
        try:
            flyio_utils.list_apps("bad_token")
            assert False
        except RuntimeError as e:
            assert "401" in str(e)


# ── fetch_logs_sse ─────────────────────────────────────────────────────────────

def test_fetch_logs_sse_basic():
    events = [{"message": "hello", "timestamp": "2023-11-14T12:00:00Z", "region": "", "level": ""}]
    with patch("urllib.request.urlopen", return_value=_fake_sse_urlopen(_sse_lines(events))):
        result = flyio_utils.fetch_logs_sse("token", "my-app")
    assert len(result) == 1
    assert result[0][1] == "hello"


def test_fetch_logs_sse_skips_ping():
    lines = [b"data: ping\n", b"data: \n"]
    with patch("urllib.request.urlopen", return_value=_fake_sse_urlopen(lines)):
        result = flyio_utils.fetch_logs_sse("token", "my-app")
    assert result == []


def test_fetch_logs_sse_skips_non_data_lines():
    lines = [
        b"event: message\n",
        b": keep-alive\n",
        b"data: " + json.dumps({"message": "real", "timestamp": "", "region": "", "level": ""}).encode() + b"\n",
    ]
    with patch("urllib.request.urlopen", return_value=_fake_sse_urlopen(lines)):
        result = flyio_utils.fetch_logs_sse("token", "my-app")
    assert len(result) == 1
    assert result[0][1] == "real"


def test_fetch_logs_sse_adds_region_prefix():
    events = [{"message": "msg", "timestamp": "", "region": "ams", "level": ""}]
    with patch("urllib.request.urlopen", return_value=_fake_sse_urlopen(_sse_lines(events))):
        result = flyio_utils.fetch_logs_sse("token", "my-app")
    assert result[0][1] == "[ams] msg"


def test_fetch_logs_sse_adds_non_info_level_prefix():
    events = [{"message": "oops", "timestamp": "", "region": "", "level": "error"}]
    with patch("urllib.request.urlopen", return_value=_fake_sse_urlopen(_sse_lines(events))):
        result = flyio_utils.fetch_logs_sse("token", "my-app")
    assert result[0][1] == "[error] oops"


def test_fetch_logs_sse_info_level_no_prefix():
    events = [{"message": "ok", "timestamp": "", "region": "", "level": "info"}]
    with patch("urllib.request.urlopen", return_value=_fake_sse_urlopen(_sse_lines(events))):
        result = flyio_utils.fetch_logs_sse("token", "my-app")
    assert result[0][1] == "ok"


def test_fetch_logs_sse_region_and_level_both_present():
    events = [{"message": "bad", "timestamp": "", "region": "lhr", "level": "error"}]
    with patch("urllib.request.urlopen", return_value=_fake_sse_urlopen(_sse_lines(events))):
        result = flyio_utils.fetch_logs_sse("token", "my-app")
    msg = result[0][1]
    assert "[lhr]" in msg
    assert "[error]" in msg
    assert "bad" in msg


def test_fetch_logs_sse_respects_limit():
    events = [{"message": f"line{i}", "timestamp": "", "region": "", "level": ""} for i in range(10)]
    with patch("urllib.request.urlopen", return_value=_fake_sse_urlopen(_sse_lines(events))):
        result = flyio_utils.fetch_logs_sse("token", "my-app", limit=3)
    assert len(result) == 3


def test_fetch_logs_sse_skips_empty_message():
    events = [{"message": "", "timestamp": "", "region": "", "level": ""}]
    with patch("urllib.request.urlopen", return_value=_fake_sse_urlopen(_sse_lines(events))):
        result = flyio_utils.fetch_logs_sse("token", "my-app")
    assert result == []


def test_fetch_logs_sse_parses_iso_timestamp():
    events = [{"message": "ts-test", "timestamp": "2023-11-14T12:00:00Z", "region": "", "level": ""}]
    with patch("urllib.request.urlopen", return_value=_fake_sse_urlopen(_sse_lines(events))):
        result = flyio_utils.fetch_logs_sse("token", "my-app")
    assert result[0][0] > 0


def test_fetch_logs_sse_skips_invalid_json():
    lines = [b"data: {invalid json}\n"]
    with patch("urllib.request.urlopen", return_value=_fake_sse_urlopen(lines)):
        result = flyio_utils.fetch_logs_sse("token", "my-app")
    assert result == []
