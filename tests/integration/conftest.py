"""Shared fixtures for lattice integration / E2E tests."""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg
import pytest

from lattice.compose import build_default
from lattice.contracts.episodic import RawEpisode
from lattice.domain.proposal import PatternDraft, Proposal
from lattice.facade import Lattice
from lattice.migrations import load_migrations

_PG_BIN = Path(os.environ.get("LATTICE_PG_BIN", "/opt/homebrew/opt/postgresql@18/bin"))


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="session")
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
    database = f"lattice_test_{uuid.uuid4().hex}"
    with psycopg.connect(pg_conninfo, autocommit=True) as admin:
        admin.execute(f"CREATE DATABASE {database}")
    conninfo = pg_conninfo.replace("dbname=postgres", f"dbname={database}")
    with psycopg.connect(conninfo, autocommit=True) as admin:
        for migration in load_migrations():
            admin.execute(migration.sql)
    try:
        yield conninfo
    finally:
        with psycopg.connect(pg_conninfo, autocommit=True) as admin:
            admin.execute(f"DROP DATABASE IF EXISTS {database} WITH (FORCE)")


def app_role_conninfo(conninfo: str) -> str:
    """Create a non-superuser role so FORCE RLS is exercised in store tests."""
    with psycopg.connect(conninfo, autocommit=True) as admin:
        admin.execute(
            "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'lattice_app') "
            "THEN CREATE ROLE lattice_app LOGIN NOSUPERUSER NOBYPASSRLS; END IF; END $$"
        )
        admin.execute("GRANT USAGE ON SCHEMA public TO lattice_app")
        admin.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO lattice_app")
    return conninfo.replace("user=postgres", "user=lattice_app")


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
