"""Unit tests for elastic_utils.py."""
import json
from unittest.mock import MagicMock, patch

import elastic_utils


def _fake_urlopen(payload) -> MagicMock:
    resp = MagicMock()
    resp.read.return_value = json.dumps(payload).encode()
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


BASE = "http://localhost:9200"


# ── verify_connection ──────────────────────────────────────────────────────────

def test_verify_connection_returns_cluster_info():
    info = {"name": "node-1", "version": {"number": "8.0.0"}}
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(info)):
        result = elastic_utils.verify_connection(BASE, api_key="k")
    assert result["name"] == "node-1"


def test_verify_connection_raises_on_http_error():
    import urllib.error
    err = urllib.error.HTTPError(url="", code=401, msg="Unauthorized", hdrs={}, fp=MagicMock())
    err.read = lambda: b'{"message": "missing auth"}'
    with patch("urllib.request.urlopen", side_effect=err):
        try:
            elastic_utils.verify_connection(BASE)
            assert False
        except RuntimeError as e:
            assert "401" in str(e)


# ── list_indices ───────────────────────────────────────────────────────────────

def test_list_indices_filters_system_indices():
    payload = [
        {"index": "my-logs"},
        {"index": ".kibana"},
        {"index": "app-events"},
        {"index": ".monitoring"},
    ]
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        result = elastic_utils.list_indices(BASE)
    assert result == ["app-events", "my-logs"]


def test_list_indices_empty():
    with patch("urllib.request.urlopen", return_value=_fake_urlopen([])):
        assert elastic_utils.list_indices(BASE) == []


def test_list_indices_non_list_response_returns_empty():
    with patch("urllib.request.urlopen", return_value=_fake_urlopen({"error": "oops"})):
        assert elastic_utils.list_indices(BASE) == []


def test_list_indices_sorted_alphabetically():
    payload = [{"index": "zzz"}, {"index": "aaa"}, {"index": "mmm"}]
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        result = elastic_utils.list_indices(BASE)
    assert result == ["aaa", "mmm", "zzz"]


def test_list_indices_uses_api_key_header():
    payload = []
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)) as mock_open:
        elastic_utils.list_indices(BASE, api_key="mykey")
    req = mock_open.call_args[0][0]
    assert req.get_header("Authorization") == "ApiKey mykey"


def test_list_indices_uses_basic_auth():
    import base64
    payload = []
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)) as mock_open:
        elastic_utils.list_indices(BASE, username="admin", password="secret")
    req = mock_open.call_args[0][0]
    expected = "Basic " + base64.b64encode(b"admin:secret").decode()
    assert req.get_header("Authorization") == expected


# ── fetch_logs ─────────────────────────────────────────────────────────────────

def test_fetch_logs_returns_events_and_sort():
    hit = {
        "_source": {"@timestamp": "2023-11-14T12:00:00Z", "message": "hello"},
        "sort": ["2023-11-14T12:00:00Z", "abc123"],
    }
    payload = {"hits": {"hits": [hit]}}
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        events, last_sort = elastic_utils.fetch_logs(BASE, "my-index", "*")
    assert len(events) == 1
    ts, msg = events[0]
    assert msg == "hello"
    assert ts > 0
    assert last_sort == ["2023-11-14T12:00:00Z", "abc123"]


def test_fetch_logs_empty_hits():
    payload = {"hits": {"hits": []}}
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        events, last_sort = elastic_utils.fetch_logs(BASE, "my-index", "*")
    assert events == []
    assert last_sort == []


def test_fetch_logs_falls_back_to_log_field():
    hit = {"_source": {"log": "fallback message"}, "sort": []}
    payload = {"hits": {"hits": [hit]}}
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        events, _ = elastic_utils.fetch_logs(BASE, "idx", "*")
    assert events[0][1] == "fallback message"


def test_fetch_logs_bad_timestamp_is_zero():
    hit = {"_source": {"@timestamp": "bad", "message": "msg"}, "sort": []}
    payload = {"hits": {"hits": [hit]}}
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        events, _ = elastic_utils.fetch_logs(BASE, "idx", "*")
    assert events[0][0] == 0


def test_fetch_logs_with_search_after_included_in_body():
    payload = {"hits": {"hits": []}}
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)) as mock_open:
        elastic_utils.fetch_logs(BASE, "idx", "*", search_after=["val1", "val2"])
    req = mock_open.call_args[0][0]
    body = json.loads(req.data)
    assert body["search_after"] == ["val1", "val2"]
