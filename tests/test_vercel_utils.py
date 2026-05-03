"""Unit tests for vercel_utils.py."""
import json
from unittest.mock import MagicMock, patch

import vercel_utils


def _fake_urlopen(payload) -> MagicMock:
    resp = MagicMock()
    resp.read.return_value = json.dumps(payload).encode()
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


# ── list_projects ──────────────────────────────────────────────────────────────

def test_list_projects_returns_list():
    payload = {
        "projects": [
            {"id": "p1", "name": "my-app", "framework": "nextjs", "updatedAt": 1700000000},
            {"id": "p2", "name": "api", "framework": None, "updatedAt": 1700000001},
        ]
    }
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        result = vercel_utils.list_projects("token123")
    assert len(result) == 2
    assert result[0]["name"] == "my-app"
    assert result[0]["framework"] == "nextjs"
    assert result[1]["framework"] == ""


def test_list_projects_skips_entries_without_name():
    payload = {"projects": [{"id": "p1", "name": "", "framework": None, "updatedAt": 0}]}
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        result = vercel_utils.list_projects("token123")
    assert result == []


def test_list_projects_accepts_bare_list():
    payload = [{"id": "p1", "name": "proj", "framework": "vite", "updatedAt": 0}]
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        result = vercel_utils.list_projects("token123")
    assert len(result) == 1


# ── get_latest_deployment ──────────────────────────────────────────────────────

def test_get_latest_deployment_returns_dict():
    payload = {
        "deployments": [
            {"uid": "dpl_abc", "url": "proj.vercel.app", "state": "READY", "createdAt": 1700000000}
        ]
    }
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        result = vercel_utils.get_latest_deployment("tok", "proj_id")
    assert result["id"] == "dpl_abc"
    assert result["state"] == "READY"


def test_get_latest_deployment_falls_back_to_any_when_empty():
    empty = {"deployments": []}
    any_payload = {
        "deployments": [
            {"uid": "dpl_fallback", "url": "x.vercel.app", "state": "READY", "createdAt": 0}
        ]
    }
    calls = [_fake_urlopen(empty), _fake_urlopen(any_payload)]
    with patch("urllib.request.urlopen", side_effect=calls):
        result = vercel_utils.get_latest_deployment("tok", "proj_id", target="production")
    assert result["id"] == "dpl_fallback"


def test_get_latest_deployment_returns_none_when_truly_empty():
    payload = {"deployments": []}
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        result = vercel_utils.get_latest_deployment("tok", "proj_id", target="any")
    assert result is None


# ── fetch_deployment_events ────────────────────────────────────────────────────

def test_fetch_deployment_events_returns_tuples():
    payload = [
        {"payload": {"text": "Build started", "date": 1700000000000}, "createdAt": 0},
        {"payload": {"text": "Build succeeded", "date": 1700000001000}, "createdAt": 0},
    ]
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        result = vercel_utils.fetch_deployment_events("tok", "dpl_abc")
    assert len(result) == 2
    assert result[0] == (1700000000000, "Build started")
    assert result[1] == (1700000001000, "Build succeeded")


def test_fetch_deployment_events_handles_iso_timestamp():
    payload = [
        {"payload": {"text": "Deploying", "date": "2023-11-14T12:00:00Z"}}
    ]
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        result = vercel_utils.fetch_deployment_events("tok", "dpl_abc")
    assert len(result) == 1
    ts_ms, msg = result[0]
    assert msg == "Deploying"
    assert ts_ms > 0


def test_fetch_deployment_events_skips_empty_text():
    payload = [
        {"payload": {"text": "", "date": 1000}},
        {"payload": {"text": "Real message", "date": 2000}},
    ]
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        result = vercel_utils.fetch_deployment_events("tok", "dpl_abc")
    assert len(result) == 1
    assert result[0][1] == "Real message"


def test_fetch_deployment_events_accepts_events_key():
    payload = {"events": [{"payload": {"text": "hello", "date": 500}}]}
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        result = vercel_utils.fetch_deployment_events("tok", "dpl_abc")
    assert result[0][1] == "hello"


# ── HTTP error handling ────────────────────────────────────────────────────────

def test_list_projects_raises_on_http_error():
    import urllib.error
    err = urllib.error.HTTPError(url="", code=401, msg="Unauthorized", hdrs={}, fp=MagicMock())
    err.read = lambda: b'{"error": {"message": "bad token"}}'
    with patch("urllib.request.urlopen", side_effect=err):
        try:
            vercel_utils.list_projects("bad_token")
            assert False
        except RuntimeError as e:
            assert "401" in str(e)
