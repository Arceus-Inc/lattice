"""Semantic consolidation ports — P0 facts and MEMORY.md storage."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Protocol, runtime_checkable

from lattice.contracts.episodic import EpisodeBatch
from lattice.domain.operation import MemoryOperation


class SemanticKind(StrEnum):
    """Taxonomy of a distilled semantic atom."""

    FACT = "fact"
    PREFERENCE = "preference"
    PROJECT_STATE = "project_state"
    CALIBRATION = "calibration"


@dataclass(frozen=True)
class SemanticAtom:
    """A durable semantic claim promoted from episodic traces."""

    id: str
    employee_id: str
    kind: SemanticKind
    claim: str
    source_run_ids: tuple[str, ...]
    confidence: float
    files_touched: tuple[str, ...] = ()
    created_at: datetime | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@runtime_checkable
class SemanticStore(Protocol):
    """Push-channel semantic memory — MEMORY.md + atom backing."""

    def list_for(self, employee_id: str) -> tuple[SemanticAtom, ...]:
        """Distilled atoms for one agent, newest first."""
        ...

    def apply(self, operation: MemoryOperation) -> SemanticAtom | None:
        """Apply one auditable operation; returns the resulting atom when applicable."""
        ...


@runtime_checkable
class SemanticExtractor(Protocol):
    """Extract semantic candidates from a ranked episode batch."""

    def extract(self, batch: EpisodeBatch) -> tuple[SemanticAtom, ...]: ...


@runtime_checkable
class SemanticReconciler(Protocol):
    """Reconcile candidates against existing semantic memory."""

    def reconcile(
        self,
        candidates: tuple[SemanticAtom, ...],
        existing: tuple[SemanticAtom, ...],
    ) -> tuple[MemoryOperation, ...]: ...
