"""Consolidation outcomes."""

from __future__ import annotations

from dataclasses import dataclass

from lattice.contracts.procedural import SkillDraft, SkillPatch
from lattice.domain.operation import MemoryOperation


@dataclass(frozen=True)
class SemanticOutcome:
    """Result of the P0 semantic pass."""

    ops_applied: tuple[MemoryOperation, ...]
    atoms_written: int


@dataclass(frozen=True)
class ProceduralOutcome:
    """Result of the P1 procedural pass."""

    patches_proposed: tuple[SkillPatch, ...]
    patches_promoted: tuple[SkillPatch, ...]
    drafts_proposed: tuple[SkillDraft, ...]
    drafts_promoted: tuple[SkillDraft, ...]


@dataclass(frozen=True)
class ConsolidationResult:
    """Full pass result — THE LOOP output."""

    employee_id: str
    episodes_scanned: int
    episodes_selected: int
    semantic: SemanticOutcome | None
    procedural: ProceduralOutcome | None
    skipped: bool = False

    @staticmethod
    def skipped_for(employee_id: str, *, episodes_scanned: int) -> ConsolidationResult:
        return ConsolidationResult(
            employee_id=employee_id,
            episodes_scanned=episodes_scanned,
            episodes_selected=0,
            semantic=None,
            procedural=None,
            skipped=True,
        )
