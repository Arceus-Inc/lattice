"""cluster.py — extended edge cases for gate and new_episodes."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from lattice.cluster import gate_open, new_episodes, rank
from lattice.contracts.cursor import ConsolidationWatermark
from lattice.contracts.episodic import RawEpisode


def _episode(run_id: str, *, offset_minutes: int = 0, files: tuple[str, ...] = ()) -> RawEpisode:
    base = datetime(2026, 7, 8, 12, 0, 0, tzinfo=UTC)
    created = base + timedelta(minutes=offset_minutes)
    return RawEpisode(
        run_id=run_id,
        task_id="t",
        employee_id="e1",
        role="backend_engineer",
        scope="project",
        intent="work",
        outcome="done",
        score=1.0,
        created_at=created,
        recorded_at=created,
        artifacts=(),
        files_touched=files,
        body="",
    )


def test_new_episodes_respects_watermark() -> None:
    episodes = tuple(_episode(f"r{i}", offset_minutes=i) for i in range(1, 6))
    watermark = ConsolidationWatermark(
        employee_id="e1",
        last_run_id="r3",
        episodes_seen=3,
        consolidated_at=None,
    )
    fresh = new_episodes(episodes, watermark)
    assert len(fresh) == 2
    # new_episodes returns top new_count from ranked (recency-first among done beats)
    assert {ep.run_id for ep in fresh} == {"r4", "r5"}


def test_gate_closed_when_below_min_new() -> None:
    episodes = (_episode("r1"), _episode("r2"))
    watermark = ConsolidationWatermark(employee_id="e1", last_run_id=None, episodes_seen=0, consolidated_at=None)
    assert gate_open(episodes, watermark, min_new=5, min_cluster=2) is False


def test_rank_breaks_ties_by_recency() -> None:
    older = _episode("r_old", offset_minutes=1)
    newer = _episode("r_new", offset_minutes=5)
    ranked = rank((older, newer))
    assert ranked[0].run_id == "r_new"
