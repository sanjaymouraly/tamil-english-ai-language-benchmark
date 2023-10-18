"""Dataset registry: versioned releases with content hashes."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.schemas import BenchmarkExample
from app.datasets.loader import dataset_content_hash


@dataclass
class DatasetVersion:
    name: str
    version: str
    content_hash: str
    example_count: int
    created_at: str
    notes: str = ""


class DatasetRegistry:
    """Track versioned benchmark releases on disk."""

    def __init__(self, registry_dir: Path) -> None:
        self.dir = Path(registry_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self.dir / "index.json"

    def _load_index(self) -> list[dict[str, Any]]:
        if self._index_path.exists():
            data = json.loads(self._index_path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return [e for e in data if isinstance(e, dict)]
            return []
        return []

    def _save_index(self, entries: list[dict[str, Any]]) -> None:
        self._index_path.write_text(
            json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def register(
        self, name: str, version: str, examples: list[BenchmarkExample], notes: str = ""
    ) -> DatasetVersion:
        entry = DatasetVersion(
            name=name,
            version=version,
            content_hash=dataset_content_hash(examples),
            example_count=len(examples),
            created_at=datetime.now(UTC).isoformat(),
            notes=notes,
        )
        entries = self._load_index()
        # Idempotent: re-registering the same (name, version) replaces the
        # previous entry instead of appending a duplicate, so repeated builds
        # do not grow the registry without bound.
        entries = [
            e for e in entries if not (e.get("name") == name and e.get("version") == version)
        ]
        entries.append(asdict(entry))
        self._save_index(entries)
        return entry

    def list_versions(self) -> list[DatasetVersion]:
        return [DatasetVersion(**e) for e in self._load_index()]

    def latest(self, name: str = "TEB") -> DatasetVersion | None:
        versions = [v for v in self.list_versions() if v.name == name]
        return versions[-1] if versions else None
