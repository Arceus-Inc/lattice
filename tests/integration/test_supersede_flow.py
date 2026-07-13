"""E2E-04 — supersede replaces an active pattern."""

from __future__ import annotations

from pathlib import Path

from tests.integration.conftest import (
    BeatSimulator,
    retry_cluster_episodes,
    valid_retry_proposal,
)


def test_supersede_active_pattern(tmp_path: Path) -> None:
    sim = BeatSimulator(consolidated_root=tmp_path)
    for episode in retry_cluster_episodes():
        sim.append_beat(episode)

    first = sim.lattice.apply(valid_retry_proposal())
    assert first.ok is True

    updated_claim = (
        "HTTP retries use exponential backoff capped at 60s; config in src/api/client.py"
    )
    supersede_proposal = valid_retry_proposal(
        run_ids=("r_b5",),
        supersedes="api.retry",
        claim=updated_claim,
    )

    # Need fresh episodes after cursor advanced — gate uses new episodes only.
    # Add one more beat so source_run_id r_b5 is in the post-cursor set is not required
    # since r_b5 was part of original set; supersedes only needs active key.
    validation = sim.lattice.validate(supersede_proposal)
    assert validation.ok is True

    result = sim.lattice.apply(supersede_proposal)
    assert result.ok is True

    context = sim.lattice.context("e_be_1", "retry")
    assert "60s" in context
    assert "30s" not in context

    active = sim.lattice._atoms.list_active("e_be_1")
    active_retry = [a for a in active if a.key == "api.retry"]
    assert len(active_retry) == 1
    assert active_retry[0].value == updated_claim
