"""lattice — the consolidation SDK for chorus episodic memory."""

from __future__ import annotations

from lattice.domain import (
    ApplyResult,
    HabitAction,
    HabitDraft,
    HintKind,
    Packet,
    PatternDraft,
    Proposal,
    ValidationResult,
)
from lattice.facade import Lattice
from lattice.reflection import (
    FailureCategory,
    ReflectionCluster,
    TrajectoryEvidence,
    cluster_reflection_evidence,
)

__all__ = [
    "ApplyResult",
    "FailureCategory",
    "HabitAction",
    "HabitDraft",
    "HintKind",
    "Lattice",
    "Packet",
    "PatternDraft",
    "Proposal",
    "ReflectionCluster",
    "TrajectoryEvidence",
    "ValidationResult",
    "cluster_reflection_evidence",
]
