"""creds_store.py — Simple credential persistence for SimpleLog panels."""
from __future__ import annotations

import json
from pathlib import Path

_DIR = Path.home() / ".config" / "simplelog"


def load(name: str) -> dict:
    """Load saved credentials for *name*. Returns {} if none saved."""
    try:
        return json.loads((_DIR / f"creds_{name}.json").read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def save(name: str, data: dict) -> None:
    """Persist *data* as credentials for *name*."""
    _DIR.mkdir(parents=True, exist_ok=True)
    (_DIR / f"creds_{name}.json").write_text(json.dumps(data, indent=2))


def clear(name: str) -> None:
    """Delete saved credentials for *name* (no-op if absent)."""
    try:
        (_DIR / f"creds_{name}.json").unlink()
    except OSError:
        pass


def exists(name: str) -> bool:
    return (_DIR / f"creds_{name}.json").exists()
