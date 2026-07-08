"""Memory and promotion operations — pure domain, zero I/O."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MemoryOperationKind(StrEnum):
    """Auditable consolidation operation over semantic memory."""

    ADD = "add"
    UPDATE = "update"
    DELETE = "delete"
    NOOP = "noop"


class PromotionVerdictKind(StrEnum):
    """Gate decision for a procedural promotion."""

    ACCEPT = "accept"
    REJECT = "reject"
    DEFER = "defer"


@dataclass(frozen=True)
class MemoryOperation:
    """One auditable semantic write lattice proposes."""

    kind: MemoryOperationKind
    atom_id: str
    employee_id: str
    claim: str
    rationale: str
    source_run_ids: tuple[str, ...]


@dataclass(frozen=True)
class PromotionVerdict:
    """Whether a skill patch or draft may be promoted."""

    kind: PromotionVerdictKind
    rationale: str
