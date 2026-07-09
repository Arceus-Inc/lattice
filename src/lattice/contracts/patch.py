"""Procedural patch port — evolved SKILL.md overlays (P1)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class SkillPatch:
    """An update to an existing skill playbook section."""

    skill_slug: str
    section: str
    new_content: str
    source_run_ids: tuple[str, ...]
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class SkillDraft:
    """A new evolved skill directory overlay."""

    slug: str
    title: str
    body: str
    source_run_ids: tuple[str, ...]
    metadata: dict[str, object] = field(default_factory=dict)


@runtime_checkable
class PatchStore(Protocol):
    """Evolved SKILL.md overlays — never mutates chorus_employee canonical skills."""

    def list_patches(self, employee_id: str) -> tuple[SkillPatch, ...]: ...

    def apply_patch(self, employee_id: str, patch: SkillPatch) -> str:
        """Write an overlay section; returns stable path id."""
        ...

    def apply_draft(self, employee_id: str, draft: SkillDraft) -> str:
        """Write a new overlay skill; returns stable path id."""
        ...
