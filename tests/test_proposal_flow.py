"""Proposal validate and apply round-trip."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from lattice.compose import build_default
from lattice.contracts.episodic import RawEpisode
from lattice.domain.proposal import PatternDraft, Proposal


class _Reader:
    def __init__(self, episodes: tuple[RawEpisode, ...]) -> None:
        self._episodes = episodes

    def records_for(self, employee_id: str) -> tuple[RawEpisode, ...]:
        return tuple(ep for ep in self._episodes if ep.employee_id == employee_id)

    def count_for(self, employee_id: str) -> int:
        return len(self.records_for(employee_id))


def _episode(run_id: str) -> RawEpisode:
    now = datetime.now(UTC)
    return RawEpisode(
        run_id=run_id,
        task_id="t",
        employee_id="e1",
        role="backend_engineer",
        scope="project",
        intent="retry",
        outcome="done",
        score=1.0,
        created_at=now,
        recorded_at=now,
        artifacts=(),
        files_touched=("src/api/client.py",),
        body="added backoff",
    )


def test_packet_and_apply_round_trip(tmp_path: Path) -> None:
    episodes = (_episode("r1"), _episode("r2"))
    lattice = build_default(
        consolidated_root=tmp_path,
        episodes=_Reader(episodes),
        min_new_episodes=2,
        min_cluster_size=2,
    )
    assert lattice.gate_open("e1") is True
    packet = lattice.packet("e1")
    assert packet is not None
    assert len(packet.engrams) == 2
    assert len(packet.hints) == 1

    proposal = Proposal(
        employee_id="e1",
        patterns=(
            PatternDraft(
                key="api.retry",
                claim="use exponential backoff on HTTP clients; cap delay at 30s",
                source_run_ids=("r1", "r2"),
            ),
        ),
    )
    validation = lattice.validate(proposal)
    assert validation.ok is True

    result = lattice.apply(proposal)
    assert result.ok is True
    assert result.patterns_written == 1
    context = lattice.context("e1", "retry api")
    assert "api.retry" in context


def test_validate_rejects_unknown_run_id(tmp_path: Path) -> None:
    episodes = (_episode("r1"),)
    lattice = build_default(consolidated_root=tmp_path, episodes=_Reader(episodes))
    proposal = Proposal(
        employee_id="e1",
        patterns=(
            PatternDraft(
                key="api.retry",
                claim="x",
                source_run_ids=("missing",),
            ),
        ),
    )
    validation = lattice.validate(proposal)
    assert validation.ok is False
    assert any("unknown source_run_id" in err for err in validation.errors)
