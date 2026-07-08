"""Semantic reconciliation — reconcile candidates against existing atoms."""

from __future__ import annotations

from lattice.contracts.semantic import SemanticAtom
from lattice.domain.operation import MemoryOperation, MemoryOperationKind
from lattice.semantic.extract import NoopSemanticReconciler

__all__ = ["AddOnlySemanticReconciler", "NoopSemanticReconciler"]


class AddOnlySemanticReconciler:
    """L2 default: ADD every candidate; no UPDATE/DELETE yet."""

    def reconcile(
        self,
        candidates: tuple[SemanticAtom, ...],
        existing: tuple[SemanticAtom, ...],
    ) -> tuple[MemoryOperation, ...]:
        _ = existing
        return tuple(
            MemoryOperation(
                kind=MemoryOperationKind.ADD,
                atom_id=candidate.id,
                employee_id=candidate.employee_id,
                claim=candidate.claim,
                rationale="add-only reconcile",
                source_run_ids=candidate.source_run_ids,
            )
            for candidate in candidates
        )
