"""Consolidation pass — WRITE→STORE→RETRIEVE owned by chorus; lattice runs RANK→RECONCILE."""

from __future__ import annotations

from lattice.consolidate.prune import Pruner
from lattice.contracts.cursor import ConsolidationCursor
from lattice.contracts.episodic import EpisodicReader
from lattice.domain.result import ConsolidationResult
from lattice.episodic.selector import EpisodeSelector
from lattice.episodic.trigger import ConsolidationTrigger
from lattice.procedural.consolidator import ProceduralConsolidator
from lattice.semantic.consolidator import SemanticConsolidator


class ConsolidationPass:
    """Orchestrate one consolidation run for a single employee."""

    def __init__(
        self,
        *,
        episodes: EpisodicReader,
        cursor: ConsolidationCursor,
        trigger: ConsolidationTrigger,
        selector: EpisodeSelector,
        semantic: SemanticConsolidator,
        procedural: ProceduralConsolidator,
        pruner: Pruner | None = None,
    ) -> None:
        self._episodes = episodes
        self._cursor = cursor
        self._trigger = trigger
        self._selector = selector
        self._semantic = semantic
        self._procedural = procedural
        self._pruner = pruner

    def run(self, employee_id: str) -> ConsolidationResult:
        scanned = self._episodes.count_for(employee_id)
        if not self._trigger.should_run(employee_id):
            return ConsolidationResult.skipped_for(employee_id, episodes_scanned=scanned)

        batch = self._selector.select(employee_id)
        semantic = self._semantic.run(batch)
        procedural = self._procedural.run(batch)

        if self._pruner is not None:
            self._pruner.prune(employee_id)

        watermark = batch.watermark_run_id
        if watermark is not None:
            self._cursor.advance(
                employee_id,
                last_run_id=watermark,
                episodes_seen=scanned,
            )

        return ConsolidationResult(
            employee_id=employee_id,
            episodes_scanned=scanned,
            episodes_selected=batch.selected_count,
            semantic=semantic,
            procedural=procedural,
            skipped=False,
        )
