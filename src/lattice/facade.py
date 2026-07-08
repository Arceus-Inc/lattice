"""Lattice facade — thin wiring over ConsolidationPass."""

from __future__ import annotations

from lattice.consolidate.pass_ import ConsolidationPass
from lattice.consolidate.prune import NoopPruner, Pruner
from lattice.contracts.cursor import ConsolidationCursor
from lattice.contracts.episodic import EpisodicReader
from lattice.domain.result import ConsolidationResult
from lattice.episodic.selector import EpisodeSelector
from lattice.episodic.trigger import ConsolidationTrigger
from lattice.procedural.consolidator import ProceduralConsolidator
from lattice.semantic.consolidator import SemanticConsolidator


class Lattice:
    """The consolidation SDK entry point."""

    def __init__(
        self,
        *,
        episodes: EpisodicReader,
        cursor: ConsolidationCursor,
        semantic: SemanticConsolidator,
        procedural: ProceduralConsolidator,
        min_new_episodes: int = 1,
        selector_limit: int = 20,
        pruner: Pruner | None = None,
    ) -> None:
        self._trigger = ConsolidationTrigger(
            episodes=episodes,
            cursor=cursor,
            min_new_episodes=min_new_episodes,
        )
        self._pass = ConsolidationPass(
            episodes=episodes,
            cursor=cursor,
            trigger=self._trigger,
            selector=EpisodeSelector(episodes=episodes, limit=selector_limit),
            semantic=semantic,
            procedural=procedural,
            pruner=pruner or NoopPruner(),
        )

    def should_consolidate(self, employee_id: str) -> bool:
        return self._trigger.should_run(employee_id)

    def consolidate(self, employee_id: str) -> ConsolidationResult:
        return self._pass.run(employee_id)
