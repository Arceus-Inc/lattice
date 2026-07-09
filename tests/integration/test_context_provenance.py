"""E2E-08 / E2E-09 — context retrieval, provenance, and beat-start teaser."""

from __future__ import annotations

from pathlib import Path

from tests.integration.conftest import (
    BeatSimulator,
    retry_cluster_episodes,
    valid_retry_proposal,
)


def test_context_renders_provenance(tmp_path: Path) -> None:
    sim = BeatSimulator(consolidated_root=tmp_path)
    for episode in retry_cluster_episodes():
        sim.append_beat(episode)
    sim.lattice.apply(valid_retry_proposal())

    context = sim.lattice.context("e_be_1", "retry api client")
    assert "**api.retry**:" in context
    assert "src: r_b1" in context
    assert "recall(query=" in context

    # With a single active pattern, recency/activation weights still surface it even
    # when token overlap is zero — verify overlap path via a targeted query instead.
    targeted = sim.lattice.context("e_be_1", "exponential backoff HTTP")
    assert "api.retry" in targeted


def test_beat_start_teaser_with_patterns(tmp_path: Path) -> None:
    sim = BeatSimulator(consolidated_root=tmp_path)
    for episode in retry_cluster_episodes():
        sim.append_beat(episode)
    sim.lattice.apply(valid_retry_proposal())

    teaser = sim.lattice.beat_start_teaser("e_be_1", "retry policy")
    assert "**Distilled patterns:**" in teaser
    assert "api.retry" in teaser
    assert len(teaser) <= 400


def test_beat_start_teaser_empty_without_patterns(tmp_path: Path) -> None:
    sim = BeatSimulator(consolidated_root=tmp_path)
    teaser = sim.lattice.beat_start_teaser("e_be_1", "retry policy")
    assert teaser == ""
