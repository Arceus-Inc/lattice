"""Agent-authored consolidation proposal — patterns (semantic) and habits (procedural)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class OpKind(StrEnum):
    """Compiled write intent — internal to validate/apply after compilation."""

    ASSERT = "assert"
    SUPERSEDE = "supersede"
    PATCH = "patch"
    DRAFT = "draft"


class HabitAction(StrEnum):
    """Whether a habit evolves an existing skill or creates a new overlay."""

    EVOLVE = "evolve"
    CREATE = "create"


@dataclass(frozen=True)
class PatternDraft:
    """Declarative claim promoted to semantic memory."""

    key: str
    claim: str
    source_run_ids: tuple[str, ...]
    supersedes: str | None = None


@dataclass(frozen=True)
class HabitDraft:
    """Procedural playbook promoted to an evolved skill overlay."""

    action: HabitAction
    source_run_ids: tuple[str, ...]
    skill: str | None = None
    section: str | None = None
    body: str = ""
    slug: str | None = None
    title: str | None = None


@dataclass(frozen=True)
class Op:
    """One compiled operation applied to stores."""

    kind: OpKind
    key: str
    value: str
    source_run_ids: tuple[str, ...]
    supersedes: str | None = None
    skill: str | None = None
    section: str | None = None
    slug: str | None = None
    title: str | None = None


@dataclass(frozen=True)
class Proposal:
    """Structured consolidation intent authored by the employee agent."""

    employee_id: str
    patterns: tuple[PatternDraft, ...] = ()
    habits: tuple[HabitDraft, ...] = ()
