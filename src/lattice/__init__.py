"""lattice — the consolidation SDK for chorus episodic memory."""

from __future__ import annotations

from lattice.domain import (
    ConsolidationResult,
    EpisodeBatch,
    MemoryOperation,
    ProceduralOutcome,
    SemanticOutcome,
)
from lattice.facade import Lattice

__all__ = [
    "ConsolidationResult",
    "EpisodeBatch",
    "Lattice",
    "MemoryOperation",
    "ProceduralOutcome",
    "SemanticOutcome",
]
