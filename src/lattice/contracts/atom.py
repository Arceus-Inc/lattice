"""Semantic atom port — flat key/value facts with provenance."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from lattice.domain.stats import PatternStats


@dataclass(frozen=True)
class Atom:
    """One durable semantic fact promoted from episodic traces."""

    key: str
    value: str
    employee_id: str
    source_run_ids: tuple[str, ...]
    created_at: datetime
    invalid_at: datetime | None = None
    activation: float = 1.0
    stats: PatternStats | None = None
    key_files: tuple[str, ...] = ()


@dataclass(frozen=True)
class ContextAtomHit:
    """One retrieved atom and its exact persisted revision when available."""

    employee_id: str
    key: str
    revision: int | None
    atom: Atom

    def __post_init__(self) -> None:
        if (self.employee_id, self.key) != (self.atom.employee_id, self.atom.key):
            raise ValueError("context hit identity must match its atom")
        if self.revision is not None and self.revision < 1:
            raise ValueError("context hit revision must be positive")


class AtomStore(Protocol):
    """Persistence port for durable semantic atoms."""

    def list_active(self, employee_id: str) -> tuple[Atom, ...]: ...

    def write(self, atom: Atom) -> None: ...

    def invalidate(self, employee_id: str, key: str, *, at: datetime) -> None: ...


class AtomHitReader(Protocol):
    """Optional revision-aware retrieval port for authoritative atom stores."""

    def list_active_hits(self, employee_id: str) -> tuple[ContextAtomHit, ...]: ...
