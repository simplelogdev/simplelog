"""railway_utils.py — Railway GraphQL API helpers for SimpleLog."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime

_GQL_URL = "https://backboard.railway.app/graphql/v2"


def _gql(query: str, token: str, variables: dict | None = None,
         timeout: int = 15) -> dict:
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req  = urllib.request.Request(_GQL_URL, data=body, method="POST",
                                   headers={"Content-Type": "application/json",
                                            "Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read())
        if "errors" in result:
            raise RuntimeError(result["errors"][0].get("message", str(result["errors"])))
        return result.get("data", {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            msg = json.loads(raw)["errors"][0]["message"]
        except Exception:
            msg = raw
        raise RuntimeError(f"Railway {e.code}: {msg}") from e
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(str(e)) from e


def verify_token(token: str) -> dict:
    """Verify token; returns {name, email}. Raises RuntimeError on failure."""
    data = _gql("{ me { name email } }", token)
    return data.get("me", {})


def list_projects(token: str) -> list[dict]:
    """Return [{id, name, services: [{id, name}]}]."""
    data = _gql("""
    {
      projects { edges { node {
        id name
        services { edges { node { id name } } }
      } } }
    }
    """, token)
    result = []
    for edge in data.get("projects", {}).get("edges", []):
        n = edge.get("node", {})
        services = [
            {"id": s["node"]["id"], "name": s["node"]["name"]}
            for s in n.get("services", {}).get("edges", [])
        ]
        result.append({"id": n.get("id", ""), "name": n.get("name", ""),
                        "services": services})
    return result


def get_latest_deployment(token: str, service_id: str) -> dict | None:
    """Return {id, status, createdAt} for latest deployment, or None."""
    data = _gql("""
    query($sid: String!) {
      deployments(serviceId: $sid, last: 1) {
        edges { node { id status createdAt } }
      }
    }
    """, token, {"sid": service_id})
    edges = data.get("deployments", {}).get("edges", [])
    if not edges:
        return None
    n = edges[0]["node"]
    return {"id": n.get("id"), "status": n.get("status", ""),
            "createdAt": n.get("createdAt", "")}


def fetch_deployment_logs(token: str, deployment_id: str) -> list[tuple[int, str]]:
    """Return (ts_ms, message) tuples for a deployment."""
    data = _gql("""
    query($did: String!) {
      deploymentLogs(deploymentId: $did) {
        message severity timestamp
      }
    }
    """, token, {"did": deployment_id})
    result: list[tuple[int, str]] = []
    for entry in data.get("deploymentLogs") or []:
        msg = entry.get("message", "")
        if not msg:
            continue
        ts_raw = entry.get("timestamp", "")
        ts_ms = 0
        if ts_raw:
            try:
                ts_ms = int(datetime.fromisoformat(
                    ts_raw.replace("Z", "+00:00")
                ).timestamp() * 1000)
            except Exception:
                ts_ms = 0
        result.append((ts_ms, msg.rstrip()))
    return result
