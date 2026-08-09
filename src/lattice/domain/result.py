"""Consolidation outcomes."""

from __future__ import annotations

from dataclasses import dataclass, field

from lattice.contracts.applied import AppliedAtomEdge
from lattice.contracts.atom import ContextAtomHit
from lattice.contracts.selection import ContextAtomSelection


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of deterministic proposal validation."""

    ok: bool
    errors: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ApplyResult:
    """Outcome of applying a validated proposal."""

    employee_id: str
    ops_applied: int = 0
    atoms_written: int = 0
    patches_written: int = 0
    errors: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return not self.errors

    @staticmethod
    def failed(*errors: str, employee_id: str = "") -> ApplyResult:
        return ApplyResult(employee_id=employee_id, errors=errors)


@dataclass(frozen=True)
class ContextResult:
    """Rendered context plus the exact atoms selected to produce it."""

    markdown: str
    hits: tuple[ContextAtomHit, ...]


@dataclass(frozen=True)
class AppliedContextResult:
    """Exact persisted outcomes plus legacy hits intentionally excluded from them."""

    edges: tuple[AppliedAtomEdge, ...]
    skipped_unversioned_hits: tuple[ContextAtomHit, ...]


@dataclass(frozen=True)
class ContextSelectionCaptureResult:
    """Durability status for exact revisions captured when context was shown."""

    durable: bool
    selections: tuple[ContextAtomSelection, ...]
    skipped_unversioned_hits: tuple[ContextAtomHit, ...]


@dataclass(frozen=True)
class AdjudicateResult:
    """Outcome of outcome-grounded adjudication over active atoms."""

    employee_id: str
    atoms_updated: int = 0
    episodes_processed: int = 0


@dataclass(frozen=True)
class ForgetResult:
    """Outcome of the sleep forget/discount pass."""

    employee_id: str
    atoms_discounted: int = 0
    atoms_invalidated: int = 0
