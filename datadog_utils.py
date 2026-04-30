"""datadog_utils.py — Datadog Logs v2 REST API helpers for SimpleLog."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import UTC, datetime

DD_SITES: dict[str, str] = {
    "US1 (datadoghq.com)":     "https://api.datadoghq.com",
    "EU1 (datadoghq.eu)":      "https://api.datadoghq.eu",
    "US3 (us3.datadoghq.com)": "https://api.us3.datadoghq.com",
    "US5 (us5.datadoghq.com)": "https://api.us5.datadoghq.com",
    "AP1 (ap1.datadoghq.com)": "https://api.ap1.datadoghq.com",
}


def _post(base_url: str, path: str, body: dict,
          api_key: str, app_key: str, timeout: int = 15) -> dict:
    url  = base_url.rstrip("/") + path
    data = json.dumps(body).encode()
    req  = urllib.request.Request(
        url, data=data, method="POST",
        headers={
            "Content-Type":       "application/json",
            "DD-API-KEY":         api_key,
            "DD-APPLICATION-KEY": app_key,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_txt = e.read().decode("utf-8", errors="replace")
        try:
            msg = json.loads(body_txt).get("errors", [body_txt])[0]
        except Exception:
            msg = body_txt
        raise RuntimeError(f"Datadog {e.code}: {msg}") from e
    except Exception as e:
        raise RuntimeError(str(e)) from e


def verify_connection(base_url: str, api_key: str, app_key: str) -> None:
    """Probe Datadog with a minimal log search. Raises RuntimeError on failure."""
    _post(base_url, "/api/v2/logs/events/search", {
        "filter": {"from": "now-1m", "to": "now", "query": ""},
        "page":   {"limit": 1},
    }, api_key, app_key)


def fetch_logs(base_url: str, query: str, from_iso: str, to_iso: str,
               api_key: str, app_key: str,
               limit: int = 500) -> list[tuple[int, str]]:
    """Fetch log events between from_iso and to_iso.

    Returns list of (ts_ms, message) tuples sorted oldest-first.
    """
    data = _post(base_url, "/api/v2/logs/events/search", {
        "filter": {"query": query, "from": from_iso, "to": to_iso},
        "sort":   "timestamp",
        "page":   {"limit": limit},
    }, api_key, app_key)

    result: list[tuple[int, str]] = []
    for item in data.get("data", []):
        attrs = item.get("attributes", {})
        ts_raw = attrs.get("timestamp", "")
        svc    = attrs.get("service", "")
        status = attrs.get("status", "")
        msg    = attrs.get("message", "") or str(attrs)

        if svc and status:
            msg = f"[{status}] {svc}: {msg}"
        elif status:
            msg = f"[{status}] {msg}"

        ts_ms = 0
        if ts_raw:
            try:
                dt = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                ts_ms = int(dt.timestamp() * 1000)
            except Exception:
                ts_ms = 0

        result.append((ts_ms, msg.rstrip()))

    result.sort(key=lambda x: x[0])
    return result


def now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def offset_iso(hours: float) -> str:
    from datetime import timedelta
    dt = datetime.now(UTC) - timedelta(hours=hours)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
