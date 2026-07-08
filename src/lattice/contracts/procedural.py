"""Procedural consolidation ports — P1 skill evolution."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

from lattice.contracts.episodic import EpisodeBatch
from lattice.domain.operation import PromotionVerdict


@dataclass(frozen=True)
class SkillPatch:
    """An update to an existing skill playbook section."""

    skill_slug: str
    section: str
    new_content: str
    rationale: str
    source_run_ids: tuple[str, ...]
    confidence: float
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class SkillDraft:
    """A proposed new skill directory."""

    slug: str
    title: str
    body: str
    source_run_ids: tuple[str, ...]
    applies_to_roles: tuple[str, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)


@runtime_checkable
class ProceduralStore(Protocol):
    """Evolved SKILL.md overlays — never mutates chorus_employee canonical skills."""

    def list_patches(self, employee_id: str) -> tuple[SkillPatch, ...]: ...

    def promote_patch(self, employee_id: str, patch: SkillPatch) -> str:
        """Write an overlay; returns stable path id."""
        ...

    def promote_draft(self, employee_id: str, draft: SkillDraft) -> str: ...


@runtime_checkable
class SkillEvolver(Protocol):
    """Derive skill patches/drafts from episodic traces."""

    def evolve(
        self,
        batch: EpisodeBatch,
        *,
        canonical_skills_root: Path | None,
    ) -> tuple[SkillPatch, ...]: ...

    def propose_drafts(
        self,
        batch: EpisodeBatch,
        *,
        canonical_skills_root: Path | None,
    ) -> tuple[SkillDraft, ...]: ...


@runtime_checkable
class PromotionGate(Protocol):
    """Accept or reject a procedural promotion before write."""

    def review_patch(self, patch: SkillPatch) -> PromotionVerdict: ...

    def review_draft(self, draft: SkillDraft) -> PromotionVerdict: ...
