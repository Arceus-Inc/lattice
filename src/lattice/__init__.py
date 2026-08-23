"""lattice — the consolidation SDK for chorus episodic memory."""

from __future__ import annotations

from lattice.domain import (
    AppliedContextResult,
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
    ApplicationAuthorization,
    FailureCategory,
    ReflectionCluster,
    ReflectionDiff,
    ReflectionProposal,
    ReflectionReview,
    ReflectionRunRef,
    ReflectionTargetKind,
    ReplayOutcome,
    ReplayResult,
    ReplaySeverity,
    RepresentativeSuccessEvidence,
    ReviewDecision,
    TrajectoryEvidence,
    cluster_reflection_evidence,
)

__all__ = [
    "AppliedContextResult",
    "ApplicationAuthorization",
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
    "ReflectionDiff",
    "ReflectionProposal",
    "ReflectionReview",
    "ReflectionRunRef",
    "ReflectionTargetKind",
    "ReplayOutcome",
    "ReplayResult",
    "ReplaySeverity",
    "RepresentativeSuccessEvidence",
    "ReviewDecision",
    "TrajectoryEvidence",
    "ValidationResult",
    "cluster_reflection_evidence",
]
