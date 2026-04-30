"""loki_utils.py — Grafana Loki HTTP API helpers for SimpleLog."""
from __future__ import annotations

import base64
import json
import urllib.error
import urllib.parse
import urllib.request


def _request(base_url: str, path: str, params: dict,
             username: str, password: str, token: str,
             timeout: int = 10) -> dict:
    url = base_url.rstrip("/") + path
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    elif username:
        creds = base64.b64encode(f"{username}:{password}".encode()).decode()
        req.add_header("Authorization", f"Basic {creds}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            msg = json.loads(body).get("message", body)
        except Exception:
            msg = body
        raise RuntimeError(f"Loki {e.code}: {msg}") from e
    except Exception as e:
        raise RuntimeError(str(e)) from e


def verify_connection(base_url: str, username: str = "", password: str = "",
                      token: str = "") -> list[str]:
    """Probe Loki and return available label names. Raises RuntimeError on failure."""
    data = _request(base_url, "/loki/api/v1/labels", {}, username, password, token)
    return data.get("data", [])


def fetch_logs(base_url: str, query: str, start_ns: int, end_ns: int,
               username: str = "", password: str = "", token: str = "",
               limit: int = 500) -> list[tuple[int, str]]:
    """Fetch log entries from Loki for [start_ns, end_ns] (nanoseconds).

    Returns list of (ts_ms, message) tuples sorted oldest-first.
    """
    params = {
        "query":     query,
        "start":     str(start_ns),
        "end":       str(end_ns),
        "limit":     str(limit),
        "direction": "forward",
    }
    data = _request(base_url, "/loki/api/v1/query_range", params, username, password, token)
    result: list[tuple[int, str]] = []
    for stream in data.get("data", {}).get("result", []):
        for ts_ns_str, line in stream.get("values", []):
            result.append((int(ts_ns_str) // 1_000_000, line))
    result.sort(key=lambda x: x[0])
    return result
