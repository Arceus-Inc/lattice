"""Consolidation trigger — after N new episodes."""

from __future__ import annotations

from lattice.contracts.cursor import ConsolidationCursor
from lattice.contracts.episodic import EpisodicReader


class ConsolidationTrigger:
    """Gate consolidation on episode count since the last watermark."""

    def __init__(
        self,
        *,
        episodes: EpisodicReader,
        cursor: ConsolidationCursor,
        min_new_episodes: int = 1,
    ) -> None:
        self._episodes = episodes
        self._cursor = cursor
        self._min_new = min_new_episodes

    def should_run(self, employee_id: str) -> bool:
        watermark = self._cursor.get(employee_id)
        total = self._episodes.count_for(employee_id)
        new_since = total - watermark.episodes_seen
        return new_since >= self._min_new
