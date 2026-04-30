"""profiles_store.py — Named credential profiles for SimpleLog panels."""
from __future__ import annotations

import json
from pathlib import Path

_DIR = Path.home() / ".config" / "simplelog"


def load_all(service: str) -> list[dict]:
    """Return all saved profiles for *service*, newest first."""
    try:
        return json.loads((_DIR / f"profiles_{service}.json").read_text())
    except (OSError, json.JSONDecodeError):
        return []


def save_all(service: str, profiles: list[dict]) -> None:
    _DIR.mkdir(parents=True, exist_ok=True)
    (_DIR / f"profiles_{service}.json").write_text(json.dumps(profiles, indent=2))


def upsert(service: str, name: str, data: dict) -> None:
    """Add or update a profile named *name* with *data*."""
    profiles = load_all(service)
    for i, p in enumerate(profiles):
        if p.get("name") == name:
            profiles[i] = {"name": name, **{k: v for k, v in data.items() if k != "name"}}
            save_all(service, profiles)
            return
    profiles.insert(0, {"name": name, **{k: v for k, v in data.items() if k != "name"}})
    save_all(service, profiles)


def delete(service: str, name: str) -> None:
    """Delete the profile named *name*."""
    save_all(service, [p for p in load_all(service) if p.get("name") != name])
