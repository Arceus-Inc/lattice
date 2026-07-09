"""examples/chorus_bridge.py — real chorus EpisodicStore adapter."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

pytest.importorskip("chorus")

from chorus.memory import EpisodicStore, SprintDelta  # noqa: E402

from examples.chorus_bridge import (  # noqa: E402
    ChorusEpisodicReader,
    build_lattice_for_chorus,
    satisfies_episodic_reader,
)
from lattice.domain.proposal import PatternDraft, Proposal  # noqa: E402


def _delta(run_id: str) -> SprintDelta:
    now = datetime.now(UTC)
    return SprintDelta(
        run_id=run_id,
        task_id=f"t_{run_id}",
        employee_id="e_be_1",
        role="backend_engineer",
        scope="project",
        intent="add retry",
        outcome="done",
        score=0.9,
        created_at=now,
        recorded_at=now,
        artifacts=(),
        files_touched=("src/api/client.py",),
        body=f"beat {run_id}",
    )


def test_build_lattice_for_chorus_wires_company_root(tmp_path: Path) -> None:
    company = tmp_path / "acme"
    store = EpisodicStore(company / "memory")
    for i in range(1, 6):
        store.append(_delta(f"r_b{i}"))

    lattice = build_lattice_for_chorus(company, min_new_episodes=5, min_cluster_size=2)
    assert satisfies_episodic_reader(ChorusEpisodicReader(store))
    assert lattice.gate_open("e_be_1") is True

    result = lattice.apply(
        Proposal(
            employee_id="e_be_1",
            patterns=(
                PatternDraft(
                    key="api.retry",
                    claim="HTTP client retries use exponential backoff capped at 30s",
                    source_run_ids=("r_b1", "r_b2", "r_b3", "r_b4", "r_b5"),
                ),
            ),
        )
    )
    assert result.ok is True
    assert (company / "lattice" / "e_be_1" / "semantic" / "api__retry.json").exists()
