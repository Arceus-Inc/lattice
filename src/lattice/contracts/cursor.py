"""Consolidation cursor — watermark per employee."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class ConsolidationWatermark:
    """Where the last successful pass stopped for one agent."""

    employee_id: str
    last_run_id: str | None
    episodes_seen: int
    consolidated_at: datetime | None


@runtime_checkable
class ConsolidationCursor(Protocol):
    """Tracks consolidation progress per employee."""

    def get(self, employee_id: str) -> ConsolidationWatermark: ...

    def advance(self, employee_id: str, *, last_run_id: str, episodes_seen: int) -> None: ...
