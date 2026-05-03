"""cloudflare_utils.py — Cloudflare Workers log helpers for SimpleLog."""
from __future__ import annotations

import base64
import contextlib
import json
import os
import socket
import ssl
import struct
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse

_API_BASE = "https://api.cloudflare.com/client/v4"


def _headers(api_token: str) -> dict:
    return {
        "Authorization": f"Bearer {api_token}",
        "Content-Type":  "application/json",
    }


def _get(path: str, api_token: str, timeout: int = 15) -> dict:
    req = urllib.request.Request(_API_BASE + path, headers=_headers(api_token))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(raw)
            msgs = [err.get("message", "") for err in body.get("errors", [])]
            msg = "; ".join(m for m in msgs if m) or raw
        except Exception:
            msg = raw
        raise RuntimeError(f"Cloudflare {e.code}: {msg}") from e
    except Exception as e:
        raise RuntimeError(str(e)) from e


def _post(path: str, api_token: str, body: dict | None = None) -> dict:
    data = json.dumps(body or {}).encode()
    req = urllib.request.Request(
        _API_BASE + path, data=data,
        headers=_headers(api_token), method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            body_resp = json.loads(raw)
            msgs = [err.get("message", "") for err in body_resp.get("errors", [])]
            msg = "; ".join(m for m in msgs if m) or raw
        except Exception:
            msg = raw
        raise RuntimeError(f"Cloudflare {e.code}: {msg}") from e
    except Exception as e:
        raise RuntimeError(str(e)) from e


def _delete(path: str, api_token: str) -> None:
    req = urllib.request.Request(
        _API_BASE + path, headers=_headers(api_token), method="DELETE",
    )
    with contextlib.suppress(Exception):
        urllib.request.urlopen(req, timeout=10)


def list_workers(api_token: str, account_id: str) -> list[str]:
    """Return sorted list of worker script IDs. Raises RuntimeError on failure."""
    data = _get(f"/accounts/{account_id}/workers/scripts", api_token)
    if not data.get("success"):
        errs = data.get("errors", [])
        msg = errs[0].get("message", "Unknown error") if errs else "Unknown error"
        raise RuntimeError(f"Failed to list workers: {msg}")
    return sorted(s["id"] for s in data.get("result", []) if s.get("id"))


def create_tail(api_token: str, account_id: str, script_name: str) -> dict:
    """Create a tail session. Returns dict with 'id', 'url' (wss://…), 'expires_at'."""
    data = _post(
        f"/accounts/{account_id}/workers/scripts/{script_name}/tails",
        api_token,
    )
    if not data.get("success"):
        errs = data.get("errors", [])
        msg = errs[0].get("message", "Unknown error") if errs else "Unknown error"
        raise RuntimeError(f"Failed to create tail: {msg}")
    return data["result"]


def delete_tail(api_token: str, account_id: str, script_name: str, tail_id: str) -> None:
    """Delete a tail session (cleanup on disconnect)."""
    _delete(
        f"/accounts/{account_id}/workers/scripts/{script_name}/tails/{tail_id}",
        api_token,
    )


# ── Minimal WebSocket client (no external deps) ──────────────────────────────

def _recv_exact(ssock: ssl.SSLSocket, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        chunk = ssock.recv(n - len(buf))
        if not chunk:
            raise EOFError("WebSocket connection closed")
        buf += chunk
    return buf


def ws_connect(ws_url: str, api_token: str, timeout: int = 30) -> ssl.SSLSocket:
    """Perform the WebSocket upgrade handshake and return the connected SSL socket."""
    parsed = urlparse(ws_url)
    host = parsed.hostname
    port = parsed.port or 443
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query

    key = base64.b64encode(os.urandom(16)).decode()
    ctx = ssl.create_default_context()
    raw = socket.create_connection((host, port), timeout=timeout)
    ssock = ctx.wrap_socket(raw, server_hostname=host)

    handshake = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        f"Authorization: Bearer {api_token}\r\n"
        "\r\n"
    ).encode()
    ssock.sendall(handshake)

    response = b""
    while b"\r\n\r\n" not in response:
        chunk = ssock.recv(4096)
        if not chunk:
            raise RuntimeError("Connection closed during WebSocket handshake")
        response += chunk

    first_line = response.split(b"\r\n")[0].decode("utf-8", errors="replace")
    if "101" not in first_line:
        raise RuntimeError(f"WebSocket upgrade failed: {first_line.strip()}")

    ssock.settimeout(35)  # > server ping interval
    return ssock


def ws_recv_frame(ssock: ssl.SSLSocket) -> tuple[int, bytes]:
    """Read one WebSocket frame. Returns (opcode, payload)."""
    header = _recv_exact(ssock, 2)
    opcode = header[0] & 0x0F
    masked = bool(header[1] & 0x80)
    length = header[1] & 0x7F

    if length == 126:
        length = struct.unpack(">H", _recv_exact(ssock, 2))[0]
    elif length == 127:
        length = struct.unpack(">Q", _recv_exact(ssock, 8))[0]

    mask = _recv_exact(ssock, 4) if masked else b""
    data = _recv_exact(ssock, length)

    if masked:
        data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))

    return opcode, data


def ws_send_frame(ssock: ssl.SSLSocket, opcode: int, payload: bytes = b"") -> None:
    """Send a masked WebSocket frame (client→server masking is required by RFC 6455)."""
    mask = os.urandom(4)
    n = len(payload)
    if n < 126:
        header = bytes([0x80 | opcode, 0x80 | n])
    elif n < 65536:
        header = bytes([0x80 | opcode, 0x80 | 126]) + struct.pack(">H", n)
    else:
        header = bytes([0x80 | opcode, 0x80 | 127]) + struct.pack(">Q", n)
    header += mask
    masked_payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    ssock.sendall(header + masked_payload)


def ws_close(ssock: ssl.SSLSocket) -> None:
    """Send a WebSocket close frame and shut down the socket."""
    with contextlib.suppress(Exception):
        ws_send_frame(ssock, 8)
    with contextlib.suppress(Exception):
        ssock.close()


def parse_tail_event(data: bytes) -> list[tuple[int, str]]:
    """Parse a Cloudflare Workers tail JSON payload into (ts_ms, message) tuples."""
    try:
        ev = json.loads(data.decode("utf-8", errors="replace"))
    except Exception:
        return []

    events: list[tuple[int, str]] = []
    ev_ts   = ev.get("eventTimestamp") or int(time.time() * 1000)
    script  = ev.get("scriptName", "worker")
    outcome = ev.get("outcome", "ok")

    # One summary line per invocation (request URL + outcome)
    event_data = ev.get("event") or {}
    req = event_data.get("request") or {} if isinstance(event_data, dict) else {}
    if req:
        method = req.get("method", "?")
        url    = req.get("url", "")
        cf     = req.get("cf") or {}
        colo   = cf.get("colo", "")
        status = "" if outcome == "ok" else f" [{outcome.upper()}]"
        line   = f"[{script}] {method} {url}{status}"
        if colo:
            line += f"  ({colo})"
        events.append((ev_ts, line))

    # console.log / warn / error / debug output
    for log in ev.get("logs") or []:
        ts   = log.get("timestamp") or ev_ts
        lvl  = (log.get("level") or "log").upper()
        msgs = log.get("message", [])
        text = " ".join(str(m) for m in msgs) if isinstance(msgs, list) else str(msgs)
        prefix = f"[{lvl}] " if lvl not in ("LOG", "") else ""
        events.append((ts, prefix + text))

    # Uncaught exceptions
    for exc in ev.get("exceptions") or []:
        ts   = exc.get("timestamp") or ev_ts
        name = exc.get("name", "Error")
        msg  = exc.get("message", "")
        events.append((ts, f"[EXCEPTION] {name}: {msg}"))

    return events
