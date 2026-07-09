"""Semantic atom port — flat key/value facts with provenance."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable


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


@runtime_checkable
class AtomStore(Protocol):
    """Push-channel semantic memory — atoms are source of truth; MEMORY.md is a view."""

    def list_active(self, employee_id: str) -> tuple[Atom, ...]:
        """Active atoms for one agent, newest first."""
        ...

    def get_active(self, employee_id: str, key: str) -> Atom | None:
        """Active atom at key, if any."""
        ...

    def write(self, atom: Atom) -> None:
        """Persist one atom."""
        ...

    def invalidate(self, employee_id: str, key: str, *, at: datetime) -> None:
        """Mark the active atom at key invalid."""
        ...
