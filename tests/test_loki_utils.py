"""Unit tests for loki_utils.py."""
import json
from unittest.mock import MagicMock, patch

import loki_utils


def _fake_urlopen(payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.read.return_value = json.dumps(payload).encode()
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


# ── verify_connection ──────────────────────────────────────────────────────────

def test_verify_connection_returns_labels():
    payload = {"status": "success", "data": ["app", "env", "host"]}
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        labels = loki_utils.verify_connection("http://loki:3100")
    assert labels == ["app", "env", "host"]


def test_verify_connection_empty_labels():
    with patch("urllib.request.urlopen", return_value=_fake_urlopen({"data": []})):
        assert loki_utils.verify_connection("http://loki:3100") == []


def test_verify_connection_uses_bearer_token():
    payload = {"data": ["x"]}
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)) as mock_open:
        loki_utils.verify_connection("http://loki:3100", token="mytoken")
    req = mock_open.call_args[0][0]
    assert req.get_header("Authorization") == "Bearer mytoken"


def test_verify_connection_uses_basic_auth():
    import base64
    payload = {"data": ["x"]}
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)) as mock_open:
        loki_utils.verify_connection("http://loki:3100", username="user", password="pass")
    req = mock_open.call_args[0][0]
    expected = "Basic " + base64.b64encode(b"user:pass").decode()
    assert req.get_header("Authorization") == expected


def test_verify_connection_no_auth_header_when_no_creds():
    payload = {"data": []}
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)) as mock_open:
        loki_utils.verify_connection("http://loki:3100")
    req = mock_open.call_args[0][0]
    assert req.get_header("Authorization") is None


# ── fetch_logs ─────────────────────────────────────────────────────────────────

def test_fetch_logs_returns_sorted_tuples():
    payload = {
        "data": {
            "result": [
                {"values": [
                    ["1700000002000000000", "second"],
                    ["1700000001000000000", "first"],
                ]},
            ]
        }
    }
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        result = loki_utils.fetch_logs("http://loki:3100", '{app="x"}', 0, 9999)
    assert len(result) == 2
    assert result[0] == (1700000001000, "first")
    assert result[1] == (1700000002000, "second")


def test_fetch_logs_empty_result():
    payload = {"data": {"result": []}}
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        result = loki_utils.fetch_logs("http://loki:3100", '{app="x"}', 0, 9999)
    assert result == []


def test_fetch_logs_converts_ns_to_ms():
    ts_ns = 1_700_000_000_123_456_789
    payload = {"data": {"result": [{"values": [[str(ts_ns), "msg"]]}]}}
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        result = loki_utils.fetch_logs("http://loki:3100", '{a="b"}', 0, 9999)
    assert result[0][0] == ts_ns // 1_000_000


def test_fetch_logs_multiple_streams():
    payload = {
        "data": {
            "result": [
                {"values": [["1000000000", "stream1"]]},
                {"values": [["2000000000", "stream2"]]},
            ]
        }
    }
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        result = loki_utils.fetch_logs("http://loki:3100", '{a="b"}', 0, 9999)
    assert len(result) == 2
    assert result[0][1] == "stream1"


def test_fetch_logs_raises_on_http_error():
    import urllib.error
    err = urllib.error.HTTPError(url="", code=401, msg="Unauthorized", hdrs={}, fp=MagicMock())
    err.read = lambda: b'{"message": "Unauthorized"}'
    with patch("urllib.request.urlopen", side_effect=err):
        try:
            loki_utils.fetch_logs("http://loki:3100", '{a="b"}', 0, 9999)
            assert False
        except RuntimeError as e:
            assert "401" in str(e)


def test_request_builds_correct_url():
    payload = {"data": []}
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)) as mock_open:
        loki_utils.verify_connection("http://loki:3100/")
    req = mock_open.call_args[0][0]
    assert req.full_url.startswith("http://loki:3100/loki/api/v1/labels")
