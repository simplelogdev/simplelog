"""gcp_utils.py — Google Cloud Logging helpers for SimpleLog."""
from __future__ import annotations

from datetime import datetime

# Common GCP resource types shown in the picker
RESOURCE_TYPES = [
    "(all)",
    "cloud_run_revision",
    "cloud_function",
    "k8s_container",
    "k8s_pod",
    "gce_instance",
    "app_engine",
    "cloud_sql_database",
    "gcs_bucket",
    "pubsub_topic",
    "bigquery_resource",
    "dataflow_step",
    "global",
]

SEVERITIES = ["ALL", "DEBUG", "INFO", "NOTICE", "WARNING", "ERROR", "CRITICAL", "ALERT", "EMERGENCY"]


# ── Client factory ─────────────────────────────────────────────────────────────

def make_client(project_id: str, key_path: str | None = None):
    """Return a google.cloud.logging.Client.

    Uses service account *key_path* if given, otherwise falls back to
    Application Default Credentials (ADC / gcloud auth).
    Raises RuntimeError on failure.
    """
    try:
        from google.cloud import logging as gcp_logging
        if key_path:
            from google.oauth2 import service_account
            creds = service_account.Credentials.from_service_account_file(
                key_path,
                scopes=[
                    "https://www.googleapis.com/auth/logging.read",
                    "https://www.googleapis.com/auth/cloud-platform.read-only",
                ],
            )
            return gcp_logging.Client(project=project_id, credentials=creds)
        return gcp_logging.Client(project=project_id)
    except Exception as e:
        raise RuntimeError(str(e)) from e


def list_projects(key_path: str | None = None) -> list[dict]:
    """Return accessible GCP projects as [{id, name}, ...].

    Raises RuntimeError on auth or API failure.
    """
    try:
        from google.cloud import resourcemanager_v3
        if key_path:
            from google.oauth2 import service_account
            creds = service_account.Credentials.from_service_account_file(
                key_path,
                scopes=["https://www.googleapis.com/auth/cloud-platform.read-only"],
            )
            rm = resourcemanager_v3.ProjectsClient(credentials=creds)
        else:
            rm = resourcemanager_v3.ProjectsClient()
        projects = []
        for p in rm.search_projects():
            projects.append({
                "id":   p.project_id,
                "name": p.display_name or p.project_id,
            })
        return sorted(projects, key=lambda x: x["name"].lower())
    except Exception as e:
        raise RuntimeError(str(e)) from e


# ── Filter builder ─────────────────────────────────────────────────────────────

def build_filter(
    resource_type: str = "",
    severity: str = "ALL",
    custom: str = "",
    since: datetime | None = None,
) -> str:
    """Compose a GCP log filter string from individual criteria."""
    parts: list[str] = []
    if resource_type and resource_type != "(all)":
        parts.append(f'resource.type="{resource_type}"')
    if severity and severity != "ALL":
        parts.append(f"severity>={severity}")
    if since:
        parts.append(f'timestamp>="{since.strftime("%Y-%m-%dT%H:%M:%SZ")}"')
    if custom.strip():
        parts.append(f"({custom.strip()})")
    return " AND ".join(parts)


# ── Log fetcher ────────────────────────────────────────────────────────────────

def _entry_to_text(entry) -> str:
    """Convert a log entry to a human-readable string."""
    sev = getattr(entry, "severity", None)
    sev_str = f"[{sev.name}] " if sev and hasattr(sev, "name") else ""
    res = getattr(entry, "resource", None)
    res_str = f"{res.type}: " if res and res.type else ""
    payload = entry.payload
    if isinstance(payload, str):
        msg = payload
    elif isinstance(payload, dict):
        msg = payload.get("message") or payload.get("msg") or str(payload)
    else:
        msg = str(payload)
    return f"{sev_str}{res_str}{msg}"


def fetch_entries(
    client,
    filter_str: str,
    max_results: int = 500,
) -> list[tuple[int, str]]:
    """Fetch log entries matching *filter_str*.

    Returns [(ts_ms, message), ...] in ascending timestamp order.
    """
    try:
        from google.cloud import logging as gcp_logging
        raw = list(client.list_entries(
            filter_=filter_str,
            order_by=gcp_logging.DESCENDING,
            max_results=max_results,
            page_size=min(max_results, 1000),
        ))
        result: list[tuple[int, str]] = []
        for entry in reversed(raw):
            ts = entry.timestamp
            ts_ms = int(ts.timestamp() * 1000) if ts else 0
            result.append((ts_ms, _entry_to_text(entry)))
        return result
    except Exception as e:
        raise RuntimeError(str(e)) from e
