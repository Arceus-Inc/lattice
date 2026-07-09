"""E2E-03 — scattered episodes never form a cluster large enough to open gate."""

from __future__ import annotations

from pathlib import Path

from tests.integration.conftest import BeatSimulator, make_episode


def test_scattered_episodes_gate_stays_closed(tmp_path: Path) -> None:
    """Five new beats on different file prefixes — max cluster size 1 < K=2."""
    sim = BeatSimulator(consolidated_root=tmp_path)

    # No shared file prefix or intent token — each episode buckets by unique run_id.
    intents = ("alpha deploy", "beta refactor", "gamma audit", "delta migrate", "epsilon patch")
    for i, intent in enumerate(intents, start=1):
        sim.append_beat(
            make_episode(
                run_id=f"r_scatter_{i}",
                files_touched=(),
                intent=intent,
                body=f"worked on {intent}",
                offset_minutes=i,
            )
        )

    assert sim.gate_open() is False
    assert sim.beat_end_teaser() == ""
    assert sim.packet() is None
