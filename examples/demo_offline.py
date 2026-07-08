"""Offline demo — noop consolidation over an in-memory episodic reader."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from lattice.compose import build_default
from lattice.contracts.episodic import RawEpisode


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
            run_id="r_inc",
            task_id="t_2",
            employee_id="e_be_1",
            role="backend_engineer",
            scope="project",
            intent="wire auth",
            outcome="incomplete",
            score=0.4,
            created_at=now,
            recorded_at=now,
            artifacts=(),
            files_touched=("src/api/auth.py",),
            body="timed out mid-beat",
        ),
    )
    reader = InMemoryEpisodicReader(episodes)
    lattice = build_default(consolidated_root=Path(".lattice-demo"), episodes=reader)
    result = lattice.consolidate("e_be_1")
    print(
        f"scanned={result.episodes_scanned} selected={result.episodes_selected} "
        f"skipped={result.skipped}"
    )
    if result.semantic is not None:
        print(f"semantic_ops={len(result.semantic.ops_applied)}")
    if result.procedural is not None:
        print(f"skill_patches_proposed={len(result.procedural.patches_proposed)}")


if __name__ == "__main__":
    main()
