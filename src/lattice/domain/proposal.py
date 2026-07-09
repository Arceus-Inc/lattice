"""Agent-authored consolidation proposal — pure domain, zero I/O."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class OpKind(StrEnum):
    """Auditable write intent over semantic or procedural memory."""

    ASSERT = "assert"
    SUPERSEDE = "supersede"
    PATCH = "patch"


@dataclass(frozen=True)
class Op:
    """One operation in a consolidation proposal."""

    kind: OpKind
    key: str
    value: str
    source_run_ids: tuple[str, ...]
    supersedes: str | None = None
    skill: str | None = None
    section: str | None = None


@dataclass(frozen=True)
class Proposal:
    """Structured consolidation intent authored by the employee agent."""

    employee_id: str
    ops: tuple[Op, ...]
