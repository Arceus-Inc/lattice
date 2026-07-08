"""Episode selector — RANK stage of THE LOOP."""

from __future__ import annotations

from lattice.contracts.episodic import EpisodeBatch, EpisodicReader, RawEpisode


class EpisodeSelector:
    """Rank and select episodes worth consolidating.

    v1 rules only: prefer ``done`` outcomes, recency order, cap batch size.
    """

    def __init__(self, *, episodes: EpisodicReader, limit: int = 20) -> None:
        self._episodes = episodes
        self._limit = limit

    def select(self, employee_id: str) -> EpisodeBatch:
        raw = self._episodes.records_for(employee_id)
        ranked = _rank(raw)[: self._limit]
        watermark = ranked[0].run_id if ranked else None
        return EpisodeBatch(
            employee_id=employee_id,
            episodes=tuple(ranked),
            watermark_run_id=watermark,
        )


def _rank(episodes: tuple[RawEpisode, ...]) -> list[RawEpisode]:
    """Done beats rank above incomplete/blocked; preserve recency within tier."""

    def key(ep: RawEpisode) -> tuple[int, float]:
        outcome_rank = 0 if ep.outcome == "done" else 1
        return (outcome_rank, -ep.created_at.timestamp())

    return sorted(episodes, key=key)
