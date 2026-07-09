"""Episodic read port — the consolidation substrate chorus captures."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class RawEpisode:
    """One append-only episodic record (spec 07 §3). lattice reads; chorus writes."""

    run_id: str
    task_id: str
    employee_id: str
    role: str
    scope: str
    intent: str
    outcome: str
    score: float
    created_at: datetime
    recorded_at: datetime | None
    artifacts: tuple[str, ...]
    files_touched: tuple[str, ...]
    body: str


@runtime_checkable
class EpisodicReader(Protocol):
    """Read-only access to chorus's raw episodic stream."""

    def records_for(self, employee_id: str) -> tuple[RawEpisode, ...]:
        """Every episode for one agent, newest first."""
        ...

    def count_for(self, employee_id: str) -> int:
        """Episode count for one agent."""
        ...
