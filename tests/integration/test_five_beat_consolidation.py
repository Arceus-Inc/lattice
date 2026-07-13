"""E2E-01 / E2E-02 — five-beat golden path and gate-closed cost policy."""

from __future__ import annotations

from pathlib import Path

from tests.integration.conftest import (
    BeatSimulator,
    retry_cluster_episodes,
    valid_retry_proposal,
)


def test_five_beat_golden_path(tmp_path: Path) -> None:
    """E2E-01: 5 beats → gate opens → apply → context hit."""
    sim = BeatSimulator(consolidated_root=tmp_path)
    episodes = retry_cluster_episodes()

    for i, episode in enumerate(episodes, start=1):
        sim.append_beat(episode)
        if i < 5:
            assert sim.gate_open() is False, f"gate should be closed after beat {i}"
            assert sim.beat_end_teaser() == ""
            assert sim.packet() is None

    assert sim.gate_open() is True
    teaser = sim.beat_end_teaser()
    assert "gate open" in teaser.lower()

    packet = sim.packet()
    assert packet is not None
    assert len(packet.engrams) == 5
    assert len(packet.hints) >= 1

    proposal = valid_retry_proposal()
    validation = sim.lattice.validate(proposal)
    assert validation.ok is True

    result = sim.lattice.apply(proposal)
    assert result.ok is True
    assert result.atoms_written == 1

    semantic_file = tmp_path / "e_be_1" / "semantic" / "api__retry.json"
    assert semantic_file.exists()

    memory_md = tmp_path / "e_be_1" / "MEMORY.md"
    assert memory_md.exists()
    memory_text = memory_md.read_text()
    assert "exponential backoff" in memory_text
    assert "LCB" in memory_text
    assert "### api.retry" in memory_text

    forget_result = sim.lattice.forget("e_be_1")
    assert forget_result.atoms_discounted >= 1

    context = sim.lattice.context("e_be_1", "retry")
    assert "api.retry" in context
    assert "r_b1" in context
    assert "src:" in context

    known_runs = {ep.run_id for ep in sim._episodes}
    for run_id in ("r_b1", "r_b2", "r_b3", "r_b4", "r_b5"):
        assert run_id in known_runs


def test_gate_closed_beats_one_through_four(tmp_path: Path) -> None:
    """E2E-02: no consolidation before gate opens."""
    sim = BeatSimulator(consolidated_root=tmp_path)
    episodes = retry_cluster_episodes()

    for episode in episodes[:4]:
        sim.append_beat(episode)

    assert sim.gate_open() is False
    assert sim.beat_end_teaser() == ""
    assert sim.packet() is None

    semantic_dir = tmp_path / "e_be_1" / "semantic"
    assert not semantic_dir.exists()

    cursor_file = tmp_path / ".cursor.json"
    if cursor_file.exists():
        assert '"episodes_seen": 0' in cursor_file.read_text() or "episodes_seen" not in cursor_file.read_text()
