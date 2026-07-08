"""No-op semantic extractor — L0 scaffold."""

from __future__ import annotations

from lattice.contracts.episodic import EpisodeBatch
from lattice.contracts.semantic import SemanticAtom
from lattice.domain.operation import MemoryOperation


class NoopSemanticExtractor:
    """Returns no candidates until L2 wires a real LLM extractor."""

    def extract(self, batch: EpisodeBatch) -> tuple[SemanticAtom, ...]:
        _ = batch
        return ()


class NoopSemanticReconciler:
    """Passes through empty candidate sets."""

    def reconcile(
        self,
        candidates: tuple[SemanticAtom, ...],
        existing: tuple[SemanticAtom, ...],
    ) -> tuple[MemoryOperation, ...]:
        _ = candidates, existing
        return ()


__all__ = ["NoopSemanticExtractor", "NoopSemanticReconciler"]
