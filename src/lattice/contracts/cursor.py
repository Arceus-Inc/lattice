"""Consolidation cursor — watermark per employee."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ConsolidationWatermark:
    """Where the last successful pass stopped for one agent."""

    employee_id: str
    last_run_id: str | None
    episodes_seen: int
    consolidated_at: datetime | None
