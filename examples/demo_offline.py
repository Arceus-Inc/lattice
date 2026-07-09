"""Offline demo — gate, packet, pattern consolidation."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from lattice.compose import build_default
from lattice.contracts.episodic import RawEpisode
from lattice.domain.proposal import PatternDraft, Proposal


class InMemoryEpisodicReader:
    def __init__(self, episodes: tuple[RawEpisode, ...]) -> None:
        self._episodes = episodes

    def records_for(self, employee_id: str) -> tuple[RawEpisode, ...]:
        return tuple(ep for ep in self._episodes if ep.employee_id == employee_id)

    def count_for(self, employee_id: str) -> int:
        return len(self.records_for(employee_id))


def main() -> None:
    now = datetime.now(UTC)
    episodes = (
        RawEpisode(
            run_id="r_done",
            task_id="t_1",
            employee_id="e_be_1",
            role="backend_engineer",
            scope="project",
            intent="add retry",
            outcome="done",
            score=0.9,
            created_at=now,
            recorded_at=now,
            artifacts=(),
            files_touched=("src/api/client.py",),
            body="added exponential backoff",
        ),
        RawEpisode(
            run_id="r_done_2",
            task_id="t_2",
            employee_id="e_be_1",
            role="backend_engineer",
            scope="project",
            intent="add retry",
            outcome="done",
            score=0.8,
            created_at=now,
            recorded_at=now,
            artifacts=(),
            files_touched=("src/api/client.py",),
            body="tuned backoff cap",
        ),
    )
    reader = InMemoryEpisodicReader(episodes)
    lattice = build_default(
        consolidated_root=Path(".lattice-demo"),
        episodes=reader,
        min_new_episodes=2,
        min_cluster_size=2,
    )
    if not lattice.gate_open("e_be_1"):
        print("gate closed")
        return
    packet = lattice.packet("e_be_1")
    assert packet is not None
    print(f"packet engrams={len(packet.engrams)} hints={len(packet.hints)}")

    proposal = Proposal(
        employee_id="e_be_1",
        patterns=(
            PatternDraft(
                key="api.retry",
                claim="HTTP client retries use exponential backoff with a 30s cap",
                source_run_ids=("r_done", "r_done_2"),
            ),
        ),
    )
    result = lattice.apply(proposal)
    print(f"apply ok={result.ok} patterns={result.patterns_written}")
    print(lattice.context("e_be_1", "retry"))


if __name__ == "__main__":
    main()
