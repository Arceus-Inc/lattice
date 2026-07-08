"""Pure domain types."""

from __future__ import annotations

from lattice.contracts.episodic import EpisodeBatch
from lattice.domain.operation import (
    MemoryOperation,
    MemoryOperationKind,
    PromotionVerdict,
    PromotionVerdictKind,
)
from lattice.domain.result import ConsolidationResult, ProceduralOutcome, SemanticOutcome

__all__ = [
    "ConsolidationResult",
    "EpisodeBatch",
    "MemoryOperation",
    "MemoryOperationKind",
    "ProceduralOutcome",
    "PromotionVerdict",
    "PromotionVerdictKind",
    "SemanticOutcome",
]
