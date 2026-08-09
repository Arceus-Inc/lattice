"""Real-Postgres coverage for the derived MEMORY.md view."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from tests.integration.conftest import _GrowingReader, make_episode

from lattice.contracts.atom import Atom
from lattice.domain.stats import PatternStats, Tier
from lattice.facade import Lattice
from lattice.stores import MemoryMdView
from lattice.stores.memory_md import render_memory_md
from lattice.stores.postgres import PostgresLatticeStore


def _atom(*, value: str = "HTTP retries use capped exponential backoff") -> Atom:
    return Atom(
        key="api.retry",
        value=value,
        employee_id="e_be_1",
        source_run_ids=("r1",),
        created_at=datetime(2026, 8, 9, tzinfo=UTC),
        stats=PatternStats(alpha_own=3.5, beta_own=1.5, tier=Tier.RULE),
        key_files=("src/api/client.py",),
    )


def test_postgres_memory_view_rewrites_from_authoritative_atoms_after_restart(
    pg_database: str, tmp_path: Path
) -> None:
    company_id = uuid.uuid4()
    with PostgresLatticeStore.open(pg_database, company_id=company_id) as store:
        view = MemoryMdView(store.atoms, tmp_path)
        view.write(_atom())
        expected = (tmp_path / "e_be_1" / "MEMORY.md").read_text(encoding="utf-8")
        assert expected == render_memory_md(store.atoms.list_active("e_be_1"))
        assert not (tmp_path / "e_be_1" / "semantic").exists()

    with PostgresLatticeStore.open(pg_database, company_id=company_id) as restarted:
        MemoryMdView(restarted.atoms, tmp_path).rewrite("e_be_1")
        assert (tmp_path / "e_be_1" / "MEMORY.md").read_text(encoding="utf-8") == expected


def test_postgres_memory_view_rewrites_after_invalidation(pg_database: str, tmp_path: Path) -> None:
    with PostgresLatticeStore.open(pg_database, company_id=uuid.uuid4()) as store:
        view = MemoryMdView(store.atoms, tmp_path)
        view.write(_atom())
        view.invalidate("e_be_1", "api.retry", at=datetime(2026, 8, 10, tzinfo=UTC))
        assert store.atoms.list_active("e_be_1") == ()
        assert (tmp_path / "e_be_1" / "MEMORY.md").read_text(encoding="utf-8") == "# MEMORY\n\n"


def test_postgres_memory_view_rewrites_for_adjudicate_and_forget(
    pg_database: str, tmp_path: Path
) -> None:
    reader = _GrowingReader([make_episode(run_id="r2")])
    with PostgresLatticeStore.open(pg_database, company_id=uuid.uuid4()) as store:
        view = MemoryMdView(store.atoms, tmp_path)
        view.write(_atom())
        lattice = Lattice(episodes=reader, atoms=view, cursor=store.cursor)
        before = (tmp_path / "e_be_1" / "MEMORY.md").read_text(encoding="utf-8")
        lattice.adjudicate("e_be_1")
        adjudicated = (tmp_path / "e_be_1" / "MEMORY.md").read_text(encoding="utf-8")
        adjudicated_atoms = store.atoms.list_active("e_be_1")
        lattice.forget("e_be_1")
        forgotten = (tmp_path / "e_be_1" / "MEMORY.md").read_text(encoding="utf-8")
        assert before != adjudicated
        assert adjudicated_atoms[0].stats != _atom().stats
        assert adjudicated == render_memory_md(adjudicated_atoms)
        forgotten_atoms = store.atoms.list_active("e_be_1")
        assert forgotten_atoms[0].stats != adjudicated_atoms[0].stats
        assert forgotten == render_memory_md(forgotten_atoms)


def test_postgres_memory_view_surfaces_renderer_failures(pg_database: str, tmp_path: Path) -> None:
    (tmp_path / "e_be_1").write_text("not a directory", encoding="utf-8")
    with PostgresLatticeStore.open(pg_database, company_id=uuid.uuid4()) as store:
        view = MemoryMdView(store.atoms, tmp_path)
        with pytest.raises(FileExistsError):
            view.write(_atom())
        assert store.atoms.list_active("e_be_1") == (_atom(),)
