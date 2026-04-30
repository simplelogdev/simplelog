"""elastic_utils.py — Elasticsearch / OpenSearch REST API helpers for SimpleLog."""
from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from datetime import datetime


def _request(base_url: str, path: str, body: dict | None = None,
             api_key: str = "", username: str = "", password: str = "",
             timeout: int = 15) -> dict | list:
    url  = base_url.rstrip("/") + path
    data = json.dumps(body).encode() if body is not None else None
    req  = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    req.add_header("Content-Type", "application/json")
    if api_key:
        req.add_header("Authorization", f"ApiKey {api_key}")
    elif username:
        creds = base64.b64encode(f"{username}:{password}".encode()).decode()
        req.add_header("Authorization", f"Basic {creds}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            err = json.loads(raw)
            msg = (err.get("error", {}) or {}).get("reason") or err.get("message", raw)
        except Exception:
            msg = raw
        raise RuntimeError(f"Elasticsearch {e.code}: {msg}") from e
    except Exception as e:
        raise RuntimeError(str(e)) from e


def verify_connection(base_url: str, api_key: str = "",
                      username: str = "", password: str = "") -> dict:
    """GET / — returns cluster info dict. Raises RuntimeError on failure."""
    return _request(base_url, "/", api_key=api_key, username=username, password=password)


def list_indices(base_url: str, api_key: str = "",
                 username: str = "", password: str = "") -> list[str]:
    """Return non-system index names sorted alphabetically."""
    data = _request(base_url, "/_cat/indices?format=json&h=index",
                    api_key=api_key, username=username, password=password)
    if not isinstance(data, list):
        return []
    return sorted(item["index"] for item in data if not item.get("index", "").startswith("."))


def fetch_logs(base_url: str, index: str, query: str,
               since_iso: str = "", search_after: list | None = None,
               api_key: str = "", username: str = "", password: str = "",
               ts_field: str = "@timestamp", size: int = 500,
               ) -> tuple[list[tuple[int, str]], list]:
    """Search logs in index. Returns (events, last_sort_values) for search_after pagination."""
    must: list = [{"query_string": {"query": query or "*"}}]
    if since_iso:
        must.append({"range": {ts_field: {"gt": since_iso}}})

    body: dict = {
        "size": size,
        "sort": [{ts_field: {"order": "asc"}}, {"_id": "asc"}],
        "query": {"bool": {"must": must}},
    }
    if search_after:
        body["search_after"] = search_after

    data = _request(base_url, f"/{index}/_search", body,
                    api_key=api_key, username=username, password=password)
    hits = data.get("hits", {}).get("hits", [])
    result: list[tuple[int, str]] = []
    last_sort: list = []
    for hit in hits:
        src = hit.get("_source", {})
        ts_raw = src.get(ts_field) or src.get("timestamp") or src.get("time") or ""
        msg = (src.get("message") or src.get("log") or src.get("msg")
               or src.get("text") or json.dumps(src))
        ts_ms = 0
        if ts_raw:
            try:
                ts_ms = int(datetime.fromisoformat(
                    str(ts_raw).replace("Z", "+00:00")
                ).timestamp() * 1000)
            except Exception:
                ts_ms = 0
        result.append((ts_ms, str(msg).rstrip()))
        last_sort = hit.get("sort", [])
    return result, last_sort
