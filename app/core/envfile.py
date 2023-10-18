"""Minimal, safe ``.env`` read/merge helpers.

Used by the "easy connect" provider UI so a user can save a provider
configuration without hand-editing files. Design goals:

* preserve unrelated lines and comments;
* only ever write ``KEY=VALUE`` for validated variable names;
* never log or echo secret values;
* refuse to touch anything that is not a plain ``.env`` file.
"""

from __future__ import annotations

import re
from pathlib import Path

ENV_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


def read_env_file(path: Path) -> dict[str, str]:
    """Parse a ``.env`` file into a mapping (values only, no quotes)."""
    path = Path(path)
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        if key.startswith("export "):
            key = key[len("export ") :].strip()
        values[key] = value.strip().strip('"').strip("'")
    return values


def update_env_file(path: Path, updates: dict[str, str]) -> list[str]:
    """Merge ``updates`` into ``path``, returning the keys written.

    Existing keys are replaced in place; new keys are appended. Comments and
    unrelated keys are preserved. Raises ``ValueError`` for an invalid key name.
    """
    for key in updates:
        if not ENV_NAME_RE.match(key):
            raise ValueError(f"invalid environment variable name: {key!r}")

    path = Path(path)
    lines: list[str] = []
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()

    remaining = dict(updates)
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        candidate = stripped[len("export ") :] if stripped.startswith("export ") else stripped
        key = candidate.split("=", 1)[0].strip() if "=" in candidate else ""
        if key and key in remaining and not stripped.startswith("#"):
            out.append(f"{key}={remaining.pop(key)}")
        else:
            out.append(line)
    for key, value in remaining.items():
        out.append(f"{key}={value}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out).rstrip("\n") + "\n", encoding="utf-8")
    return list(updates)


def mask_secret(value: str) -> str:
    """Return a non-reversible display form of a secret for the UI."""
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}…{value[-2:]} ({len(value)} chars)"
