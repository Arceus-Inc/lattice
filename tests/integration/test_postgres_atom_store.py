"""Real-Postgres conformance tests for the semantic atom store."""

from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier

import psycopg
from tests.integration.conftest import app_role_conninfo

from lattice.contracts.atom import Atom, AtomStore
from lattice.domain.stats import PatternStats, Tier
from lattice.semantic.retrieve import context_result
from lattice.stores.postgres_atoms import PostgresAtomStore


def _atom(*, value: str = "retry with capped exponential backoff") -> Atom:
    return Atom(
        employee_id="agent-1",
        key="api.retry",
        value=value,
        source_run_ids=("run-1", "run-2"),
        created_at=datetime(2026, 8, 9, tzinfo=UTC),
        activation=0.75,
        stats=PatternStats(alpha_own=3.5, beta_own=1.5, tier=Tier.RULE),
        key_files=("src/api/client.py", "tests/test_client.py"),
    )


def test_postgres_atom_round_trip_survives_restart(pg_database: str) -> None:
    company_id = uuid.uuid4()
    atom = _atom()
    older = Atom(
        employee_id=atom.employee_id,
        key="api.timeout",
        value="client requests time out before a retry is considered",
        source_run_ids=("run-0",),
        created_at=datetime(2026, 8, 8, tzinfo=UTC),
    )
    with PostgresAtomStore.open(pg_database, company_id=company_id) as store:
        typed_store: AtomStore = store
        typed_store.write(atom)
        typed_store.write(older)
        assert typed_store.list_active(atom.employee_id) == (atom, older)

    with PostgresAtomStore.open(pg_database, company_id=company_id) as restarted:
        assert restarted.list_active(atom.employee_id) == (atom, older)


def test_postgres_atom_write_overwrites_head_and_records_versions(pg_database: str) -> None:
    company_id = uuid.uuid4()
    first = _atom(value="retry with capped exponential backoff")
    second = Atom(
        employee_id=first.employee_id,
        key=first.key,
        value="retry with capped exponential backoff and jitter",
        source_run_ids=("run-3",),
        created_at=datetime(2026, 8, 10, tzinfo=UTC),
        activation=0.9,
        stats=PatternStats(alpha_own=4.5, beta_own=1.5, tier=Tier.RULE),
        key_files=("src/api/client.py",),
    )
    with PostgresAtomStore.open(pg_database, company_id=company_id) as store:
        store.write(first)
        store.write(second)
        assert store.list_active(first.employee_id) == (second,)

    with psycopg.connect(pg_database) as admin:
        versions = admin.execute(
            "SELECT version, value FROM lattice_atom_revision "
            "WHERE employee_id = %s AND key = %s ORDER BY version",
            (first.employee_id, first.key),
        ).fetchall()
    assert versions == [(1, first.value), (2, second.value)]


def test_postgres_atom_hits_include_exact_head_revision(pg_database: str) -> None:
    with PostgresAtomStore.open(pg_database, company_id=uuid.uuid4()) as store:
        first = _atom(value="first revision")
        second = _atom(value="second revision")
        store.write(first)
        assert store.list_active_hits(first.employee_id)[0].revision == 1
        store.write(second)
        hit = store.list_active_hits(second.employee_id)[0]
        assert hit.atom == second
        assert (hit.employee_id, hit.key, hit.revision) == ("agent-1", "api.retry", 2)
        assert context_result("retry", (hit,)).hits == (hit,)


def test_postgres_atom_invalidation_removes_active_head_and_keeps_history(pg_database: str) -> None:
    company_id = uuid.uuid4()
    atom = _atom()
    invalid_at = datetime(2026, 8, 11, tzinfo=UTC)
    with PostgresAtomStore.open(pg_database, company_id=company_id) as store:
        store.write(atom)
        store.invalidate(atom.employee_id, atom.key, at=invalid_at)
        store.invalidate(atom.employee_id, atom.key, at=invalid_at)
        assert store.list_active(atom.employee_id) == ()

    with psycopg.connect(pg_database) as admin:
        revisions = admin.execute(
            "SELECT version, invalid_at FROM lattice_atom_revision "
            "WHERE employee_id = %s AND key = %s ORDER BY version",
            (atom.employee_id, atom.key),
        ).fetchall()
    assert revisions == [(1, None), (2, invalid_at)]


def test_postgres_atom_identical_concurrent_writes_are_idempotent(pg_database: str) -> None:
    company_id = uuid.uuid4()
    atom = _atom()
    with (
        PostgresAtomStore.open(pg_database, company_id=company_id) as store_a,
        PostgresAtomStore.open(pg_database, company_id=company_id) as store_b,
    ):
        barrier = Barrier(2)
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = (
                executor.submit(_write_after_barrier, store_a, atom, barrier),
                executor.submit(_write_after_barrier, store_b, atom, barrier),
            )
            for future in futures:
                future.result()
        assert store_a.list_active(atom.employee_id) == (atom,)

    with psycopg.connect(pg_database) as admin:
        revisions = admin.execute(
            "SELECT version FROM lattice_atom_revision "
            "WHERE employee_id = %s AND key = %s ORDER BY version",
            (atom.employee_id, atom.key),
        ).fetchall()
        source_runs = admin.execute(
            "SELECT run_id FROM lattice_atom_revision_source_run "
            "WHERE employee_id = %s AND key = %s ORDER BY position",
            (atom.employee_id, atom.key),
        ).fetchall()
    assert revisions == [(1,)]
    assert source_runs == [("run-1",), ("run-2",)]


def test_postgres_atom_isolates_companies_with_force_rls(pg_database: str) -> None:
    app_conninfo = app_role_conninfo(pg_database)
    company_a, company_b = uuid.uuid4(), uuid.uuid4()
    atom = _atom()
    with (
        PostgresAtomStore.open(app_conninfo, company_id=company_a) as store_a,
        PostgresAtomStore.open(app_conninfo, company_id=company_b) as store_b,
    ):
        store_a.write(atom)
        assert store_a.list_active(atom.employee_id) == (atom,)
        assert store_b.list_active(atom.employee_id) == ()
        store_b.write(atom)
        assert store_a.list_active(atom.employee_id) == (atom,)
        assert store_b.list_active(atom.employee_id) == (atom,)


def _write_after_barrier(store: PostgresAtomStore, atom: Atom, barrier: Barrier) -> None:
    barrier.wait()
    store.write(atom)
