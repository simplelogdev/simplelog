"""Unit tests for cloudflare_utils.py."""
from __future__ import annotations

import json
import os
import struct
import time
import urllib.error
from unittest.mock import MagicMock, patch

import cloudflare_utils

# ── Helpers ───────────────────────────────────────────────────────────────────

def _fake_urlopen(payload: dict, status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.read.return_value = json.dumps(payload).encode()
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def _http_error(code: int, body: bytes = b"") -> urllib.error.HTTPError:
    err = urllib.error.HTTPError(url="", code=code, msg="", hdrs={}, fp=MagicMock())
    err.read = lambda: body
    return err


# ── list_workers ──────────────────────────────────────────────────────────────

def test_list_workers_returns_sorted_names():
    payload = {
        "success": True,
        "result": [
            {"id": "worker-b", "etag": "x"},
            {"id": "worker-a", "etag": "y"},
            {"id": "worker-c", "etag": "z"},
        ],
    }
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        result = cloudflare_utils.list_workers("token", "account123")
    assert result == ["worker-a", "worker-b", "worker-c"]


def test_list_workers_skips_entries_without_id():
    payload = {
        "success": True,
        "result": [{"id": "good"}, {"id": ""}, {}],
    }
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        result = cloudflare_utils.list_workers("token", "acct")
    assert result == ["good"]


def test_list_workers_empty_result():
    payload = {"success": True, "result": []}
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        result = cloudflare_utils.list_workers("token", "acct")
    assert result == []


def test_list_workers_raises_on_api_failure():
    payload = {"success": False, "errors": [{"message": "Auth error"}]}
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        try:
            cloudflare_utils.list_workers("bad", "acct")
            assert False, "should raise"
        except RuntimeError as e:
            assert "Auth error" in str(e)


def test_list_workers_raises_on_http_error():
    err = _http_error(401, b'{"errors": [{"message": "Unauthorized"}]}')
    with patch("urllib.request.urlopen", side_effect=err):
        try:
            cloudflare_utils.list_workers("bad", "acct")
            assert False, "should raise"
        except RuntimeError as e:
            assert "401" in str(e)


def test_list_workers_raises_on_http_error_non_json_body():
    err = _http_error(500, b"Internal Server Error")
    with patch("urllib.request.urlopen", side_effect=err):
        try:
            cloudflare_utils.list_workers("t", "a")
            assert False
        except RuntimeError as e:
            assert "500" in str(e)


def test_list_workers_sends_bearer_auth():
    payload = {"success": True, "result": []}
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)) as mock_open:
        cloudflare_utils.list_workers("my_secret_token", "acct")
    req = mock_open.call_args[0][0]
    assert req.get_header("Authorization") == "Bearer my_secret_token"


# ── create_tail ───────────────────────────────────────────────────────────────

def test_create_tail_returns_result_dict():
    payload = {
        "success": True,
        "result": {
            "id": "tail-xyz",
            "url": "wss://tail.developers.workers.dev/tail-xyz",
            "expires_at": "2024-01-01T00:00:00Z",
        },
    }
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        result = cloudflare_utils.create_tail("token", "acct", "my-worker")
    assert result["id"] == "tail-xyz"
    assert result["url"].startswith("wss://")


def test_create_tail_raises_on_api_failure():
    payload = {"success": False, "errors": [{"message": "Worker not found"}]}
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        try:
            cloudflare_utils.create_tail("t", "a", "missing-worker")
            assert False, "should raise"
        except RuntimeError as e:
            assert "Worker not found" in str(e)


def test_create_tail_raises_on_http_error():
    err = _http_error(403, b'{"errors": [{"message": "Forbidden"}]}')
    with patch("urllib.request.urlopen", side_effect=err):
        try:
            cloudflare_utils.create_tail("t", "a", "w")
            assert False
        except RuntimeError as e:
            assert "403" in str(e)


def test_create_tail_uses_post():
    payload = {"success": True, "result": {"id": "t", "url": "wss://x", "expires_at": ""}}
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)) as mock_open:
        cloudflare_utils.create_tail("token", "acct", "worker")
    req = mock_open.call_args[0][0]
    assert req.get_method() == "POST"


# ── delete_tail ───────────────────────────────────────────────────────────────

def test_delete_tail_suppresses_errors():
    with patch("urllib.request.urlopen", side_effect=Exception("network down")):
        cloudflare_utils.delete_tail("t", "a", "w", "tail-id")  # must not raise


def test_delete_tail_uses_delete_method():
    resp = MagicMock()
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=resp) as mock_open:
        cloudflare_utils.delete_tail("token", "acct", "worker", "tail-xyz")
    req = mock_open.call_args[0][0]
    assert req.get_method() == "DELETE"
    assert "tail-xyz" in req.full_url


# ── ws_recv_frame / ws_send_frame ─────────────────────────────────────────────

def _build_server_frame(opcode: int, payload: bytes, masked: bool = False) -> bytes:
    """Build a WebSocket frame as if sent by a server (unmasked by default)."""
    n = len(payload)
    mask_bit = 0x80 if masked else 0x00
    header = bytes([0x80 | opcode])
    if n < 126:
        header += bytes([mask_bit | n])
    elif n < 65536:
        header += bytes([mask_bit | 126]) + struct.pack(">H", n)
    else:
        header += bytes([mask_bit | 127]) + struct.pack(">Q", n)
    if masked:
        mask = os.urandom(4)
        header += mask
        payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    return header + payload


class _FakeSocket:
    """Feeds pre-built bytes to ws_recv_frame one recv() call at a time."""

    def __init__(self, data: bytes) -> None:
        self._buf = data
        self._pos = 0

    def recv(self, n: int) -> bytes:
        chunk = self._buf[self._pos:self._pos + n]
        self._pos += len(chunk)
        return chunk

    def sendall(self, data: bytes) -> None:
        pass  # capture in subclass if needed


def test_ws_recv_frame_text_frame():
    payload = b"hello world"
    frame = _build_server_frame(1, payload)
    ssock = _FakeSocket(frame)
    opcode, data = cloudflare_utils.ws_recv_frame(ssock)
    assert opcode == 1
    assert data == payload


def test_ws_recv_frame_binary_frame():
    payload = b"\x00\x01\x02\x03"
    frame = _build_server_frame(2, payload)
    ssock = _FakeSocket(frame)
    opcode, data = cloudflare_utils.ws_recv_frame(ssock)
    assert opcode == 2
    assert data == payload


def test_ws_recv_frame_126_length_encoding():
    payload = b"x" * 200
    frame = _build_server_frame(1, payload)
    ssock = _FakeSocket(frame)
    opcode, data = cloudflare_utils.ws_recv_frame(ssock)
    assert opcode == 1
    assert len(data) == 200


def test_ws_recv_frame_masked_payload():
    payload = b"secret"
    frame = _build_server_frame(1, payload, masked=True)
    ssock = _FakeSocket(frame)
    opcode, data = cloudflare_utils.ws_recv_frame(ssock)
    assert opcode == 1
    assert data == payload


def test_ws_recv_frame_ping():
    frame = _build_server_frame(9, b"")
    ssock = _FakeSocket(frame)
    opcode, data = cloudflare_utils.ws_recv_frame(ssock)
    assert opcode == 9


def test_ws_recv_frame_close():
    frame = _build_server_frame(8, b"")
    ssock = _FakeSocket(frame)
    opcode, _ = cloudflare_utils.ws_recv_frame(ssock)
    assert opcode == 8


def test_ws_recv_frame_eof_raises():
    ssock = _FakeSocket(b"")  # empty — recv returns b""
    try:
        cloudflare_utils.ws_recv_frame(ssock)
        assert False, "should raise EOFError"
    except EOFError:
        pass


class _CaptureSendSocket(_FakeSocket):
    def __init__(self) -> None:
        super().__init__(b"")
        self.sent: list[bytes] = []

    def sendall(self, data: bytes) -> None:
        self.sent.append(data)


def test_ws_send_frame_sets_fin_bit():
    sock = _CaptureSendSocket()
    cloudflare_utils.ws_send_frame(sock, 1, b"hi")
    frame = sock.sent[0]
    assert frame[0] & 0x80  # FIN bit
    assert frame[0] & 0x0F == 1  # opcode 1 = text


def test_ws_send_frame_sets_mask_bit():
    sock = _CaptureSendSocket()
    cloudflare_utils.ws_send_frame(sock, 1, b"data")
    frame = sock.sent[0]
    assert frame[1] & 0x80  # mask bit must be set (client→server)


def test_ws_send_frame_payload_is_masked():
    sock = _CaptureSendSocket()
    payload = b"hello"
    cloudflare_utils.ws_send_frame(sock, 1, payload)
    frame = sock.sent[0]
    # header: 2 bytes + 4 mask bytes = 6
    mask = frame[2:6]
    masked_payload = frame[6:]
    recovered = bytes(b ^ mask[i % 4] for i, b in enumerate(masked_payload))
    assert recovered == payload


def test_ws_send_frame_ping_no_payload():
    sock = _CaptureSendSocket()
    cloudflare_utils.ws_send_frame(sock, 9)
    frame = sock.sent[0]
    assert frame[0] & 0x0F == 9  # ping opcode


def test_ws_send_frame_126_length():
    sock = _CaptureSendSocket()
    cloudflare_utils.ws_send_frame(sock, 2, b"z" * 200)
    frame = sock.sent[0]
    assert frame[1] & 0x7F == 126  # extended 16-bit length follows


# ── parse_tail_event ──────────────────────────────────────────────────────────

def _make_event(**kwargs) -> bytes:
    base = {
        "scriptName": "my-worker",
        "outcome": "ok",
        "eventTimestamp": 1700000000000,
        "event": {},
        "logs": [],
        "exceptions": [],
    }
    base.update(kwargs)
    return json.dumps(base).encode()


def test_parse_tail_event_request_line():
    data = _make_event(
        event={"request": {"method": "GET", "url": "https://ex.com/api", "cf": {"colo": "CDG"}}},
    )
    events = cloudflare_utils.parse_tail_event(data)
    assert len(events) == 1
    ts, msg = events[0]
    assert ts == 1700000000000
    assert "GET" in msg
    assert "https://ex.com/api" in msg
    assert "CDG" in msg


def test_parse_tail_event_failed_outcome_in_request_line():
    data = _make_event(
        outcome="exception",
        event={"request": {"method": "POST", "url": "https://ex.com/crash", "cf": {}}},
    )
    events = cloudflare_utils.parse_tail_event(data)
    assert len(events) == 1
    assert "EXCEPTION" in events[0][1]


def test_parse_tail_event_console_log():
    data = _make_event(logs=[{"level": "log", "timestamp": 1700000001000, "message": ["hello", "world"]}])
    events = cloudflare_utils.parse_tail_event(data)
    assert len(events) == 1
    ts, msg = events[0]
    assert ts == 1700000001000
    assert "hello world" in msg
    assert "[LOG]" not in msg  # 'log' level has no prefix


def test_parse_tail_event_console_error_has_prefix():
    data = _make_event(logs=[{"level": "error", "timestamp": 1700000002000, "message": ["boom"]}])
    events = cloudflare_utils.parse_tail_event(data)
    assert "[ERROR]" in events[0][1]
    assert "boom" in events[0][1]


def test_parse_tail_event_console_warn_has_prefix():
    data = _make_event(logs=[{"level": "warn", "timestamp": 0, "message": ["careful"]}])
    events = cloudflare_utils.parse_tail_event(data)
    assert "[WARN]" in events[0][1]


def test_parse_tail_event_console_debug_has_prefix():
    data = _make_event(logs=[{"level": "debug", "timestamp": 0, "message": ["dbg"]}])
    events = cloudflare_utils.parse_tail_event(data)
    assert "[DEBUG]" in events[0][1]


def test_parse_tail_event_exception():
    data = _make_event(
        exceptions=[{"name": "TypeError", "message": "x is not a function", "timestamp": 1700000003000}]
    )
    events = cloudflare_utils.parse_tail_event(data)
    assert len(events) == 1
    ts, msg = events[0]
    assert ts == 1700000003000
    assert "[EXCEPTION]" in msg
    assert "TypeError" in msg
    assert "x is not a function" in msg


def test_parse_tail_event_all_three_combined():
    data = _make_event(
        event={"request": {"method": "GET", "url": "https://ex.com/", "cf": {}}},
        logs=[{"level": "log", "timestamp": 1, "message": ["ok"]}],
        exceptions=[{"name": "Error", "message": "fail", "timestamp": 2}],
    )
    events = cloudflare_utils.parse_tail_event(data)
    assert len(events) == 3  # request + log + exception


def test_parse_tail_event_no_request():
    data = _make_event(logs=[{"level": "log", "timestamp": 0, "message": ["only log"]}])
    events = cloudflare_utils.parse_tail_event(data)
    assert len(events) == 1
    assert "only log" in events[0][1]


def test_parse_tail_event_empty_logs_and_exceptions():
    data = _make_event()
    events = cloudflare_utils.parse_tail_event(data)
    assert events == []


def test_parse_tail_event_bad_json_returns_empty():
    events = cloudflare_utils.parse_tail_event(b"{not valid json}")
    assert events == []


def test_parse_tail_event_empty_bytes_returns_empty():
    events = cloudflare_utils.parse_tail_event(b"")
    assert events == []


def test_parse_tail_event_uses_event_timestamp_as_fallback():
    now = int(time.time() * 1000)
    data = json.dumps({
        "scriptName": "w",
        "outcome": "ok",
        "eventTimestamp": now,
        "event": {},
        "logs": [{"level": "log", "message": ["msg"]}],  # no timestamp
        "exceptions": [],
    }).encode()
    events = cloudflare_utils.parse_tail_event(data)
    assert events[0][0] == now


def test_parse_tail_event_message_list_joined():
    data = _make_event(logs=[{"level": "log", "timestamp": 0, "message": ["a", "b", "c"]}])
    events = cloudflare_utils.parse_tail_event(data)
    assert events[0][1] == "a b c"


def test_parse_tail_event_colo_absent_no_parentheses():
    data = _make_event(
        event={"request": {"method": "GET", "url": "https://ex.com/", "cf": {}}},
    )
    events = cloudflare_utils.parse_tail_event(data)
    assert "(" not in events[0][1]


def test_parse_tail_event_no_colo_key():
    data = _make_event(
        event={"request": {"method": "GET", "url": "https://ex.com/", "cf": None}},
    )
    events = cloudflare_utils.parse_tail_event(data)
    assert len(events) == 1  # must not crash


def test_parse_tail_event_ok_outcome_no_status_tag():
    data = _make_event(
        outcome="ok",
        event={"request": {"method": "GET", "url": "https://ex.com/", "cf": {}}},
    )
    events = cloudflare_utils.parse_tail_event(data)
    assert "[OK]" not in events[0][1]
    assert "[" not in events[0][1].split("//")[1]  # no brackets in path part
