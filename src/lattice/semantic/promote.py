"""Semantic promotion — apply reconciled operations to the store."""

from __future__ import annotations

from lattice.contracts.semantic import SemanticStore
from lattice.domain.operation import MemoryOperation, MemoryOperationKind
from lattice.domain.result import SemanticOutcome


class SemanticPromoter:
    """Apply memory operations through the semantic store port."""

    def __init__(self, store: SemanticStore) -> None:
        self._store = store

    def apply(self, operations: tuple[MemoryOperation, ...]) -> SemanticOutcome:
        written = 0
        applied: list[MemoryOperation] = []
        for op in operations:
            if op.kind is MemoryOperationKind.NOOP:
                continue
            result = self._store.apply(op)
            applied.append(op)
            if result is not None:
                written += 1
        return SemanticOutcome(ops_applied=tuple(applied), atoms_written=written)
