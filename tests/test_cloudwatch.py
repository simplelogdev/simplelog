"""Tests for cloudwatch.py — all AWS calls are mocked."""
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

import cloudwatch

# ── helpers ───────────────────────────────────────────────────────────────────

def _client_error(code: str = "AccessDeniedException") -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": "mock"}}, "op")


def _make_paginator(pages: list[dict]):
    """Return a mock paginator whose paginate() yields *pages*."""
    pag = MagicMock()
    pag.paginate.return_value = iter(pages)
    return pag


# ── list_profiles ─────────────────────────────────────────────────────────────

def test_list_profiles_returns_profiles(tmp_path):
    creds = tmp_path / "credentials"
    creds.write_text("[dev]\naws_access_key_id=A\n[default]\naws_access_key_id=B\n")
    cfg = tmp_path / "config"
    cfg.write_text("[profile prod]\nregion=eu-west-1\n")
    with patch("os.path.expanduser", side_effect=lambda p: str(creds) if "credentials" in p else str(cfg)):
        result = cloudwatch.list_profiles()
    assert result == ["dev", "prod"]


def test_list_profiles_empty(tmp_path):
    with patch("os.path.expanduser", return_value=str(tmp_path / "nonexistent")):
        result = cloudwatch.list_profiles()
    assert result == []


# ── make_client ───────────────────────────────────────────────────────────────

def test_make_client_with_profile():
    mock_session = MagicMock()
    with patch("cloudwatch.boto3.Session", return_value=mock_session) as mock_cls:
        cloudwatch.make_client(profile="dev", region="eu-west-1")
    mock_cls.assert_called_once_with(profile_name="dev", region_name="eu-west-1")
    mock_session.client.assert_called_once_with("logs")


def test_make_client_with_access_keys():
    mock_session = MagicMock()
    with patch("cloudwatch.boto3.Session", return_value=mock_session) as mock_cls:
        cloudwatch.make_client(
            region="us-east-1",
            access_key_id="AKID",
            secret_access_key="SECRET",
        )
    mock_cls.assert_called_once_with(
        aws_access_key_id="AKID",
        aws_secret_access_key="SECRET",
        region_name="us-east-1",
    )
    mock_session.client.assert_called_once_with("logs")


def test_make_client_default():
    mock_session = MagicMock()
    with patch("cloudwatch.boto3.Session", return_value=mock_session) as mock_cls:
        cloudwatch.make_client()
    mock_cls.assert_called_once_with(profile_name=None, region_name="us-east-1")


# ── list_log_groups ───────────────────────────────────────────────────────────

def test_list_log_groups_basic():
    client = MagicMock()
    client.get_paginator.return_value = _make_paginator([
        {"logGroups": [{"logGroupName": "/aws/lambda/fn"}, {"logGroupName": "/app/web"}]},
    ])
    result = cloudwatch.list_log_groups(client)
    assert result == ["/app/web", "/aws/lambda/fn"]  # sorted


def test_list_log_groups_multiple_pages():
    client = MagicMock()
    client.get_paginator.return_value = _make_paginator([
        {"logGroups": [{"logGroupName": "/c"}, {"logGroupName": "/a"}]},
        {"logGroups": [{"logGroupName": "/b"}]},
    ])
    result = cloudwatch.list_log_groups(client)
    assert result == ["/a", "/b", "/c"]


def test_list_log_groups_with_prefix():
    client = MagicMock()
    client.get_paginator.return_value = _make_paginator([
        {"logGroups": [{"logGroupName": "/app/svc"}]},
    ])
    cloudwatch.list_log_groups(client, prefix="/app")
    _, call_kwargs = client.get_paginator.return_value.paginate.call_args
    assert call_kwargs.get("logGroupNamePrefix") == "/app"


def test_list_log_groups_client_error_raises_runtime():
    client = MagicMock()
    paginator = MagicMock()
    paginator.paginate.side_effect = _client_error()
    client.get_paginator.return_value = paginator
    with pytest.raises(RuntimeError):
        cloudwatch.list_log_groups(client)


def test_list_log_groups_empty():
    client = MagicMock()
    client.get_paginator.return_value = _make_paginator([{"logGroups": []}])
    assert cloudwatch.list_log_groups(client) == []


# ── list_log_streams ──────────────────────────────────────────────────────────

def test_list_log_streams_basic():
    client = MagicMock()
    client.get_paginator.return_value = _make_paginator([
        {"logStreams": [{"logStreamName": "stream-a"}, {"logStreamName": "stream-b"}]},
    ])
    result = cloudwatch.list_log_streams(client, "/my/group")
    assert result == ["stream-a", "stream-b"]


def test_list_log_streams_caps_at_200():
    """The 200-stream cap stops pagination after the page that crosses the threshold."""
    client = MagicMock()
    page1 = [{"logStreamName": f"s{i}"} for i in range(200)]
    page2 = [{"logStreamName": f"extra{i}"} for i in range(50)]
    client.get_paginator.return_value = _make_paginator([
        {"logStreams": page1},
        {"logStreams": page2},
    ])
    result = cloudwatch.list_log_streams(client, "/g")
    assert len(result) == 200
    assert not any(s.startswith("extra") for s in result)


def test_list_log_streams_prefix_disables_ordering():
    client = MagicMock()
    client.get_paginator.return_value = _make_paginator([{"logStreams": []}])
    cloudwatch.list_log_streams(client, "/g", prefix="app-")
    call_kwargs = client.get_paginator.return_value.paginate.call_args[1]
    assert "orderBy" not in call_kwargs
    assert "descending" not in call_kwargs
    assert call_kwargs.get("logStreamNamePrefix") == "app-"


def test_list_log_streams_client_error_raises_runtime():
    client = MagicMock()
    paginator = MagicMock()
    paginator.paginate.side_effect = _client_error()
    client.get_paginator.return_value = paginator
    with pytest.raises(RuntimeError):
        cloudwatch.list_log_streams(client, "/g")


# ── fetch_events ──────────────────────────────────────────────────────────────

def test_fetch_events_basic():
    client = MagicMock()
    client.get_paginator.return_value = _make_paginator([
        {"events": [
            {"timestamp": 1000, "message": "hello\n"},
            {"timestamp": 2000, "message": "world"},
        ]},
    ])
    result = cloudwatch.fetch_events(client, "/g")
    assert result == [(1000, "hello"), (2000, "world")]


def test_fetch_events_with_filter_pattern():
    client = MagicMock()
    client.get_paginator.return_value = _make_paginator([{"events": []}])
    cloudwatch.fetch_events(client, "/g", filter_pattern="ERROR")
    call_kwargs = client.get_paginator.return_value.paginate.call_args[1]
    assert call_kwargs.get("filterPattern") == "ERROR"


def test_fetch_events_with_log_stream():
    client = MagicMock()
    client.get_paginator.return_value = _make_paginator([{"events": []}])
    cloudwatch.fetch_events(client, "/g", log_stream="my-stream")
    call_kwargs = client.get_paginator.return_value.paginate.call_args[1]
    assert call_kwargs.get("logStreamNames") == ["my-stream"]


def test_fetch_events_max_events_cap():
    """max_events stops pagination after the page that crosses the threshold."""
    client = MagicMock()
    page1 = [{"timestamp": i, "message": f"line{i}"} for i in range(500)]
    page2 = [{"timestamp": 999, "message": "overflow"}]
    client.get_paginator.return_value = _make_paginator([
        {"events": page1},
        {"events": page2},
    ])
    result = cloudwatch.fetch_events(client, "/g", max_events=500)
    assert len(result) == 500
    assert all(msg != "overflow" for _, msg in result)


def test_fetch_events_unlimited_when_none():
    client = MagicMock()
    events = [{"timestamp": i, "message": f"line{i}"} for i in range(600)]
    client.get_paginator.return_value = _make_paginator([{"events": events}])
    result = cloudwatch.fetch_events(client, "/g", max_events=None)
    assert len(result) == 600


def test_fetch_events_client_error_raises_runtime():
    client = MagicMock()
    paginator = MagicMock()
    paginator.paginate.side_effect = _client_error()
    client.get_paginator.return_value = paginator
    with pytest.raises(RuntimeError):
        cloudwatch.fetch_events(client, "/g")


def test_fetch_events_start_ms_forwarded():
    client = MagicMock()
    client.get_paginator.return_value = _make_paginator([{"events": []}])
    cloudwatch.fetch_events(client, "/g", start_ms=12345)
    call_kwargs = client.get_paginator.return_value.paginate.call_args[1]
    assert call_kwargs.get("startTime") == 12345
