"""Episode selector ranks done above incomplete."""

from __future__ import annotations

from datetime import UTC, datetime

from lattice.contracts.episodic import RawEpisode
from lattice.episodic.selector import EpisodeSelector


class _Reader:
    def __init__(self, episodes: tuple[RawEpisode, ...]) -> None:
        self._episodes = episodes

    def records_for(self, employee_id: str) -> tuple[RawEpisode, ...]:
        return tuple(ep for ep in self._episodes if ep.employee_id == employee_id)

    def count_for(self, employee_id: str) -> int:
        return len(self.records_for(employee_id))


def _episode(run_id: str, outcome: str) -> RawEpisode:
    now = datetime.now(UTC)
    return RawEpisode(
        run_id=run_id,
        task_id="t",
        employee_id="e1",
        role="backend_engineer",
        scope="project",
        intent="work",
        outcome=outcome,
        score=1.0,
        created_at=now,
        recorded_at=now,
        artifacts=(),
        files_touched=(),
        body="",
    )


def test_selector_prefers_done() -> None:
    reader = _Reader((_episode("r_inc", "incomplete"), _episode("r_done", "done")))
    batch = EpisodeSelector(episodes=reader, limit=10).select("e1")
    assert [ep.run_id for ep in batch.episodes] == ["r_done", "r_inc"]
