"""Typed context-hit result coverage."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from lattice.contracts.atom import Atom, ContextAtomHit
from lattice.contracts.episodic import RawEpisode
from lattice.facade import Lattice
from lattice.semantic.retrieve import context_result, render_context, top_k, top_k_hits
from lattice.stores import JsonCursorStore, MemoryMdStore


class _Reader:
    def records_for(self, employee_id: str) -> tuple[RawEpisode, ...]:
        return ()

    def count_for(self, employee_id: str) -> int:
        return 0


def test_file_context_result_has_honest_unversioned_hit(tmp_path: Path) -> None:
    atoms = MemoryMdStore(tmp_path)
    atom = Atom(
        key="api.retry",
        value="HTTP retries use exponential backoff capped at 30s",
        employee_id="e1",
        source_run_ids=("r1",),
        created_at=datetime(2026, 8, 9, tzinfo=UTC),
    )
    atoms.write(atom)
    lattice = Lattice(episodes=_Reader(), cursor=JsonCursorStore(tmp_path), atoms=atoms)

    result = lattice.context_result("e1", "retry")

    assert len(result.hits) == 1
    assert result.hits[0].atom == atom
    assert result.hits[0].employee_id == "e1"
    assert result.hits[0].key == "api.retry"
    assert result.hits[0].revision is None
    assert lattice.context("e1", "retry") == result.markdown


def test_legacy_and_typed_context_retrieval_have_identical_ranking_and_markdown() -> None:
    atoms = (
        Atom(
            key="api.retry",
            value="HTTP retries use exponential backoff capped at 30s",
            employee_id="e1",
            source_run_ids=("r1",),
            created_at=datetime(2026, 8, 9, tzinfo=UTC),
        ),
        Atom(
            key="ui.theme",
            value="Dark mode uses CSS variables in the theme stylesheet",
            employee_id="e1",
            source_run_ids=("r2",),
            created_at=datetime(2026, 8, 8, tzinfo=UTC),
        ),
    )
    hits = tuple(
        ContextAtomHit(employee_id=atom.employee_id, key=atom.key, revision=None, atom=atom)
        for atom in atoms
    )

    typed = context_result("retry HTTP", hits)

    assert tuple(hit.atom for hit in top_k_hits("retry HTTP", hits)) == top_k("retry HTTP", atoms)
    assert typed.markdown == render_context("retry HTTP", atoms)
