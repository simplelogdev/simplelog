"""azure_utils.py — Azure Monitor Logs helpers for SimpleLog."""
from __future__ import annotations

from datetime import datetime, timedelta

# Common Log Analytics tables grouped by category
TABLES: dict[str, list[str]] = {
    "Application": [
        "AppTraces",
        "AppExceptions",
        "AppRequests",
        "AppDependencies",
        "AppEvents",
        "AppPageViews",
        "AppBrowserTimings",
        "AppPerformanceCounters",
    ],
    "Container / Kubernetes": [
        "ContainerLog",
        "ContainerLogV2",
        "KubePodInventory",
        "KubeNodeInventory",
        "KubeEvents",
        "KubeServices",
        "ContainerInventory",
    ],
    "Security": [
        "SecurityEvent",
        "SigninLogs",
        "AuditLogs",
        "AADNonInteractiveUserSignInLogs",
        "AzureActivity",
        "DeviceEvents",
        "OfficeActivity",
    ],
    "Infrastructure": [
        "Heartbeat",
        "Perf",
        "Event",
        "Syslog",
        "AzureDiagnostics",
        "AzureMetrics",
        "VMConnection",
        "InsightsMetrics",
    ],
    "Network": [
        "AzureNetworkAnalytics_CL",
        "NetworkMonitoring",
        "DnsEvents",
        "WireData",
    ],
}

# Columns that are candidates for the "message" content per table
_MESSAGE_COLS = ["Message", "RawData", "ResultDescription", "SeverityText",
                 "Properties", "Details", "OperationName", "ActivityStatusValue"]


# ── Credential / client factories ──────────────────────────────────────────────

def make_credential(tenant_id: str, client_id: str, client_secret: str):
    """Return a ClientSecretCredential. Raises RuntimeError on failure."""
    try:
        from azure.identity import ClientSecretCredential
        return ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
        )
    except Exception as e:
        raise RuntimeError(str(e)) from e


def make_logs_client(credential):
    """Return an Azure LogsQueryClient."""
    try:
        from azure.monitor.query import LogsQueryClient
        return LogsQueryClient(credential)
    except Exception as e:
        raise RuntimeError(str(e)) from e


def verify_credential(credential, workspace_id: str) -> None:
    """Run a cheap query to verify the credential + workspace.

    Raises RuntimeError if the query fails.
    """
    client = make_logs_client(credential)
    _run_query(client, workspace_id, "Heartbeat | limit 1", timedelta(hours=1))


# ── Query helpers ──────────────────────────────────────────────────────────────

def build_table_query(table: str, since_dt: datetime | None = None, limit: int = 500) -> str:
    """Build a KQL query for *table* optionally filtered from *since_dt*."""
    if since_dt:
        ts = since_dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        return (
            f"{table}\n"
            f"| where TimeGenerated > datetime({ts})\n"
            f"| order by TimeGenerated asc\n"
            f"| limit {limit}"
        )
    return (
        f"{table}\n"
        f"| where TimeGenerated > ago(1h)\n"
        f"| order by TimeGenerated asc\n"
        f"| limit {limit}"
    )


def _run_query(client, workspace_id: str, query: str, timespan) -> list[tuple[int, str]]:
    """Execute a KQL query and return [(ts_ms, message), ...].

    Raises RuntimeError on failure.
    """
    from azure.monitor.query import LogsQueryStatus
    try:
        resp = client.query_workspace(
            workspace_id=workspace_id,
            query=query,
            timespan=timespan,
        )
    except Exception as e:
        raise RuntimeError(str(e)) from e

    if resp.status == LogsQueryStatus.PARTIAL:
        tables = resp.partial_data
    elif resp.status == LogsQueryStatus.SUCCESS:
        tables = resp.tables
    else:
        raise RuntimeError(f"Azure query failed: {getattr(resp, 'partial_error', 'unknown')}")

    if not tables:
        return []

    table = tables[0]
    col_names = [c.name for c in table.columns]
    result: list[tuple[int, str]] = []

    # Find timestamp column
    ts_col = next((i for i, c in enumerate(col_names)
                   if c.lower() in ("timegenerated", "timestamp", "time")), None)

    # Find best message column
    msg_col = None
    for candidate in _MESSAGE_COLS:
        idx = next((i for i, c in enumerate(col_names)
                    if c.lower() == candidate.lower()), None)
        if idx is not None:
            msg_col = idx
            break

    for row in table.rows:
        # Timestamp
        ts_ms = 0
        if ts_col is not None:
            val = row[ts_col]
            if isinstance(val, datetime):
                ts_ms = int(val.timestamp() * 1000)
            elif isinstance(val, str):
                try:
                    dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
                    ts_ms = int(dt.timestamp() * 1000)
                except ValueError:
                    pass

        # Message
        if msg_col is not None:
            msg = str(row[msg_col] or "")
        else:
            pairs = [f"{col_names[i]}={row[i]}" for i in range(len(col_names))
                     if col_names[i].lower() not in ("timegenerated", "tenantid", "_resourceid")]
            msg = "  ".join(pairs[:8])

        if msg:
            result.append((ts_ms, msg))

    return result


def fetch_logs(
    client,
    workspace_id: str,
    query: str,
    timespan_hours: float = 1.0,
) -> list[tuple[int, str]]:
    """Fetch logs using *query* over the last *timespan_hours*.

    Returns [(ts_ms, message), ...].
    """
    return _run_query(client, workspace_id, query, timedelta(hours=timespan_hours))


def fetch_logs_since(
    client,
    workspace_id: str,
    query: str,
    since_dt: datetime,
) -> list[tuple[int, str]]:
    """Fetch new logs since *since_dt* by injecting a TimeGenerated filter.

    If the query already contains 'where TimeGenerated', we replace it;
    otherwise we inject a new where clause after the table name.
    """
    ts = since_dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    filter_clause = f"| where TimeGenerated > datetime({ts})"

    lines = query.strip().splitlines()
    injected = False
    new_lines = []
    for line in lines:
        stripped = line.strip().lower()
        if stripped.startswith("| where timegenerated"):
            new_lines.append(filter_clause)
            injected = True
        else:
            new_lines.append(line)

    if not injected and lines:
        new_lines.insert(1, filter_clause)

    merged = "\n".join(new_lines)
    # Use a wide timespan so Azure doesn't reject the query
    return _run_query(client, workspace_id, merged, timedelta(hours=24))
