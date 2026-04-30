"""vercel_utils.py — Vercel REST API helpers for SimpleLog."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

_BASE = "https://api.vercel.com"
_CONFIG_PATH = Path.home() / ".config" / "simplelog" / "vercel_config.json"


# ── Token persistence ──────────────────────────────────────────────────────────

def load_token() -> str:
    try:
        return json.loads(_CONFIG_PATH.read_text()).get("token", "")
    except (OSError, json.JSONDecodeError):
        return ""


def save_token(token: str) -> None:
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_PATH.write_text(json.dumps({"token": token}))


# ── HTTP helper ────────────────────────────────────────────────────────────────

def _get(path: str, token: str, params: dict | None = None, timeout: int = 10) -> dict | list:
    url = _BASE + path
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{qs}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            msg = json.loads(body).get("error", {}).get("message", body)
        except Exception:
            msg = body
        raise RuntimeError(f"Vercel API error {e.code}: {msg}") from e
    except Exception as e:
        raise RuntimeError(str(e)) from e


# ── Public API ─────────────────────────────────────────────────────────────────

def verify_token(token: str) -> dict:
    """Verify token and return user info dict. Raises RuntimeError on failure."""
    return _get("/v2/user", token)


def list_projects(token: str) -> list[dict]:
    """Return list of projects. Each dict has: id, name, framework, updatedAt."""
    data = _get("/v9/projects", token, params={"limit": "100"})
    projects = data if isinstance(data, list) else data.get("projects", [])
    return [
        {
            "id":         p.get("id", ""),
            "name":       p.get("name", ""),
            "framework":  p.get("framework") or "",
            "updatedAt":  p.get("updatedAt", 0),
        }
        for p in projects
        if p.get("name")
    ]


def get_latest_deployment(token: str, project_id: str, target: str = "production") -> dict | None:
    """Return the latest deployment dict for *project_id*, or None if none found.

    Dict has: id, url, state, createdAt.
    """
    params: dict = {"projectId": project_id, "limit": "5"}
    if target != "any":
        params["target"] = target
    data = _get("/v6/deployments", token, params=params)
    deployments = data if isinstance(data, list) else data.get("deployments", [])
    if not deployments:
        if target != "any":
            return get_latest_deployment(token, project_id, "any")
        return None
    d = deployments[0]
    return {
        "id":        d.get("uid") or d.get("id", ""),
        "url":       d.get("url", ""),
        "state":     d.get("state", ""),
        "createdAt": d.get("createdAt", 0),
    }


def fetch_deployment_events(token: str, deployment_id: str, since_ms: int = 0) -> list[tuple[int, str]]:
    """Fetch log events for *deployment_id* since *since_ms*.

    Returns list of (ts_ms, message) tuples.
    """
    params: dict = {"limit": "500"}
    if since_ms:
        params["since"] = str(since_ms)
    data = _get(f"/v2/deployments/{deployment_id}/events", token, params=params)
    events_raw = data if isinstance(data, list) else data.get("events", []) if isinstance(data, dict) else []

    result: list[tuple[int, str]] = []
    for ev in events_raw:
        if not isinstance(ev, dict):
            continue
        payload = ev.get("payload", {}) or {}
        text = payload.get("text", "") or ev.get("text", "") or ""
        ts = payload.get("date") or ev.get("date") or ev.get("createdAt") or 0
        if isinstance(ts, str):
            try:
                from datetime import datetime
                ts = int(datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp() * 1000)
            except Exception:
                ts = 0
        if text:
            result.append((int(ts), text.rstrip()))
    return result
