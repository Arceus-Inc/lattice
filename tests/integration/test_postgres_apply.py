"""Real-Postgres atomic apply integration tests."""

from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from threading import Barrier

import psycopg
import pytest
from tests.integration.conftest import _GrowingReader, retry_cluster_episodes, valid_retry_proposal

from lattice.contracts.atom import Atom, AtomStore
from lattice.domain.result import ApplyResult
from lattice.facade import Lattice
from lattice.stores.postgres import PostgresLatticeStore


def _lattice(store: PostgresLatticeStore, reader: _GrowingReader) -> Lattice:
    return store.build_lattice(episodes=reader)


class _FailingAfterWrite:
    def __init__(self, store: AtomStore) -> None:
        self._store = store

    def list_active(self, employee_id: str) -> tuple[Atom, ...]:
        return self._store.list_active(employee_id)

    def write(self, atom: Atom) -> None:
        self._store.write(atom)
        raise RuntimeError("forced failure after atom write")

    def invalidate(self, employee_id: str, key: str, *, at: datetime) -> None:
        self._store.invalidate(employee_id, key, at=at)


def test_postgres_apply_commits_atom_and_cursor_across_restart(pg_database: str) -> None:
    company_id = uuid.uuid4()
    reader = _GrowingReader(list(retry_cluster_episodes()))
    with PostgresLatticeStore.open(pg_database, company_id=company_id) as store:
        assert _lattice(store, reader).apply(valid_retry_proposal()).ok is True

    with PostgresLatticeStore.open(pg_database, company_id=company_id) as restarted:
        assert restarted.atoms.list_active("e_be_1")[0].key == "api.retry"
        assert restarted.cursor.get("e_be_1").episodes_seen == 5


def test_postgres_apply_rolls_back_atom_and_cursor_after_write_failure(pg_database: str) -> None:
    reader = _GrowingReader(list(retry_cluster_episodes()))
    with PostgresLatticeStore.open(pg_database, company_id=uuid.uuid4()) as store:
        lattice = Lattice(
            episodes=reader,
            atoms=_FailingAfterWrite(store.atoms),
            cursor=store.cursor,
            apply_scope=store.apply_scope,
        )
        with pytest.raises(RuntimeError, match="forced failure"):
            lattice.apply(valid_retry_proposal())
        assert store.atoms.list_active("e_be_1") == ()
        assert store.cursor.get("e_be_1").episodes_seen == 0


def test_postgres_apply_validation_failure_writes_neither_store(pg_database: str) -> None:
    reader = _GrowingReader(list(retry_cluster_episodes()))
    with PostgresLatticeStore.open(pg_database, company_id=uuid.uuid4()) as store:
        result = _lattice(store, reader).apply(valid_retry_proposal(run_ids=("missing",)))
        assert result.ok is False
        assert store.atoms.list_active("e_be_1") == ()
        assert store.cursor.get("e_be_1").episodes_seen == 0


def test_postgres_apply_serializes_same_employee_scopes(pg_database: str) -> None:
    company_id = uuid.uuid4()
    reader = _GrowingReader(list(retry_cluster_episodes()))
    barrier = Barrier(2)
    with (
        PostgresLatticeStore.open(pg_database, company_id=company_id) as first_store,
        PostgresLatticeStore.open(pg_database, company_id=company_id) as second_store,
    ):
        first = _lattice(first_store, reader)
        second = _lattice(second_store, reader)
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = tuple(
                executor.map(
                    _apply_after_barrier,
                    (first, second),
                    (barrier, barrier),
                )
            )
        assert sum(result.ok for result in results) == 1
        assert sum(result.errors == ("no fresh episodes",) for result in results) == 1
        assert first_store.cursor.get("e_be_1").episodes_seen == 5
        assert len(first_store.atoms.list_active("e_be_1")) == 1


def test_postgres_apply_replay_does_not_create_an_atom_revision(pg_database: str) -> None:
    company_id = uuid.uuid4()
    reader = _GrowingReader(list(retry_cluster_episodes()))
    with PostgresLatticeStore.open(pg_database, company_id=company_id) as store:
        lattice = _lattice(store, reader)
        assert lattice.apply(valid_retry_proposal()).ok is True
        before = _revision_count(pg_database)
        result = lattice.apply(valid_retry_proposal())
        assert result.errors == ("no fresh episodes",)
        assert _revision_count(pg_database) == before


def _apply_after_barrier(lattice: Lattice, barrier: Barrier) -> ApplyResult:
    barrier.wait()
    return lattice.apply(valid_retry_proposal())


def _revision_count(conninfo: str) -> int:
    with psycopg.connect(conninfo) as connection:
        row = connection.execute("SELECT COUNT(*) FROM lattice_atom_revision").fetchone()
    if row is None or not isinstance(row[0], int):
        raise RuntimeError("revision count query did not return an integer")
    return row[0]
