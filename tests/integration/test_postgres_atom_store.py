"""Real-Postgres conformance tests for the semantic atom store."""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import psycopg
import pytest

from lattice.contracts.atom import Atom, AtomStore
from lattice.domain.stats import PatternStats, Tier
from lattice.migrations import load_migrations
from lattice.stores.postgres_atoms import PostgresAtomStore

_PG_BIN = Path(os.environ.get("LATTICE_PG_BIN", "/opt/homebrew/opt/postgresql@18/bin"))


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="module")
def pg_conninfo(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    if not _PG_BIN.exists():
        pytest.skip(f"PostgreSQL 18 not found at {_PG_BIN} (set LATTICE_PG_BIN)")
    data = tmp_path_factory.mktemp("lattice_pgdata")
    env = {**os.environ, "LC_ALL": "C"}
    subprocess.run(
        [
            str(_PG_BIN / "initdb"),
            "-D",
            str(data),
            "-U",
            "postgres",
            "--auth=trust",
            "--encoding=UTF8",
            "--locale=C",
        ],
        check=True,
        capture_output=True,
        env=env,
    )
    port = _free_port()
    subprocess.run(
        [
            str(_PG_BIN / "pg_ctl"),
            "-D",
            str(data),
            "-o",
            f"-p {port} -c listen_addresses=127.0.0.1 "
            "-c fsync=off -c unix_socket_directories=/tmp",
            "-l",
            str(data / "log"),
            "-w",
            "start",
        ],
        check=True,
        capture_output=True,
        env=env,
    )
    try:
        yield f"host=127.0.0.1 port={port} user=postgres dbname=postgres"
    finally:
        subprocess.run(
            [str(_PG_BIN / "pg_ctl"), "-D", str(data), "-w", "stop"],
            check=True,
            capture_output=True,
            env=env,
        )
        shutil.rmtree(data, ignore_errors=True)


@pytest.fixture
def pg_database(pg_conninfo: str) -> Iterator[str]:
    database = f"lattice_atoms_{uuid.uuid4().hex}"
    with psycopg.connect(pg_conninfo, autocommit=True) as admin:
        admin.execute(f"CREATE DATABASE {database}")
    conninfo = pg_conninfo.replace("dbname=postgres", f"dbname={database}")
    _apply_migrations(conninfo)
    try:
        yield conninfo
    finally:
        with psycopg.connect(pg_conninfo, autocommit=True) as admin:
            admin.execute(f"DROP DATABASE IF EXISTS {database} WITH (FORCE)")


def _apply_migrations(conninfo: str) -> None:
    with psycopg.connect(conninfo, autocommit=True) as admin:
        for migration in load_migrations():
            admin.execute(migration.sql)


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
    company_id = str(uuid.uuid4())
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
    company_id = str(uuid.uuid4())
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


def test_postgres_atom_invalidation_removes_active_head_and_keeps_history(pg_database: str) -> None:
    company_id = str(uuid.uuid4())
    atom = _atom()
    invalid_at = datetime(2026, 8, 11, tzinfo=UTC)
    with PostgresAtomStore.open(pg_database, company_id=company_id) as store:
        store.write(atom)
        store.invalidate(atom.employee_id, atom.key, at=invalid_at)
        assert store.list_active(atom.employee_id) == ()

    with psycopg.connect(pg_database) as admin:
        revisions = admin.execute(
            "SELECT version, invalid_at FROM lattice_atom_revision "
            "WHERE employee_id = %s AND key = %s ORDER BY version",
            (atom.employee_id, atom.key),
        ).fetchall()
    assert revisions[0] == (1, None)
    assert revisions[1] == (2, invalid_at)


def test_postgres_atom_isolates_companies_with_force_rls(pg_database: str) -> None:
    app_conninfo = _app_role_conninfo(pg_database)
    company_a, company_b = str(uuid.uuid4()), str(uuid.uuid4())
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


def _app_role_conninfo(conninfo: str) -> str:
    with psycopg.connect(conninfo, autocommit=True) as admin:
        admin.execute(
            "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'lattice_app') "
            "THEN CREATE ROLE lattice_app LOGIN NOSUPERUSER NOBYPASSRLS; END IF; END $$"
        )
        admin.execute("GRANT USAGE ON SCHEMA public TO lattice_app")
        admin.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO lattice_app")
    return conninfo.replace("user=postgres", "user=lattice_app")
