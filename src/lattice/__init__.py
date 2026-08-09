"""lattice — the consolidation SDK for chorus episodic memory."""

from __future__ import annotations

from lattice.domain import (
    AppliedContextResult,
    ApplyResult,
    ContextSelectionCaptureResult,
    HabitAction,
    HabitDraft,
    HintKind,
    Packet,
    PatternDraft,
    Proposal,
    ValidationResult,
)
from lattice.facade import Lattice

__all__ = [
    "AppliedContextResult",
    "ApplyResult",
    "ContextSelectionCaptureResult",
    "HabitAction",
    "HabitDraft",
    "HintKind",
    "Lattice",
    "Packet",
    "PatternDraft",
    "Proposal",
    "ValidationResult",
]
