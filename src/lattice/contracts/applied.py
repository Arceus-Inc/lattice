"""Exact atom-revision APPLIED outcome edges."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Protocol


class LandedOutcomePhase(StrEnum):
    """Closed APPLIED outcome phases, kept independent from Dream's seam package."""

    CANCELLED = "cancelled"
    DELEGATED = "delegated"
    TERMINAL_PASS = "terminal_pass"
    TERMINAL_FAIL = "terminal_fail"
    NEEDS_REWORK = "needs_rework"
    STRANDED = "stranded"


@dataclass(frozen=True)
class AppliedAtomEdge:
    """One beat's outcome for one exact, retrieved Postgres atom revision."""

    employee_id: str
    key: str
    revision: int
    beat_run_id: str
    outcome_phase: LandedOutcomePhase
    landed_at: datetime

    def __post_init__(self) -> None:
        if self.revision < 1:
            raise ValueError("revision must be positive")
        if self.landed_at.tzinfo is None or self.landed_at.utcoffset() != timedelta(0):
            raise ValueError("landed_at must be timezone-aware UTC")


class AppliedEdgeConflictError(RuntimeError):
    """An APPLIED edge replay disagrees with its already-recorded outcome."""


class AppliedEdgeStore(Protocol):
    """Postgres-only persistence port for immutable atom outcome edges."""

    def record(self, edge: AppliedAtomEdge) -> None: ...

    def record_all(self, edges: tuple[AppliedAtomEdge, ...]) -> tuple[AppliedAtomEdge, ...]:
        """Persist one beat's complete selected set atomically and idempotently."""
        ...

    def list_for_run(self, employee_id: str, beat_run_id: str) -> tuple[AppliedAtomEdge, ...]: ...
