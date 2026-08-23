"""Real-Postgres coverage for the derived MEMORY.md view."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from tests.integration.conftest import _GrowingReader, make_episode, valid_retry_proposal

from lattice.contracts.atom import Atom, AtomStore
from lattice.domain.stats import PatternStats, Tier
from lattice.facade import Lattice
from lattice.stores import MemoryMdView
from lattice.stores.memory_md import render_memory_md
from lattice.stores.postgres import PostgresLatticeStore


def _atom(
    *,
    key: str = "api.retry",
    value: str = "HTTP retries use capped exponential backoff",
) -> Atom:
    return Atom(
        key=key,
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


def test_postgres_memory_view_defers_rewrite_until_apply_scope_commits(
    pg_database: str, tmp_path: Path
) -> None:
    with PostgresLatticeStore.open(pg_database, company_id=uuid.uuid4()) as store:
        view = MemoryMdView(store.atoms, tmp_path, transaction_scope=store.apply_scope)
        memory_md = tmp_path / "e_be_1" / "MEMORY.md"
        with view.apply_scope("e_be_1"):
            view.write(_atom())
            assert not memory_md.exists()
        assert memory_md.read_text(encoding="utf-8") == render_memory_md(store.atoms.list_active("e_be_1"))


def test_postgres_apply_renders_memory_view_after_atom_and_cursor_commit(
    pg_database: str, tmp_path: Path
) -> None:
    reader = _GrowingReader(
        [make_episode(run_id=f"r_b{index}", offset_minutes=index) for index in range(1, 6)]
    )
    with PostgresLatticeStore.open(pg_database, company_id=uuid.uuid4()) as store:
        view = MemoryMdView(store.atoms, tmp_path, transaction_scope=store.apply_scope)
        lattice = Lattice(episodes=reader, atoms=view, cursor=store.cursor, apply_scope=view.apply_scope)
        assert lattice.apply(
            valid_retry_proposal(run_ids=("r_b1", "r_b2", "r_b3", "r_b4", "r_b5"))
        ).ok is True
        assert store.cursor.get("e_be_1").episodes_seen == 5
        assert (tmp_path / "e_be_1" / "MEMORY.md").read_text(encoding="utf-8") == render_memory_md(
            store.atoms.list_active("e_be_1")
        )


def test_postgres_memory_view_keeps_prior_view_when_apply_rolls_back(
    pg_database: str, tmp_path: Path
) -> None:
    reader = _GrowingReader(
        [make_episode(run_id=f"r_b{index}", offset_minutes=index) for index in range(1, 6)]
    )
    with PostgresLatticeStore.open(pg_database, company_id=uuid.uuid4()) as store:
        view = MemoryMdView(store.atoms, tmp_path, transaction_scope=store.apply_scope)
        original = _atom(key="api.original", value="original authoritative atom")
        view.write(original)
        before = (tmp_path / "e_be_1" / "MEMORY.md").read_text(encoding="utf-8")
        lattice = Lattice(
            episodes=reader,
            atoms=_FailingAfterWrite(view),
            cursor=store.cursor,
            apply_scope=view.apply_scope,
        )
        with pytest.raises(RuntimeError, match="forced failure"):
            lattice.apply(
                valid_retry_proposal(run_ids=("r_b1", "r_b2", "r_b3", "r_b4", "r_b5"))
            )
        assert store.atoms.list_active("e_be_1") == (original,)
        assert store.cursor.get("e_be_1").episodes_seen == 0
        assert (tmp_path / "e_be_1" / "MEMORY.md").read_text(encoding="utf-8") == before


def test_postgres_memory_view_surfaces_renderer_failures(pg_database: str, tmp_path: Path) -> None:
    (tmp_path / "e_be_1").write_text("not a directory", encoding="utf-8")
    with PostgresLatticeStore.open(pg_database, company_id=uuid.uuid4()) as store:
        view = MemoryMdView(store.atoms, tmp_path, transaction_scope=store.apply_scope)
        with pytest.raises(FileExistsError):
            with view.apply_scope("e_be_1"):
                view.write(_atom())
        assert store.atoms.list_active("e_be_1") == (_atom(),)


class _FailingAfterWrite:
    def __init__(self, atoms: AtomStore) -> None:
        self._atoms = atoms

    def list_active(self, employee_id: str) -> tuple[Atom, ...]:
        return self._atoms.list_active(employee_id)

    def write(self, atom: Atom) -> None:
        self._atoms.write(atom)
        raise RuntimeError("forced failure after atom write")

    def invalidate(self, employee_id: str, key: str, *, at: datetime) -> None:
        self._atoms.invalidate(employee_id, key, at=at)
