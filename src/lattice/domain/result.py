"""Consolidation outcomes."""

from __future__ import annotations

from dataclasses import dataclass, field


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
