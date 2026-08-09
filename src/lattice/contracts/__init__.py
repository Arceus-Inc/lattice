"""lattice contracts — every Protocol and port type (the seam)."""

from __future__ import annotations

from lattice.contracts.applied import (
    AppliedAtomEdge,
    AppliedBeatOutcome,
    AppliedEdgeConflictError,
    AppliedEdgeStore,
    LandedOutcomePhase,
)
from lattice.contracts.atom import Atom, AtomHitReader, AtomStore, ContextAtomHit
from lattice.contracts.cursor import ConsolidationWatermark, CursorConflictError, CursorStore
from lattice.contracts.episodic import EpisodicReader, RawEpisode
from lattice.contracts.patch import PatchStore, SkillDraft, SkillPatch
from lattice.contracts.selection import (
    ContextAtomSelection,
    ContextSelectionCaptureOutcome,
    ContextSelectionConflictError,
    ContextSelectionJournal,
    ContextSelectionSnapshot,
)

__all__ = [
    "AppliedAtomEdge",
    "AppliedBeatOutcome",
    "AppliedEdgeConflictError",
    "AppliedEdgeStore",
    "Atom",
    "AtomHitReader",
    "AtomStore",
    "ConsolidationWatermark",
    "ContextAtomHit",
    "ContextAtomSelection",
    "ContextSelectionCaptureOutcome",
    "ContextSelectionConflictError",
    "ContextSelectionJournal",
    "ContextSelectionSnapshot",
    "CursorConflictError",
    "CursorStore",
    "EpisodicReader",
    "LandedOutcomePhase",
    "PatchStore",
    "RawEpisode",
    "SkillDraft",
    "SkillPatch",
]
