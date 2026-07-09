"""E2E-05 / E2E-10 — persistence and cursor advancement."""

from __future__ import annotations

import json
from pathlib import Path

from lattice.compose import build_default
from tests.integration.conftest import (
    BeatSimulator,
    _GrowingReader,
    retry_cluster_episodes,
    valid_retry_proposal,
)


def test_persistence_across_restart(tmp_path: Path) -> None:
    """E2E-05: atoms and cursor survive a new Lattice instance."""
    sim = BeatSimulator(consolidated_root=tmp_path)
    for episode in retry_cluster_episodes():
        sim.append_beat(episode)

    sim.lattice.apply(valid_retry_proposal())

    episodes = list(sim._episodes)
    restarted = build_default(
        consolidated_root=tmp_path,
        episodes=_GrowingReader(episodes),
    )

    context = restarted.context("e_be_1", "retry")
    assert "api.retry" in context
    assert restarted.gate_open("e_be_1") is False

    cursor = json.loads((tmp_path / ".cursor.json").read_text())
    assert cursor["e_be_1"]["episodes_seen"] == 5


def test_cursor_advances_only_on_successful_apply(tmp_path: Path) -> None:
    """E2E-10: cursor advances on success, not on validation failure."""
    sim = BeatSimulator(consolidated_root=tmp_path)
    for episode in retry_cluster_episodes():
        sim.append_beat(episode)

    assert sim.gate_open() is True

    bad_proposal = valid_retry_proposal(run_ids=("ghost_run",))
    bad_result = sim.lattice.apply(bad_proposal)
    assert bad_result.ok is False
    assert sim.gate_open() is True

    good_result = sim.lattice.apply(valid_retry_proposal())
    assert good_result.ok is True
    assert sim.gate_open() is False

    cursor = json.loads((tmp_path / ".cursor.json").read_text())
    assert cursor["e_be_1"]["episodes_seen"] == 5
    assert cursor["e_be_1"]["last_run_id"] == "r_b5"
