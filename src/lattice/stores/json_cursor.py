"""Consolidation cursor — JSON watermark per employee."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from lattice.contracts.cursor import ConsolidationWatermark


class JsonCursorStore:
    """Persists consolidation watermarks at ``<root>/.cursor.json``."""

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    def get(self, employee_id: str) -> ConsolidationWatermark:
        payload = self._load()
        entry = payload.get(employee_id, {})
        consolidated_raw = entry.get("consolidated_at")
        consolidated_at = (
            datetime.fromisoformat(str(consolidated_raw)) if consolidated_raw else None
        )
        last_run_id = entry.get("last_run_id")
        return ConsolidationWatermark(
            employee_id=employee_id,
            last_run_id=str(last_run_id) if last_run_id is not None else None,
            episodes_seen=int(entry.get("episodes_seen", 0)),
            consolidated_at=consolidated_at,
        )

    def advance(self, employee_id: str, *, last_run_id: str, episodes_seen: int) -> None:
        payload = self._load()
        payload[employee_id] = {
            "last_run_id": last_run_id,
            "episodes_seen": episodes_seen,
            "consolidated_at": datetime.now(UTC).isoformat(),
        }
        self._path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @property
    def _path(self) -> Path:
        return self._root / ".cursor.json"

    def _load(self) -> dict[str, dict[str, Any]]:
        if not self._path.exists():
            return {}
        return cast(dict[str, dict[str, Any]], json.loads(self._path.read_text(encoding="utf-8")))
