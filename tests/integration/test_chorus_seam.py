"""E2E-11 — ChorusEpisodicReader seam against real EpisodicStore."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

pytest.importorskip("chorus")

from chorus.memory import EpisodicStore, SprintDelta  # noqa: E402
from lattice.compose import build_default  # noqa: E402
from lattice.contracts.episodic import EpisodicReader  # noqa: E402

from examples.chorus_bridge import ChorusEpisodicReader  # noqa: E402
from tests.integration.conftest import valid_retry_proposal  # noqa: E402


def _sprint_delta(run_id: str, *, offset: int = 0) -> SprintDelta:
    base = datetime(2026, 7, 8, 12, 0, 0, tzinfo=UTC)
    return SprintDelta(
        run_id=run_id,
        task_id=f"t_{run_id}",
        employee_id="e_be_1",
        role="backend_engineer",
        scope="project",
        intent="add retry",
        outcome="done",
        score=0.9,
        created_at=base.replace(minute=base.minute + offset),
        recorded_at=base.replace(minute=base.minute + offset),
        artifacts=(),
        files_touched=("src/api/client.py",),
        body=f"beat {run_id}",
    )


def test_chorus_episodic_reader_satisfies_protocol(tmp_path: Path) -> None:
    store = EpisodicStore(tmp_path / "memory")
    reader = ChorusEpisodicReader(store)
    assert isinstance(reader, EpisodicReader)


def test_chorus_seam_five_beat_golden_path(tmp_path: Path) -> None:
    store = EpisodicStore(tmp_path / "memory")
    for i in range(1, 6):
        store.append(_sprint_delta(f"r_b{i}", offset=i))

    reader = ChorusEpisodicReader(store)
    lattice = build_default(
        consolidated_root=tmp_path / "lattice",
        episodes=reader,
    )

    assert lattice.gate_open("e_be_1") is True
    packet = lattice.packet("e_be_1")
    assert packet is not None
    assert len(packet.engrams) == 5

    result = lattice.apply(valid_retry_proposal())
    assert result.ok is True

    context = lattice.context("e_be_1", "retry")
    assert "api.retry" in context
    assert "r_b1" in context
