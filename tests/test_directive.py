"""Beat-end teaser and directive policy."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from lattice.compose import build_default
from lattice.contracts.episodic import RawEpisode
from lattice.directive import (
    BEAT_END_GATE_OPEN,
    DEFAULT_MIN_NEW_EPISODES,
    beat_end_notice,
    beat_start_notice,
)


class _Reader:
    def __init__(self, episodes: tuple[RawEpisode, ...]) -> None:
        self._episodes = episodes

    def records_for(self, employee_id: str) -> tuple[RawEpisode, ...]:
        return tuple(ep for ep in self._episodes if ep.employee_id == employee_id)

    def count_for(self, employee_id: str) -> int:
        return len(self.records_for(employee_id))


def _episode(run_id: str, *, files: tuple[str, ...] = ("src/a.py",)) -> RawEpisode:
    now = datetime.now(UTC)
    return RawEpisode(
        run_id=run_id,
        task_id="t",
        employee_id="e1",
        role="backend_engineer",
        scope="project",
        intent="work",
        outcome="done",
        score=1.0,
        created_at=now,
        recorded_at=now,
        artifacts=(),
        files_touched=files,
        body="",
    )


def test_beat_end_notice_silent_when_gate_closed() -> None:
    assert beat_end_notice(gate_open=False) == ""


def test_beat_end_notice_open() -> None:
    assert beat_end_notice(gate_open=True) == BEAT_END_GATE_OPEN


def test_beat_start_notice_empty_without_context() -> None:
    assert beat_start_notice(context="") == ""


def test_default_gate_requires_n_beats(tmp_path: Path) -> None:
    episodes = tuple(_episode(f"r{i}") for i in range(DEFAULT_MIN_NEW_EPISODES - 1))
    lattice = build_default(consolidated_root=tmp_path, episodes=_Reader(episodes))
    assert lattice.gate_open("e1") is False
    assert lattice.beat_end_teaser("e1") == ""

    one_more = (*episodes, _episode("r_last"))
    lattice2 = build_default(consolidated_root=tmp_path, episodes=_Reader(one_more))
    assert lattice2.gate_open("e1") is True
    assert "Lattice gate open" in lattice2.beat_end_teaser("e1")
