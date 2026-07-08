"""P0 semantic consolidation — extract → reconcile → promote."""

from __future__ import annotations

from lattice.contracts.episodic import EpisodeBatch
from lattice.contracts.semantic import SemanticExtractor, SemanticReconciler, SemanticStore
from lattice.domain.result import SemanticOutcome
from lattice.semantic.promote import SemanticPromoter


class SemanticConsolidator:
    """Owns the semantic vertical slice for one episode batch."""

    def __init__(
        self,
        *,
        extractor: SemanticExtractor,
        reconciler: SemanticReconciler,
        store: SemanticStore,
    ) -> None:
        self._extractor = extractor
        self._reconciler = reconciler
        self._store = store
        self._promoter = SemanticPromoter(store)

    def run(self, batch: EpisodeBatch) -> SemanticOutcome:
        candidates = self._extractor.extract(batch)
        existing = self._store.list_for(batch.employee_id)
        operations = self._reconciler.reconcile(candidates, existing)
        return self._promoter.apply(operations)
