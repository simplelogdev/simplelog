"""kubernetes_utils.py — kubectl subprocess helpers for SimpleLog."""
from __future__ import annotations

import json
import shutil
import subprocess


def is_available() -> bool:
    """Return True if kubectl is in PATH."""
    return shutil.which("kubectl") is not None


def _run(args: list[str], timeout: int = 10) -> str:
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"kubectl exited {result.returncode}")
    return result.stdout


def list_contexts() -> list[str]:
    """Return available kubeconfig context names."""
    out = _run(["kubectl", "config", "get-contexts", "-o", "name"])
    return [c.strip() for c in out.splitlines() if c.strip()]


def current_context() -> str:
    """Return the current kubeconfig context name."""
    return _run(["kubectl", "config", "current-context"]).strip()


def list_namespaces(context: str = "") -> list[str]:
    """Return namespace names."""
    cmd = ["kubectl", "get", "namespaces", "-o", "jsonpath={.items[*].metadata.name}"]
    if context:
        cmd.extend(["--context", context])
    out = _run(cmd)
    return out.split()


def list_pods(namespace: str, context: str = "") -> list[dict]:
    """Return [{name, status, ready}] for pods in namespace."""
    cmd = ["kubectl", "get", "pods", "-n", namespace, "-o", "json"]
    if context:
        cmd.extend(["--context", context])
    data = json.loads(_run(cmd))
    result = []
    for item in data.get("items", []):
        name   = item["metadata"]["name"]
        phase  = (item.get("status") or {}).get("phase", "Unknown")
        result.append({"name": name, "status": phase})
    return result


def build_logs_cmd(pod: str, namespace: str, context: str = "",
                   container: str = "", tail: int = 200) -> list[str]:
    """Return the kubectl logs -f command for streaming."""
    cmd = ["kubectl", "logs", "-f", pod, "-n", namespace, f"--tail={tail}"]
    if context:
        cmd.extend(["--context", context])
    if container:
        cmd.extend(["-c", container])
    return cmd
