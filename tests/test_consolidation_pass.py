"""Consolidation pass integration — noop extractors."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from lattice.compose import build_default
from lattice.contracts.episodic import RawEpisode


class _Reader:
    def __init__(self, episodes: tuple[RawEpisode, ...]) -> None:
        self._episodes = episodes

    def records_for(self, employee_id: str) -> tuple[RawEpisode, ...]:
        return tuple(ep for ep in self._episodes if ep.employee_id == employee_id)

    def count_for(self, employee_id: str) -> int:
        return len(self.records_for(employee_id))


def test_consolidation_pass_scans_and_selects(tmp_path: Path) -> None:
    now = datetime.now(UTC)
    episodes = (
        RawEpisode(
            run_id="r1",
            task_id="t",
            employee_id="e1",
            role="backend_engineer",
            scope="project",
            intent="x",
            outcome="done",
            score=1.0,
            created_at=now,
            recorded_at=now,
            artifacts=(),
            files_touched=(),
            body="",
        ),
    )
    lattice = build_default(consolidated_root=tmp_path, episodes=_Reader(episodes))
    result = lattice.consolidate("e1")
    assert result.skipped is False
    assert result.episodes_scanned == 1
    assert result.episodes_selected == 1
    assert result.semantic is not None
    assert result.semantic.atoms_written == 0
    assert result.procedural is not None
    assert result.procedural.patches_promoted == ()
