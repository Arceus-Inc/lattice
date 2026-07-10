"""Composition root — the one place allowed to import chorus."""

from __future__ import annotations

from chorus.memory import EpisodicStore, SprintDelta

from lattice.contracts.episodic import EpisodicReader, RawEpisode


class ChorusEpisodicReader:
    """Adapt chorus ``EpisodicStore`` to lattice ``EpisodicReader``."""

    def __init__(self, store: EpisodicStore) -> None:
        self._store = store

    def records_for(self, employee_id: str) -> tuple[RawEpisode, ...]:
        return tuple(_to_raw(delta) for delta in self._store.records_for(employee_id))

    def count_for(self, employee_id: str) -> int:
        return len(self._store.records_for(employee_id))


def _to_raw(delta: SprintDelta) -> RawEpisode:
    return RawEpisode(
        run_id=delta.run_id,
        task_id=delta.task_id,
        employee_id=delta.employee_id,
        role=delta.role,
        scope=delta.scope,
        intent=delta.intent,
        outcome=delta.outcome,
        score=delta.score,
        created_at=delta.created_at,
        recorded_at=delta.recorded_at,
        artifacts=delta.artifacts,
        files_touched=delta.files_touched,
        body=delta.body,
    )


def satisfies_episodic_reader(adapter: ChorusEpisodicReader) -> bool:
    return isinstance(adapter, EpisodicReader)
