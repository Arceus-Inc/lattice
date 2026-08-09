"""Real-Postgres conformance tests for immutable APPLIED atom outcome edges."""

from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta, timezone
from threading import Barrier

import psycopg
import pytest
from psycopg.errors import ForeignKeyViolation, ObjectNotInPrerequisiteState
from tests.integration.conftest import _GrowingReader, app_role_conninfo

from lattice.contracts.applied import AppliedAtomEdge, AppliedEdgeConflictError, LandedOutcomePhase
from lattice.contracts.atom import Atom, ContextAtomHit
from lattice.contracts.selection import ContextAtomSelection
from lattice.stores.postgres import PostgresLatticeStore
from lattice.stores.postgres_applied_edges import PostgresAppliedEdgeStore
from lattice.stores.postgres_atoms import PostgresAtomStore
from lattice.stores.postgres_context_selections import PostgresContextSelectionJournal


def _atom(*, key: str = "api.retry", value: str = "retry with capped exponential backoff") -> Atom:
    return Atom(
        employee_id="agent-1",
        key=key,
        value=value,
        source_run_ids=("run-source",),
        created_at=datetime(2026, 8, 9, tzinfo=UTC),
    )


def _edge(
    hit: ContextAtomHit,
    *,
    beat_run_id: str = "run-landing",
    outcome_phase: LandedOutcomePhase = LandedOutcomePhase.TERMINAL_PASS,
    landed_at: datetime = datetime(2026, 8, 10, tzinfo=UTC),
) -> AppliedAtomEdge:
    if hit.revision is None:
        raise AssertionError("Postgres hit must have an exact revision")
    return AppliedAtomEdge(
        employee_id=hit.employee_id,
        key=hit.key,
        revision=hit.revision,
        beat_run_id=beat_run_id,
        outcome_phase=outcome_phase,
        landed_at=landed_at,
    )


def _selection(edge: AppliedAtomEdge) -> ContextAtomSelection:
    return ContextAtomSelection(
        employee_id=edge.employee_id,
        beat_run_id=edge.beat_run_id,
        key=edge.key,
        revision=edge.revision,
    )


def _capture(
    conninfo: str,
    company_id: uuid.UUID,
    edges: tuple[AppliedAtomEdge, ...],
) -> None:
    with PostgresContextSelectionJournal.open(conninfo, company_id=company_id) as selections:
        selections.append_all(tuple(_selection(edge) for edge in edges))


def test_postgres_applied_edges_survive_restart_and_allow_multiple_atoms_per_beat(
    pg_database: str,
) -> None:
    company_id = uuid.uuid4()
    with PostgresAtomStore.open(pg_database, company_id=company_id) as atoms:
        atoms.write(_atom(key="api.retry"))
        atoms.write(_atom(key="api.timeout"))
        retry_hit, timeout_hit = atoms.list_active_hits("agent-1")
    expected = (_edge(retry_hit), _edge(timeout_hit))
    _capture(pg_database, company_id, expected)
    with PostgresAppliedEdgeStore.open(pg_database, company_id=company_id) as edges:
        assert edges.record_all(tuple(reversed(expected))) == expected
        assert edges.list_for_run("agent-1", "run-landing") == expected

    with PostgresAppliedEdgeStore.open(pg_database, company_id=company_id) as restarted:
        assert restarted.list_for_run("agent-1", "run-landing") == expected


def test_postgres_applied_edges_round_trip_terminal_failure(pg_database: str) -> None:
    company_id = uuid.uuid4()
    with PostgresAtomStore.open(pg_database, company_id=company_id) as atoms:
        atoms.write(_atom())
        edge = _edge(
            atoms.list_active_hits("agent-1")[0],
            beat_run_id="run-failure",
            outcome_phase=LandedOutcomePhase.TERMINAL_FAIL,
        )
    with PostgresAppliedEdgeStore.open(pg_database, company_id=company_id) as edges:
        _capture(pg_database, company_id, (edge,))
        edges.record(edge)
        assert edges.list_for_run("agent-1", "run-failure") == (edge,)


def test_postgres_applied_edge_replay_is_idempotent_and_conflicts_on_different_outcome(
    pg_database: str,
) -> None:
    company_id = uuid.uuid4()
    with PostgresAtomStore.open(pg_database, company_id=company_id) as atoms:
        atoms.write(_atom())
        edge = _edge(atoms.list_active_hits("agent-1")[0])
    with PostgresAppliedEdgeStore.open(pg_database, company_id=company_id) as edges:
        _capture(pg_database, company_id, (edge,))
        assert edges.record_all((edge,)) == (edge,)
        assert edges.record_all((edge,)) == (edge,)
        conflicting = AppliedAtomEdge(
            employee_id=edge.employee_id,
            key=edge.key,
            revision=edge.revision,
            beat_run_id=edge.beat_run_id,
            outcome_phase=LandedOutcomePhase.TERMINAL_FAIL,
            landed_at=edge.landed_at,
        )
        with pytest.raises(AppliedEdgeConflictError):
            edges.record(conflicting)
        assert edges.list_for_run("agent-1", "run-landing") == (edge,)


def test_postgres_applied_beat_rejects_subset_and_superset_replays(pg_database: str) -> None:
    company_id = uuid.uuid4()
    with PostgresAtomStore.open(pg_database, company_id=company_id) as atoms:
        atoms.write(_atom(key="api.retry"))
        atoms.write(_atom(key="api.timeout"))
        atoms.write(_atom(key="api.circuit_breaker"))
        circuit_hit, retry_hit, timeout_hit = atoms.list_active_hits("agent-1")
    original = (_edge(retry_hit), _edge(timeout_hit))
    superset = (_edge(circuit_hit), *original)
    _capture(pg_database, company_id, original)
    with PostgresAppliedEdgeStore.open(pg_database, company_id=company_id) as edges:
        assert edges.record_all(original) == original
        with pytest.raises(AppliedEdgeConflictError):
            edges.record_all((original[0],))
        with pytest.raises(AppliedEdgeConflictError):
            edges.record_all(superset)
        assert edges.list_for_run("agent-1", "run-landing") == original


def test_postgres_applied_beat_rejects_mixed_phase_and_landed_time(pg_database: str) -> None:
    company_id = uuid.uuid4()
    with PostgresAtomStore.open(pg_database, company_id=company_id) as atoms:
        atoms.write(_atom(key="api.retry"))
        atoms.write(_atom(key="api.timeout"))
        retry_hit, timeout_hit = atoms.list_active_hits("agent-1")
    retry = _edge(retry_hit)
    with PostgresAppliedEdgeStore.open(pg_database, company_id=company_id) as edges:
        with pytest.raises(AppliedEdgeConflictError):
            edges.record_all(
                (
                    retry,
                    _edge(timeout_hit, outcome_phase=LandedOutcomePhase.NEEDS_REWORK),
                )
            )
        with pytest.raises(AppliedEdgeConflictError):
            edges.record_all(
                (
                    retry,
                    _edge(timeout_hit, landed_at=retry.landed_at + timedelta(seconds=1)),
                )
            )
        assert edges.list_for_run("agent-1", "run-landing") == ()


def test_postgres_applied_beat_serializes_concurrent_conflicting_replays(
    pg_database: str,
) -> None:
    company_id = uuid.uuid4()
    with PostgresAtomStore.open(pg_database, company_id=company_id) as atoms:
        atoms.write(_atom(key="api.retry"))
        atoms.write(_atom(key="api.timeout"))
        retry_hit, timeout_hit = atoms.list_active_hits("agent-1")
    subset = (_edge(retry_hit),)
    superset = (*subset, _edge(timeout_hit))
    _capture(pg_database, company_id, subset)
    barrier = Barrier(2)
    with (
        PostgresAppliedEdgeStore.open(pg_database, company_id=company_id) as first,
        PostgresAppliedEdgeStore.open(pg_database, company_id=company_id) as second,
        ThreadPoolExecutor(max_workers=2) as executor,
    ):
        first_result = executor.submit(_record_after_barrier, first, subset, barrier)
        second_result = executor.submit(_record_after_barrier, second, superset, barrier)
        assert sorted((first_result.result(), second_result.result())) == ["conflict", "stored"]
        persisted = first.list_for_run("agent-1", "run-landing")
        assert persisted == subset


def test_postgres_applied_edge_batch_rolls_back_when_it_diverges_from_the_journal(
    pg_database: str,
) -> None:
    company_id = uuid.uuid4()
    with PostgresAtomStore.open(pg_database, company_id=company_id) as atoms:
        atoms.write(_atom())
        edge = _edge(atoms.list_active_hits("agent-1")[0])
    invalid = AppliedAtomEdge(
        employee_id=edge.employee_id,
        key=edge.key,
        revision=edge.revision + 1,
        beat_run_id=edge.beat_run_id,
        outcome_phase=edge.outcome_phase,
        landed_at=edge.landed_at,
    )
    _capture(pg_database, company_id, (edge,))
    with PostgresAppliedEdgeStore.open(pg_database, company_id=company_id) as edges:
        with pytest.raises(AppliedEdgeConflictError):
            edges.record_all((edge, invalid))
        assert edges.list_for_run("agent-1", "run-landing") == ()


def test_canonical_postgres_composition_records_revisioned_context_across_restart(
    pg_database: str,
) -> None:
    company_id = uuid.uuid4()
    landed_at = datetime(2026, 8, 10, tzinfo=UTC)
    with PostgresLatticeStore.open(pg_database, company_id=company_id) as store:
        store.atoms.write(_atom())
        lattice = store.build_lattice(episodes=_GrowingReader([]))

        context = lattice.context_result("agent-1", "retry")

        assert len(context.hits) == 1
        assert context.hits[0].revision == 1
        capture = lattice.capture_context_selection(
            "agent-1",
            context,
            beat_run_id="run-canonical",
        )
        assert capture.durable is True
        assert store.applied_edges.list_for_run("agent-1", "run-canonical") == ()

    with PostgresLatticeStore.open(pg_database, company_id=company_id) as restarted:
        lattice = restarted.build_lattice(episodes=_GrowingReader([]))
        assert lattice.context_result("agent-1", "retry").hits[0].revision == 1
        assert lattice.context_selection_for_run("agent-1", "run-canonical") == capture.selections
        recorded = lattice.record_landed_selection(
            "agent-1",
            "run-canonical",
            outcome_phase=LandedOutcomePhase.NEEDS_REWORK,
            landed_at=landed_at,
        )
        assert restarted.applied_edges.list_for_run("agent-1", "run-canonical") == recorded


def test_postgres_context_selection_requires_an_exact_atom_revision(pg_database: str) -> None:
    selection = ContextAtomSelection(
        employee_id="agent-1",
        key="api.retry",
        revision=1,
        beat_run_id="run-landing",
    )
    with PostgresContextSelectionJournal.open(pg_database, company_id=uuid.uuid4()) as selections:
        with pytest.raises(ForeignKeyViolation):
            selections.append_all((selection,))


def test_applied_edge_requires_a_timezone_aware_utc_landed_at() -> None:
    base = dict(
        employee_id="agent-1",
        key="api.retry",
        revision=1,
        beat_run_id="run-landing",
        outcome_phase=LandedOutcomePhase.NEEDS_REWORK,
    )

    with pytest.raises(ValueError, match="timezone-aware UTC"):
        AppliedAtomEdge(landed_at=datetime(2026, 8, 10), **base)
    with pytest.raises(ValueError, match="timezone-aware UTC"):
        AppliedAtomEdge(landed_at=datetime(2026, 8, 10, tzinfo=timezone(timedelta(hours=1))), **base)


def test_landed_outcome_phase_has_the_closed_cross_repo_phase_values() -> None:
    assert {phase.value for phase in LandedOutcomePhase} == {
        "cancelled",
        "delegated",
        "terminal_pass",
        "terminal_fail",
        "needs_rework",
        "stranded",
    }


def test_postgres_applied_edges_remain_valid_after_atom_invalidation(pg_database: str) -> None:
    company_id = uuid.uuid4()
    atom = _atom()
    with PostgresAtomStore.open(pg_database, company_id=company_id) as atoms:
        atoms.write(atom)
        edge = _edge(atoms.list_active_hits("agent-1")[0])
        _capture(pg_database, company_id, (edge,))
        atoms.invalidate("agent-1", "api.retry", at=datetime(2026, 8, 11, tzinfo=UTC))
    with PostgresAppliedEdgeStore.open(pg_database, company_id=company_id) as edges:
        edges.record(edge)
        assert edges.list_for_run("agent-1", "run-landing") == (edge,)


def test_postgres_applied_edges_obey_company_force_rls(pg_database: str) -> None:
    app_conninfo = app_role_conninfo(pg_database)
    company_a, company_b = uuid.uuid4(), uuid.uuid4()
    with (
        PostgresAtomStore.open(app_conninfo, company_id=company_a) as atoms_a,
        PostgresAtomStore.open(app_conninfo, company_id=company_b) as atoms_b,
    ):
        atoms_a.write(_atom(value="company a"))
        atoms_b.write(_atom(value="company b"))
        edge_a = _edge(atoms_a.list_active_hits("agent-1")[0])
        edge_b = _edge(atoms_b.list_active_hits("agent-1")[0])
    _capture(app_conninfo, company_a, (edge_a,))
    _capture(app_conninfo, company_b, (edge_b,))
    with (
        PostgresAppliedEdgeStore.open(app_conninfo, company_id=company_a) as edges_a,
        PostgresAppliedEdgeStore.open(app_conninfo, company_id=company_b) as edges_b,
    ):
        edges_a.record(edge_a)
        edges_b.record(edge_b)
        assert edges_a.list_for_run("agent-1", "run-landing") == (edge_a,)
        assert edges_b.list_for_run("agent-1", "run-landing") == (edge_b,)


def test_postgres_applied_edges_reject_update_and_delete_for_the_runtime_role(
    pg_database: str,
) -> None:
    app_conninfo = app_role_conninfo(pg_database)
    company_id = uuid.uuid4()
    with PostgresAtomStore.open(app_conninfo, company_id=company_id) as atoms:
        atoms.write(_atom())
        edge = _edge(atoms.list_active_hits("agent-1")[0])
    _capture(app_conninfo, company_id, (edge,))
    with PostgresAppliedEdgeStore.open(app_conninfo, company_id=company_id) as edges:
        edges.record(edge)

    with psycopg.connect(app_conninfo, autocommit=True) as connection:
        connection.execute("SELECT set_config('app.company_id', %s, false)", (str(company_id),))
        with pytest.raises(ObjectNotInPrerequisiteState):
            connection.execute(
                "UPDATE lattice_atom_applied_edge SET landed_at = landed_at "
                "WHERE employee_id = %s AND key = %s AND revision = %s AND beat_run_id = %s",
                (edge.employee_id, edge.key, edge.revision, edge.beat_run_id),
            )
        with pytest.raises(ObjectNotInPrerequisiteState):
            connection.execute(
                "DELETE FROM lattice_atom_applied_edge "
                "WHERE employee_id = %s AND key = %s AND revision = %s AND beat_run_id = %s",
                (edge.employee_id, edge.key, edge.revision, edge.beat_run_id),
            )
        with pytest.raises(ObjectNotInPrerequisiteState):
            connection.execute(
                "UPDATE lattice_atom_applied_beat SET selected_count = selected_count "
                "WHERE employee_id = %s AND beat_run_id = %s",
                (edge.employee_id, edge.beat_run_id),
            )
        with pytest.raises(ObjectNotInPrerequisiteState):
            connection.execute(
                "DELETE FROM lattice_atom_applied_beat "
                "WHERE employee_id = %s AND beat_run_id = %s",
                (edge.employee_id, edge.beat_run_id),
            )


def _record_after_barrier(
    store: PostgresAppliedEdgeStore,
    edges: tuple[AppliedAtomEdge, ...],
    barrier: Barrier,
) -> str:
    barrier.wait()
    try:
        store.record_all(edges)
    except AppliedEdgeConflictError:
        return "conflict"
    return "stored"
