"""Real-Postgres conformance tests for consolidation cursor persistence."""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import uuid
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest

from lattice.contracts.cursor import ConsolidationWatermark, CursorStore
from lattice.migrations import load_migrations
from lattice.stores.postgres_cursor import PostgresCursorStore

_PG_BIN = Path(os.environ.get("LATTICE_PG_BIN", "/opt/homebrew/opt/postgresql@18/bin"))


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="module")
def pg_conninfo(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    if not _PG_BIN.exists():
        pytest.skip(f"PostgreSQL 18 not found at {_PG_BIN} (set LATTICE_PG_BIN)")
    data = tmp_path_factory.mktemp("lattice_cursor_pgdata")
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
    database = f"lattice_cursors_{uuid.uuid4().hex}"
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


def test_postgres_cursor_returns_empty_watermark(pg_database: str) -> None:
    with PostgresCursorStore.open(pg_database, company_id=uuid.uuid4()) as store:
        typed_store: CursorStore = store
        assert typed_store.get("agent-1") == ConsolidationWatermark(
            employee_id="agent-1",
            last_run_id=None,
            episodes_seen=0,
            consolidated_at=None,
        )


def test_postgres_cursor_advance_survives_restart(pg_database: str) -> None:
    company_id = uuid.uuid4()
    with PostgresCursorStore.open(pg_database, company_id=company_id) as store:
        store.advance("agent-1", last_run_id="run-5", episodes_seen=5)
        first = store.get("agent-1")
        assert first.last_run_id == "run-5"
        assert first.episodes_seen == 5
        assert first.consolidated_at is not None

    with PostgresCursorStore.open(pg_database, company_id=company_id) as restarted:
        assert restarted.get("agent-1") == first


def test_postgres_cursor_exact_retry_is_a_noop(pg_database: str) -> None:
    with PostgresCursorStore.open(pg_database, company_id=uuid.uuid4()) as store:
        store.advance("agent-1", last_run_id="run-5", episodes_seen=5)
        first = store.get("agent-1")
        store.advance("agent-1", last_run_id="run-5", episodes_seen=5)
        assert store.get("agent-1") == first


def test_postgres_cursor_stale_advance_cannot_move_backward(pg_database: str) -> None:
    with PostgresCursorStore.open(pg_database, company_id=uuid.uuid4()) as store:
        store.advance("agent-1", last_run_id="run-5", episodes_seen=5)
        first = store.get("agent-1")
        store.advance("agent-1", last_run_id="run-3", episodes_seen=3)
        assert store.get("agent-1") == first


def test_postgres_cursor_isolates_companies_with_force_rls(pg_database: str) -> None:
    app_conninfo = _app_role_conninfo(pg_database)
    with (
        PostgresCursorStore.open(app_conninfo, company_id=uuid.uuid4()) as store_a,
        PostgresCursorStore.open(app_conninfo, company_id=uuid.uuid4()) as store_b,
    ):
        store_a.advance("agent-1", last_run_id="run-a", episodes_seen=5)
        assert store_a.get("agent-1").last_run_id == "run-a"
        assert store_b.get("agent-1").episodes_seen == 0
        store_b.advance("agent-1", last_run_id="run-b", episodes_seen=3)
        assert store_a.get("agent-1").last_run_id == "run-a"
        assert store_b.get("agent-1").last_run_id == "run-b"


def _app_role_conninfo(conninfo: str) -> str:
    with psycopg.connect(conninfo, autocommit=True) as admin:
        admin.execute(
            "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'lattice_app') "
            "THEN CREATE ROLE lattice_app LOGIN NOSUPERUSER NOBYPASSRLS; END IF; END $$"
        )
        admin.execute("GRANT USAGE ON SCHEMA public TO lattice_app")
        admin.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO lattice_app")
    return conninfo.replace("user=postgres", "user=lattice_app")
