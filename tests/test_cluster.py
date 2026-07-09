"""Cluster and gate algorithms."""

from __future__ import annotations

from datetime import UTC, datetime

from lattice.cluster import build_hints, cluster, gate_open, rank
from lattice.contracts.cursor import ConsolidationWatermark
from lattice.contracts.episodic import RawEpisode


def _episode(
    run_id: str,
    *,
    outcome: str = "done",
    files: tuple[str, ...] = (),
    intent: str = "work",
) -> RawEpisode:
    now = datetime.now(UTC)
    return RawEpisode(
        run_id=run_id,
        task_id="t",
        employee_id="e1",
        role="backend_engineer",
        scope="project",
        intent=intent,
        outcome=outcome,
        score=1.0,
        created_at=now,
        recorded_at=now,
        artifacts=(),
        files_touched=files,
        body="",
    )


def test_rank_prefers_done() -> None:
    ranked = rank((_episode("r_inc", outcome="incomplete"), _episode("r_done")))
    assert [ep.run_id for ep in ranked] == ["r_done", "r_inc"]


def test_gate_requires_cluster_size() -> None:
    watermark = ConsolidationWatermark(
        employee_id="e1",
        last_run_id=None,
        episodes_seen=0,
        consolidated_at=None,
    )
    solo = (_episode("r1", files=("src/a.py",)),)
    assert gate_open(solo, watermark, min_new=1, min_cluster=2) is False

    pair = (
        _episode("r1", files=("src/a.py",)),
        _episode("r2", files=("src/b.py",)),
    )
    assert gate_open(pair, watermark, min_new=1, min_cluster=2) is True


def test_cluster_and_pattern_hints() -> None:
    episodes = (
        _episode("r1", files=("src/a.py",)),
        _episode("r2", files=("src/b.py",)),
        _episode("r3", files=("docs/readme.md",)),
    )
    groups = cluster(episodes)
    assert len(groups) == 2
    hints = build_hints(groups, min_cluster=2)
    assert len(hints) == 1
    assert hints[0].key_template == "src"
