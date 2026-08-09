"""Typed context-hit result coverage."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from lattice.contracts.applied import AppliedAtomEdge, AppliedBeatOutcome, LandedOutcomePhase
from lattice.contracts.atom import Atom, ContextAtomHit
from lattice.contracts.episodic import RawEpisode
from lattice.contracts.selection import (
    ContextAtomSelection,
    ContextSelectionCaptureOutcome,
    ContextSelectionSnapshot,
)
from lattice.domain.result import (
    AppliedContextResult,
    ContextResult,
    ContextSelectionCaptureResult,
)
from lattice.facade import Lattice
from lattice.semantic.retrieve import context_result, render_context, top_k, top_k_hits
from lattice.stores import JsonCursorStore, MemoryMdStore


class _Reader:
    def records_for(self, employee_id: str) -> tuple[RawEpisode, ...]:
        return ()

    def count_for(self, employee_id: str) -> int:
        return 0


class _HitReader:
    def __init__(self, hits: tuple[ContextAtomHit, ...]) -> None:
        self._hits = hits

    def list_active_hits(self, employee_id: str) -> tuple[ContextAtomHit, ...]:
        return tuple(hit for hit in self._hits if hit.employee_id == employee_id)


class _RecordingAppliedEdges:
    def __init__(self) -> None:
        self.batches: list[tuple[AppliedAtomEdge, ...]] = []

    def record(self, edge: AppliedAtomEdge) -> None:
        self.record_all((edge,))

    def record_all(self, edges: tuple[AppliedAtomEdge, ...]) -> tuple[AppliedAtomEdge, ...]:
        self.batches.append(edges)
        return edges

    def seal(
        self,
        outcome: AppliedBeatOutcome,
        edges: tuple[AppliedAtomEdge, ...],
    ) -> tuple[AppliedAtomEdge, ...]:
        self.batches.append(edges)
        return edges

    def list_for_run(self, employee_id: str, beat_run_id: str) -> tuple[AppliedAtomEdge, ...]:
        return tuple(
            edge
            for batch in self.batches
            for edge in batch
            if edge.employee_id == employee_id and edge.beat_run_id == beat_run_id
        )


class _RecordingContextSelections:
    def __init__(self) -> None:
        self.selections: tuple[ContextAtomSelection, ...] = ()
        self.complete = True
        self.snapshots: list[ContextSelectionSnapshot] = []

    def capture(
        self,
        snapshot: ContextSelectionSnapshot,
    ) -> ContextSelectionCaptureOutcome:
        self.snapshots.append(snapshot)
        self.selections = tuple(
            sorted(
                {*self.selections, *snapshot.selections},
                key=lambda selection: (selection.key, selection.revision),
            )
        )
        self.complete = self.complete and snapshot.complete
        return ContextSelectionCaptureOutcome(
            employee_id=snapshot.employee_id,
            beat_run_id=snapshot.beat_run_id,
            selections=self.selections,
            complete=self.complete,
        )

    def list_for_run(
        self,
        employee_id: str,
        beat_run_id: str,
    ) -> tuple[ContextAtomSelection, ...]:
        return tuple(
            selection
            for selection in self.selections
            if selection.employee_id == employee_id and selection.beat_run_id == beat_run_id
        )


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
    assert lattice.capture_context_selection("e1", result, beat_run_id="beat-1") == (
        ContextSelectionCaptureResult(False, (), result.hits)
    )
    with pytest.raises(RuntimeError, match="no durable context selection journal"):
        lattice.context_selection_for_run("e1", "beat-1")

    recorded = lattice.record_landed_context(
        "e1",
        result,
        beat_run_id="beat-1",
        outcome_phase=LandedOutcomePhase.CANCELLED,
        landed_at=datetime(2026, 8, 10, tzinfo=UTC),
    )

    assert recorded == AppliedContextResult((), result.hits)


def test_record_landed_context_persists_exact_revisioned_hits_in_one_batch(tmp_path: Path) -> None:
    retry = Atom(
        key="api.retry",
        value="HTTP retries use exponential backoff capped at 30s",
        employee_id="e1",
        source_run_ids=("r1",),
        created_at=datetime(2026, 8, 9, tzinfo=UTC),
    )
    timeout = Atom(
        key="api.timeout",
        value="HTTP timeouts use the shared request deadline",
        employee_id="e1",
        source_run_ids=("r2",),
        created_at=datetime(2026, 8, 9, tzinfo=UTC),
    )
    retry_hit = ContextAtomHit(employee_id="e1", key="api.retry", revision=3, atom=retry)
    timeout_hit = ContextAtomHit(employee_id="e1", key="api.timeout", revision=4, atom=timeout)
    applied_edges = _RecordingAppliedEdges()
    context_selections = _RecordingContextSelections()
    lattice = Lattice(
        episodes=_Reader(),
        cursor=JsonCursorStore(tmp_path),
        atoms=MemoryMdStore(tmp_path),
        applied_edges=applied_edges,
        context_selections=context_selections,
    )

    context = ContextResult(markdown="", hits=(retry_hit, timeout_hit))
    result = lattice.record_landed_context(
        "e1",
        context,
        beat_run_id="beat-1",
        outcome_phase=LandedOutcomePhase.TERMINAL_FAIL,
        landed_at=datetime(2026, 8, 10, tzinfo=UTC),
    )

    expected_retry = AppliedAtomEdge(
        employee_id="e1",
        key="api.retry",
        revision=3,
        beat_run_id="beat-1",
        outcome_phase=LandedOutcomePhase.TERMINAL_FAIL,
        landed_at=datetime(2026, 8, 10, tzinfo=UTC),
    )
    expected_timeout = AppliedAtomEdge(
        employee_id="e1",
        key="api.timeout",
        revision=4,
        beat_run_id="beat-1",
        outcome_phase=LandedOutcomePhase.TERMINAL_FAIL,
        landed_at=datetime(2026, 8, 10, tzinfo=UTC),
    )
    assert result == AppliedContextResult((expected_retry, expected_timeout), ())
    assert applied_edges.batches == [(expected_retry, expected_timeout)]
    assert context_selections.snapshots == [
        ContextSelectionSnapshot(
            employee_id="e1",
            beat_run_id="beat-1",
            selections=(
                ContextAtomSelection("e1", "beat-1", "api.retry", 3),
                ContextAtomSelection("e1", "beat-1", "api.timeout", 4),
            ),
            complete=True,
        )
    ]


def test_mixed_landed_context_is_captured_incomplete_and_not_sealed(tmp_path: Path) -> None:
    versioned_atom = Atom(
        key="api.retry",
        value="Retry with backoff",
        employee_id="e1",
        source_run_ids=("r1",),
        created_at=datetime(2026, 8, 9, tzinfo=UTC),
    )
    legacy_atom = Atom(
        key="api.legacy",
        value="Legacy memory",
        employee_id="e1",
        source_run_ids=("r2",),
        created_at=datetime(2026, 8, 9, tzinfo=UTC),
    )
    context = ContextResult(
        markdown="",
        hits=(
            ContextAtomHit("e1", "api.retry", 3, versioned_atom),
            ContextAtomHit("e1", "api.legacy", None, legacy_atom),
        ),
    )
    applied_edges = _RecordingAppliedEdges()
    context_selections = _RecordingContextSelections()
    lattice = Lattice(
        episodes=_Reader(),
        cursor=JsonCursorStore(tmp_path),
        atoms=MemoryMdStore(tmp_path),
        applied_edges=applied_edges,
        context_selections=context_selections,
    )

    with pytest.raises(RuntimeError, match="cannot be sealed"):
        lattice.record_landed_context(
            "e1",
            context,
            beat_run_id="beat-mixed",
            outcome_phase=LandedOutcomePhase.TERMINAL_FAIL,
            landed_at=datetime(2026, 8, 10, tzinfo=UTC),
        )

    assert applied_edges.batches == []
    assert context_selections.snapshots[0].complete is False
    assert context_selections.snapshots[0].selections == (
        ContextAtomSelection("e1", "beat-mixed", "api.retry", 3),
    )


def test_record_landed_context_requires_a_store_for_revisioned_hits(tmp_path: Path) -> None:
    atom = Atom(
        key="api.retry",
        value="HTTP retries use exponential backoff capped at 30s",
        employee_id="e1",
        source_run_ids=("r1",),
        created_at=datetime(2026, 8, 9, tzinfo=UTC),
    )
    hit = ContextAtomHit(employee_id="e1", key="api.retry", revision=3, atom=atom)
    lattice = Lattice(
        episodes=_Reader(),
        cursor=JsonCursorStore(tmp_path),
        atoms=MemoryMdStore(tmp_path),
        atom_hits=_HitReader((hit,)),
    )

    with pytest.raises(RuntimeError, match="AppliedEdgeStore"):
        lattice.record_landed_context(
            "e1",
            lattice.context_result("e1", "retry"),
            beat_run_id="beat-1",
            outcome_phase=LandedOutcomePhase.TERMINAL_PASS,
            landed_at=datetime(2026, 8, 10, tzinfo=UTC),
        )


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
