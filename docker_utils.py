"""docker_utils.py — Docker CLI query helpers for SimpleLog."""
from __future__ import annotations

import json
import shutil
import subprocess


def is_docker_available() -> bool:
    """Return True if the docker CLI is available in PATH."""
    return shutil.which("docker") is not None


def _run(args: list[str], timeout: int = 10) -> str:
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"docker exited {result.returncode}")
    return result.stdout


def _extract_label(labels_str: str, key: str) -> str:
    """Parse 'key=val,key2=val2' label string from docker ps output."""
    for part in labels_str.split(","):
        if "=" in part:
            k, _, v = part.partition("=")
            if k.strip() == key:
                return v.strip()
    return ""


def list_containers() -> list[dict]:
    """Return running containers as a list of dicts.

    Each dict has: id, name, image, status, compose_project, compose_service.
    Raises RuntimeError if docker CLI fails.
    """
    raw = _run(["docker", "ps", "--no-trunc", "--format", "{{json .}}"])
    containers = []
    for line in raw.strip().splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
            labels = obj.get("Labels", "") or ""
            containers.append({
                "id":              obj.get("ID", "")[:12],
                "name":            obj.get("Names", "").lstrip("/"),
                "image":           obj.get("Image", ""),
                "status":          obj.get("Status", ""),
                "compose_project": _extract_label(labels, "com.docker.compose.project"),
                "compose_service": _extract_label(labels, "com.docker.compose.service"),
            })
        except (json.JSONDecodeError, KeyError):
            continue
    return containers


def list_compose_stacks() -> list[dict]:
    """Return running Compose projects as a list of dicts.

    Each dict has: name, status, config_files.
    Requires docker compose v2 plugin. Raises RuntimeError if unavailable.
    """
    try:
        raw = _run(["docker", "compose", "ls", "--format", "json"])
    except RuntimeError:
        return []
    try:
        stacks = json.loads(raw.strip() or "[]")
    except json.JSONDecodeError:
        return []
    return [
        {
            "name":         s.get("Name", ""),
            "status":       s.get("Status", ""),
            "config_files": s.get("ConfigFiles", ""),
        }
        for s in stacks
        if s.get("Name") and "running" in s.get("Status", "").lower()
    ]
