"""flyio_utils.py — Fly.io REST + SSE API helpers for SimpleLog."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from datetime import datetime

_API_BASE = "https://api.fly.io/v1"


def _get(path: str, token: str, timeout: int = 15) -> dict | list:
    url = _API_BASE + path
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            msg = json.loads(raw).get("error", raw)
        except Exception:
            msg = raw
        raise RuntimeError(f"Fly.io {e.code}: {msg}") from e
    except Exception as e:
        raise RuntimeError(str(e)) from e


def list_apps(token: str) -> list[dict]:
    """Return [{id, name, status}] for all apps. Raises RuntimeError on failure."""
    data = _get("/apps", token)
    apps = data if isinstance(data, list) else data.get("apps", [])
    return [{"id": a.get("id", ""), "name": a.get("name", ""),
             "status": a.get("status", "")}
            for a in apps if a.get("name")]


def fetch_logs_sse(token: str, app_name: str,
                   limit: int = 300, timeout: int = 20) -> list[tuple[int, str]]:
    """Read Fly.io SSE log stream and return up to limit (ts_ms, message) tuples."""
    url = f"{_API_BASE}/apps/{app_name}/logs"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept":        "text/event-stream",
    })
    result: list[tuple[int, str]] = []
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8", errors="replace").rstrip("\n\r")
                if not line.startswith("data: "):
                    continue
                payload = line[6:]
                if payload in ("", "ping"):
                    continue
                try:
                    ev = json.loads(payload)
                    msg    = ev.get("message", "")
                    ts_raw = ev.get("timestamp", "")
                    region = ev.get("region", "")
                    level  = ev.get("level", "")
                    if not msg:
                        continue
                    if region:
                        msg = f"[{region}] {msg}"
                    if level and level not in ("info", ""):
                        msg = f"[{level}] {msg}"
                    ts_ms = 0
                    if ts_raw:
                        try:
                            ts_ms = int(datetime.fromisoformat(
                                ts_raw.replace("Z", "+00:00")
                            ).timestamp() * 1000)
                        except Exception:
                            ts_ms = int(time.time() * 1000)
                    result.append((ts_ms, msg.rstrip()))
                    if len(result) >= limit:
                        break
                except json.JSONDecodeError:
                    continue
    except (TimeoutError, OSError, urllib.error.URLError):
        pass
    except Exception as e:
        if result:
            return result
        raise RuntimeError(str(e)) from e
    return result
