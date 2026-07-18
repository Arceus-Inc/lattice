"""Semantic atom port — flat key/value facts with provenance."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

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
