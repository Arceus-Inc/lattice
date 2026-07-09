"""Shared fixtures for lattice integration / E2E tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from lattice.compose import build_default
from lattice.contracts.episodic import EpisodicReader, RawEpisode
from lattice.domain.proposal import PatternDraft, Proposal
from lattice.facade import Lattice


@dataclass
class _GrowingReader:
    """EpisodicReader backed by a mutable episode list."""

    _episodes: list[RawEpisode]

    def records_for(self, employee_id: str) -> tuple[RawEpisode, ...]:
        return tuple(ep for ep in self._episodes if ep.employee_id == employee_id)

    def count_for(self, employee_id: str) -> int:
        return len(self.records_for(employee_id))


def make_episode(
    *,
    run_id: str,
    employee_id: str = "e_be_1",
    intent: str = "add retry",
    outcome: str = "done",
    files_touched: tuple[str, ...] = ("src/api/client.py",),
    body: str = "worked on retry logic",
    offset_minutes: int = 0,
) -> RawEpisode:
    """Build a RawEpisode with sensible defaults for retry-cluster scenarios."""
    base = datetime(2026, 7, 8, 12, 0, 0, tzinfo=UTC)
    created = base + timedelta(minutes=offset_minutes)
    return RawEpisode(
        run_id=run_id,
        task_id=f"t_{run_id}",
        employee_id=employee_id,
        role="backend_engineer",
        scope="project",
        intent=intent,
        outcome=outcome,
        score=0.9,
        created_at=created,
        recorded_at=created,
        artifacts=(),
        files_touched=files_touched,
        body=body,
    )


def retry_cluster_episodes(*, employee_id: str = "e_be_1") -> tuple[RawEpisode, ...]:
    """Five beats on the same file prefix — opens gate at N=5, K=2."""
    bodies = (
        "added retry wrapper",
        "tuned backoff base",
        "capped delay at 30s",
        "added jitter",
        "documented retry policy",
    )
    return tuple(
        make_episode(
            run_id=f"r_b{i}",
            employee_id=employee_id,
            body=body,
            offset_minutes=i,
        )
        for i, body in enumerate(bodies, start=1)
    )


def valid_retry_proposal(
    *,
    employee_id: str = "e_be_1",
    run_ids: tuple[str, ...] = ("r_b1", "r_b2", "r_b3", "r_b4", "r_b5"),
    supersedes: str | None = None,
    claim: str = (
        "HTTP client retries use exponential backoff capped at 30s; config in src/api/client.py"
    ),
) -> Proposal:
    return Proposal(
        employee_id=employee_id,
        patterns=(
            PatternDraft(
                key="api.retry",
                claim=claim,
                source_run_ids=run_ids,
                supersedes=supersedes,
            ),
        ),
    )


@dataclass
class BeatSimulator:
    """Incrementally append beats and query lattice state."""

    consolidated_root: Path
    employee_id: str = "e_be_1"
    min_new_episodes: int = 5
    min_cluster_size: int = 2
    _episodes: list[RawEpisode] = field(default_factory=list)
    _reader: _GrowingReader = field(init=False)
    _lattice: Lattice | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        self._reader = _GrowingReader(self._episodes)

    @property
    def lattice(self) -> Lattice:
        if self._lattice is None:
            self._lattice = build_default(
                consolidated_root=self.consolidated_root,
                episodes=self._reader,
                min_new_episodes=self.min_new_episodes,
                min_cluster_size=self.min_cluster_size,
            )
        return self._lattice

    def append_beat(self, episode: RawEpisode) -> None:
        self._episodes.append(episode)

    def gate_open(self) -> bool:
        return self.lattice.gate_open(self.employee_id)

    def beat_end_teaser(self) -> str:
        return self.lattice.beat_end_teaser(self.employee_id)

    def packet(self):
        return self.lattice.packet(self.employee_id)
