"""Unit tests for railway_utils.py."""
import json
from unittest.mock import MagicMock, patch

import railway_utils


def _fake_urlopen(payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.read.return_value = json.dumps(payload).encode()
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


# ── verify_token ───────────────────────────────────────────────────────────────

def test_verify_token_returns_user_info():
    payload = {"data": {"me": {"name": "Alice", "email": "alice@example.com"}}}
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        result = railway_utils.verify_token("mytoken")
    assert result == {"name": "Alice", "email": "alice@example.com"}


def test_verify_token_raises_on_gql_errors():
    payload = {"errors": [{"message": "Unauthorized"}]}
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        try:
            railway_utils.verify_token("bad_token")
            assert False
        except RuntimeError as e:
            assert "Unauthorized" in str(e)


def test_verify_token_raises_on_http_error():
    import urllib.error
    err = urllib.error.HTTPError(url="", code=401, msg="Unauthorized", hdrs={}, fp=MagicMock())
    err.read = lambda: b'{"errors": [{"message": "bad token"}]}'
    with patch("urllib.request.urlopen", side_effect=err):
        try:
            railway_utils.verify_token("bad")
            assert False
        except RuntimeError as e:
            assert "401" in str(e)


# ── list_projects ──────────────────────────────────────────────────────────────

def test_list_projects_returns_projects_with_services():
    payload = {
        "data": {
            "projects": {
                "edges": [
                    {
                        "node": {
                            "id": "proj1",
                            "name": "My Project",
                            "services": {
                                "edges": [
                                    {"node": {"id": "svc1", "name": "web"}},
                                    {"node": {"id": "svc2", "name": "worker"}},
                                ]
                            },
                        }
                    }
                ]
            }
        }
    }
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        result = railway_utils.list_projects("token")
    assert len(result) == 1
    assert result[0]["name"] == "My Project"
    assert len(result[0]["services"]) == 2
    assert result[0]["services"][0] == {"id": "svc1", "name": "web"}


def test_list_projects_empty():
    payload = {"data": {"projects": {"edges": []}}}
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        assert railway_utils.list_projects("token") == []


# ── get_latest_deployment ──────────────────────────────────────────────────────

def test_get_latest_deployment_returns_dict():
    payload = {
        "data": {
            "deployments": {
                "edges": [
                    {"node": {"id": "dep1", "status": "SUCCESS", "createdAt": "2023-11-14T12:00:00Z"}}
                ]
            }
        }
    }
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        result = railway_utils.get_latest_deployment("token", "svc1")
    assert result["id"] == "dep1"
    assert result["status"] == "SUCCESS"


def test_get_latest_deployment_returns_none_when_empty():
    payload = {"data": {"deployments": {"edges": []}}}
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        result = railway_utils.get_latest_deployment("token", "svc1")
    assert result is None


# ── fetch_deployment_logs ──────────────────────────────────────────────────────

def test_fetch_deployment_logs_returns_tuples():
    payload = {
        "data": {
            "deploymentLogs": [
                {"message": "Build started", "severity": "INFO", "timestamp": "2023-11-14T12:00:00Z"},
                {"message": "Build finished", "severity": "INFO", "timestamp": "2023-11-14T12:00:10Z"},
            ]
        }
    }
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        result = railway_utils.fetch_deployment_logs("token", "dep1")
    assert len(result) == 2
    assert result[0][1] == "Build started"
    assert result[1][1] == "Build finished"
    assert result[0][0] < result[1][0]


def test_fetch_deployment_logs_skips_empty_messages():
    payload = {
        "data": {
            "deploymentLogs": [
                {"message": "", "severity": "INFO", "timestamp": "2023-11-14T12:00:00Z"},
                {"message": "real", "severity": "INFO", "timestamp": "2023-11-14T12:00:01Z"},
            ]
        }
    }
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        result = railway_utils.fetch_deployment_logs("token", "dep1")
    assert len(result) == 1
    assert result[0][1] == "real"


def test_fetch_deployment_logs_bad_timestamp_is_zero():
    payload = {
        "data": {
            "deploymentLogs": [
                {"message": "msg", "severity": "INFO", "timestamp": "not-a-date"},
            ]
        }
    }
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        result = railway_utils.fetch_deployment_logs("token", "dep1")
    assert result[0][0] == 0


def test_fetch_deployment_logs_empty():
    payload = {"data": {"deploymentLogs": []}}
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        assert railway_utils.fetch_deployment_logs("token", "dep1") == []


def test_gql_sends_bearer_auth():
    payload = {"data": {"me": {"name": "test", "email": "t@t.com"}}}
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)) as mock_open:
        railway_utils.verify_token("my_secret_token")
    req = mock_open.call_args[0][0]
    assert req.get_header("Authorization") == "Bearer my_secret_token"
