"""Agent-authored consolidation proposal — patterns (semantic memory)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class OpKind(StrEnum):
    """Compiled write intent — internal to validate/apply after compilation."""

    ASSERT = "assert"
    SUPERSEDE = "supersede"


@dataclass(frozen=True)
class PatternDraft:
    """Declarative claim promoted to semantic memory."""

    key: str
    claim: str
    source_run_ids: tuple[str, ...]
    supersedes: str | None = None


@dataclass(frozen=True)
class Op:
    """One compiled operation applied to the pattern store."""

    kind: OpKind
    key: str
    value: str
    source_run_ids: tuple[str, ...]
    supersedes: str | None = None


@dataclass(frozen=True)
class Proposal:
    """Structured consolidation intent authored by the employee agent."""

    employee_id: str
    patterns: tuple[PatternDraft, ...] = ()
