"""Real-Postgres coverage for durable context selection lineage."""

from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from threading import Barrier

import psycopg
import pytest
from psycopg.errors import ObjectNotInPrerequisiteState
from tests.integration.conftest import _GrowingReader, app_role_conninfo

from lattice.contracts.applied import (
    AppliedAtomEdge,
    AppliedBeatOutcome,
    AppliedEdgeConflictError,
    LandedOutcomePhase,
)
from lattice.contracts.atom import Atom, ContextAtomHit
from lattice.contracts.selection import ContextAtomSelection, ContextSelectionConflictError
from lattice.domain.result import (
    AppliedContextResult,
    ContextResult,
    ContextSelectionCaptureResult,
)
from lattice.facade import Lattice
from lattice.migrations import load_migrations
from lattice.stores.postgres import PostgresLatticeStore
from lattice.stores.postgres_applied_edges import PostgresAppliedEdgeStore
from lattice.stores.postgres_atoms import PostgresAtomStore
from lattice.stores.postgres_context_selections import PostgresContextSelectionJournal


def _atom(key: str, *, value: str = "durable context") -> Atom:
    return Atom(
        employee_id="agent-1",
        key=key,
        value=value,
        source_run_ids=("source-run",),
        created_at=datetime(2026, 8, 9, tzinfo=UTC),
    )


def _selection(key: str, revision: int, *, beat_run_id: str = "beat-1") -> ContextAtomSelection:
    return ContextAtomSelection(
        employee_id="agent-1",
        beat_run_id=beat_run_id,
        key=key,
        revision=revision,
    )


def _edge(selection: ContextAtomSelection) -> AppliedAtomEdge:
    return AppliedAtomEdge(
        employee_id=selection.employee_id,
        beat_run_id=selection.beat_run_id,
        key=selection.key,
        revision=selection.revision,
        outcome_phase=LandedOutcomePhase.TERMINAL_PASS,
        landed_at=datetime(2026, 8, 10, tzinfo=UTC),
    )


def test_context_selection_append_is_idempotent_and_rejects_a_divergent_revision(
    pg_database: str,
) -> None:
    company_id = uuid.uuid4()
    with PostgresAtomStore.open(pg_database, company_id=company_id) as atoms:
        atoms.write(_atom("api.retry", value="revision one"))
        first = _selection("api.retry", 1)
        atoms.write(_atom("api.retry", value="revision two"))
        divergent = _selection("api.retry", 2)
        atoms.write(_atom("api.timeout"))
        addition = _selection("api.timeout", 1)

    with PostgresContextSelectionJournal.open(pg_database, company_id=company_id) as journal:
        assert journal.append_all((first,)) == (first,)
        assert journal.append_all((addition,)) == (addition,)
        assert journal.append_all((first,)) == (first,)
        with pytest.raises(ContextSelectionConflictError):
            journal.append_all((divergent,))

    with PostgresContextSelectionJournal.open(pg_database, company_id=company_id) as restarted:
        assert restarted.list_for_run("agent-1", "beat-1") == (first, addition)


def test_context_selection_is_immutable_after_seal_but_exact_replay_is_accepted(
    pg_database: str,
) -> None:
    app_conninfo = app_role_conninfo(pg_database)
    company_id = uuid.uuid4()
    with PostgresAtomStore.open(app_conninfo, company_id=company_id) as atoms:
        atoms.write(_atom("api.retry"))
        atoms.write(_atom("api.timeout"))
        atoms.write(_atom("api.circuit_breaker"))
        atoms.write(_atom("api.retry", value="revision two"))
    selected = _selection("api.retry", 1)
    second = _selection("api.timeout", 1)
    addition = _selection("api.circuit_breaker", 1)
    divergent = _selection("api.retry", 2)
    with PostgresContextSelectionJournal.open(app_conninfo, company_id=company_id) as journal:
        journal.append_all((selected, second))
    with PostgresAppliedEdgeStore.open(app_conninfo, company_id=company_id) as applied:
        applied.record_all((_edge(selected), _edge(second)))
    with PostgresContextSelectionJournal.open(app_conninfo, company_id=company_id) as journal:
        assert journal.append_all((second, selected)) == (selected, second)
        with pytest.raises(ContextSelectionConflictError):
            journal.append_all((selected,))
        with pytest.raises(ContextSelectionConflictError):
            journal.append_all((selected, second, addition))
        with pytest.raises(ContextSelectionConflictError):
            journal.append_all((divergent, second))

    with psycopg.connect(app_conninfo, autocommit=True) as connection:
        connection.execute("SELECT set_config('app.company_id', %s, false)", (str(company_id),))
        with pytest.raises(ObjectNotInPrerequisiteState):
            connection.execute(
                "INSERT INTO lattice_context_atom_selection "
                "(employee_id, beat_run_id, key, revision) VALUES (%s, %s, %s, %s)",
                (addition.employee_id, addition.beat_run_id, addition.key, addition.revision),
            )
        with pytest.raises(ObjectNotInPrerequisiteState):
            connection.execute(
                "UPDATE lattice_context_atom_selection SET revision = revision "
                "WHERE employee_id = %s AND beat_run_id = %s AND key = %s",
                (selected.employee_id, selected.beat_run_id, selected.key),
            )
        with pytest.raises(ObjectNotInPrerequisiteState):
            connection.execute(
                "DELETE FROM lattice_context_atom_selection "
                "WHERE employee_id = %s AND beat_run_id = %s AND key = %s",
                (selected.employee_id, selected.beat_run_id, selected.key),
            )


def test_context_selection_obeys_company_force_rls(pg_database: str) -> None:
    app_conninfo = app_role_conninfo(pg_database)
    company_a, company_b = uuid.uuid4(), uuid.uuid4()
    selected = _selection("api.retry", 1)
    with (
        PostgresAtomStore.open(app_conninfo, company_id=company_a) as atoms_a,
        PostgresAtomStore.open(app_conninfo, company_id=company_b) as atoms_b,
    ):
        atoms_a.write(_atom("api.retry", value="company a"))
        atoms_b.write(_atom("api.retry", value="company b"))
    with (
        PostgresContextSelectionJournal.open(app_conninfo, company_id=company_a) as journal_a,
        PostgresContextSelectionJournal.open(app_conninfo, company_id=company_b) as journal_b,
    ):
        journal_a.append_all((selected,))
        journal_b.append_all((selected,))
        assert journal_a.list_for_run("agent-1", "beat-1") == (selected,)
        assert journal_b.list_for_run("agent-1", "beat-1") == (selected,)


def test_context_selection_append_and_seal_are_serialized(pg_database: str) -> None:
    company_id = uuid.uuid4()
    with PostgresAtomStore.open(pg_database, company_id=company_id) as atoms:
        atoms.write(_atom("api.retry"))
        atoms.write(_atom("api.timeout"))
    selected = _selection("api.retry", 1)
    addition = _selection("api.timeout", 1)
    with PostgresContextSelectionJournal.open(pg_database, company_id=company_id) as setup:
        setup.append_all((selected,))
    barrier = Barrier(2)
    with (
        PostgresContextSelectionJournal.open(pg_database, company_id=company_id) as journal,
        PostgresAppliedEdgeStore.open(pg_database, company_id=company_id) as applied,
        ThreadPoolExecutor(max_workers=2) as executor,
    ):
        append_result = executor.submit(_append_after_barrier, journal, addition, barrier)
        seal_result = executor.submit(_seal_after_barrier, applied, _edge(selected), barrier)
        outcomes = (append_result.result(), seal_result.result())
        assert outcomes.count("conflict") == 1
        if "sealed" in outcomes:
            assert journal.list_for_run("agent-1", "beat-1") == (selected,)
            assert applied.list_for_run("agent-1", "beat-1") == (_edge(selected),)
        else:
            assert journal.list_for_run("agent-1", "beat-1") == (selected, addition)
            assert applied.list_for_run("agent-1", "beat-1") == ()


def test_empty_selection_seals_across_restart_and_rejects_changed_outcome_or_addition(
    pg_database: str,
) -> None:
    company_id = uuid.uuid4()
    landed_at = datetime(2026, 8, 10, tzinfo=UTC)
    with PostgresLatticeStore.open(pg_database, company_id=company_id) as store:
        lattice = store.build_lattice(episodes=_GrowingReader([]))
        context = lattice.context_result("agent-1", "nothing selected")
        capture = lattice.capture_context_selection("agent-1", context, beat_run_id="empty-beat")
        assert capture.durable is True
        assert capture.selections == ()

    with psycopg.connect(pg_database) as connection:
        assert connection.execute(
            "SELECT selected_count, selected_digest, complete "
            "FROM lattice_context_selection_beat "
            "WHERE company_id = %s AND employee_id = %s AND beat_run_id = %s",
            (company_id, "agent-1", "empty-beat"),
        ).fetchone() == (0, sha256().digest(), True)

    with PostgresLatticeStore.open(pg_database, company_id=company_id) as restarted:
        lattice = restarted.build_lattice(episodes=_GrowingReader([]))
        assert lattice.record_landed_selection(
            "agent-1",
            "empty-beat",
            outcome_phase=LandedOutcomePhase.TERMINAL_PASS,
            landed_at=landed_at,
        ) == ()
        assert lattice.record_landed_selection(
            "agent-1",
            "empty-beat",
            outcome_phase=LandedOutcomePhase.TERMINAL_PASS,
            landed_at=landed_at,
        ) == ()
        with pytest.raises(AppliedEdgeConflictError):
            lattice.record_landed_selection(
                "agent-1",
                "empty-beat",
                outcome_phase=LandedOutcomePhase.TERMINAL_FAIL,
                landed_at=landed_at,
            )
        with pytest.raises(AppliedEdgeConflictError):
            lattice.record_landed_selection(
                "agent-1",
                "empty-beat",
                outcome_phase=LandedOutcomePhase.TERMINAL_PASS,
                landed_at=landed_at + timedelta(seconds=1),
            )
        restarted.atoms.write(_atom("api.retry"))
        selected_context = lattice.context_result("agent-1", "retry")
        with pytest.raises(ContextSelectionConflictError):
            lattice.capture_context_selection(
                "agent-1",
                selected_context,
                beat_run_id="empty-beat",
            )

    with psycopg.connect(pg_database) as connection:
        row = connection.execute(
            "SELECT selected_count, selected_digest FROM lattice_atom_applied_beat "
            "WHERE employee_id = %s AND beat_run_id = %s",
            ("agent-1", "empty-beat"),
        ).fetchone()
    assert row == (0, sha256().digest())


def test_absent_capture_cannot_be_mistaken_for_a_complete_empty_capture(
    pg_database: str,
) -> None:
    outcome = AppliedBeatOutcome(
        employee_id="agent-1",
        beat_run_id="never-captured",
        outcome_phase=LandedOutcomePhase.TERMINAL_PASS,
        landed_at=datetime(2026, 8, 10, tzinfo=UTC),
    )
    with PostgresAppliedEdgeStore.open(
        pg_database,
        company_id=uuid.uuid4(),
    ) as applied:
        with pytest.raises(AppliedEdgeConflictError, match="complete durable"):
            applied.seal(outcome, ())

    with psycopg.connect(pg_database) as connection:
        assert connection.execute(
            "SELECT count(*) FROM lattice_atom_applied_beat "
            "WHERE employee_id = %s AND beat_run_id = %s",
            (outcome.employee_id, outcome.beat_run_id),
        ).fetchone() == (0,)


def test_mixed_capture_survives_restart_but_refuses_partial_seal(pg_database: str) -> None:
    company_id = uuid.uuid4()
    with PostgresLatticeStore.open(pg_database, company_id=company_id) as store:
        store.atoms.write(_atom("api.retry"))
        versioned = store.atoms.list_active_hits("agent-1")[0]
        legacy_atom = _atom("api.legacy")
        context = ContextResult(
            markdown="",
            hits=(
                versioned,
                ContextAtomHit(
                    employee_id="agent-1",
                    key=legacy_atom.key,
                    revision=None,
                    atom=legacy_atom,
                ),
            ),
        )
        capture = store.build_lattice(episodes=_GrowingReader([])).capture_context_selection(
            "agent-1",
            context,
            beat_run_id="mixed-beat",
        )
        assert capture.durable is False
        assert capture.selections == (_selection("api.retry", 1, beat_run_id="mixed-beat"),)

    with PostgresLatticeStore.open(pg_database, company_id=company_id) as restarted:
        lattice = restarted.build_lattice(episodes=_GrowingReader([]))
        assert lattice.context_selection_for_run("agent-1", "mixed-beat") == capture.selections
        with pytest.raises(AppliedEdgeConflictError, match="complete durable"):
            lattice.record_landed_selection(
                "agent-1",
                "mixed-beat",
                outcome_phase=LandedOutcomePhase.TERMINAL_PASS,
                landed_at=datetime(2026, 8, 10, tzinfo=UTC),
            )

    with psycopg.connect(pg_database) as connection:
        assert connection.execute(
            "SELECT selected_count, complete FROM lattice_context_selection_beat "
            "WHERE company_id = %s AND employee_id = %s AND beat_run_id = %s",
            (company_id, "agent-1", "mixed-beat"),
        ).fetchone() == (1, False)


def test_later_versioned_capture_reports_sticky_incomplete_union_after_restart(
    pg_database: str,
) -> None:
    company_id = uuid.uuid4()
    with PostgresLatticeStore.open(pg_database, company_id=company_id) as store:
        store.atoms.write(_atom("api.retry"))
        store.atoms.write(_atom("api.timeout"))
        hits = {hit.key: hit for hit in store.atoms.list_active_hits("agent-1")}
        legacy_atom = _atom("api.legacy")
        lattice = store.build_lattice(episodes=_GrowingReader([]))

        mixed = lattice.capture_context_selection(
            "agent-1",
            ContextResult(
                markdown="",
                hits=(
                    hits["api.retry"],
                    ContextAtomHit("agent-1", "api.legacy", None, legacy_atom),
                ),
            ),
            beat_run_id="sticky-beat",
        )
        later = lattice.capture_context_selection(
            "agent-1",
            ContextResult(markdown="", hits=(hits["api.timeout"],)),
            beat_run_id="sticky-beat",
        )

        assert mixed.durable is False
        assert later.durable is False
        assert later.skipped_unversioned_hits == ()
        assert later.selections == (
            _selection("api.retry", 1, beat_run_id="sticky-beat"),
            _selection("api.timeout", 1, beat_run_id="sticky-beat"),
        )

    with PostgresLatticeStore.open(pg_database, company_id=company_id) as restarted:
        lattice = restarted.build_lattice(episodes=_GrowingReader([]))
        replay = lattice.capture_context_selection(
            "agent-1",
            ContextResult(markdown="", hits=restarted.atoms.list_active_hits("agent-1")),
            beat_run_id="sticky-beat",
        )
        assert replay.durable is False
        assert replay.selections == later.selections
        with pytest.raises(AppliedEdgeConflictError, match="complete durable"):
            lattice.record_landed_selection(
                "agent-1",
                "sticky-beat",
                outcome_phase=LandedOutcomePhase.TERMINAL_PASS,
                landed_at=datetime(2026, 8, 10, tzinfo=UTC),
            )


def test_concurrent_capture_order_converges_to_an_incomplete_union(pg_database: str) -> None:
    company_id = uuid.uuid4()
    with PostgresLatticeStore.open(pg_database, company_id=company_id) as setup:
        setup.atoms.write(_atom("api.retry"))
        setup.atoms.write(_atom("api.timeout"))
        hits = {hit.key: hit for hit in setup.atoms.list_active_hits("agent-1")}
    legacy_atom = _atom("api.legacy")
    mixed_context = ContextResult(
        markdown="",
        hits=(
            hits["api.retry"],
            ContextAtomHit("agent-1", "api.legacy", None, legacy_atom),
        ),
    )
    versioned_context = ContextResult(markdown="", hits=(hits["api.timeout"],))
    barrier = Barrier(2)
    with (
        PostgresLatticeStore.open(pg_database, company_id=company_id) as first,
        PostgresLatticeStore.open(pg_database, company_id=company_id) as second,
        ThreadPoolExecutor(max_workers=2) as executor,
    ):
        mixed_result = executor.submit(
            _capture_after_barrier,
            first.build_lattice(episodes=_GrowingReader([])),
            mixed_context,
            "concurrent-sticky",
            barrier,
        )
        versioned_result = executor.submit(
            _capture_after_barrier,
            second.build_lattice(episodes=_GrowingReader([])),
            versioned_context,
            "concurrent-sticky",
            barrier,
        )
        results = (mixed_result.result(), versioned_result.result())
        assert results[0].durable is False
        if results[1].durable:
            assert results[1].selections == (
                _selection("api.timeout", 1, beat_run_id="concurrent-sticky"),
            )
            assert results[0].selections == (
                _selection("api.retry", 1, beat_run_id="concurrent-sticky"),
                _selection("api.timeout", 1, beat_run_id="concurrent-sticky"),
            )
        else:
            assert results[1].selections == (
                _selection("api.retry", 1, beat_run_id="concurrent-sticky"),
                _selection("api.timeout", 1, beat_run_id="concurrent-sticky"),
            )

    with PostgresLatticeStore.open(pg_database, company_id=company_id) as restarted:
        lattice = restarted.build_lattice(episodes=_GrowingReader([]))
        replay = lattice.capture_context_selection(
            "agent-1",
            ContextResult(markdown="", hits=restarted.atoms.list_active_hits("agent-1")),
            beat_run_id="concurrent-sticky",
        )
        assert replay.durable is False
        assert replay.selections == (
            _selection("api.retry", 1, beat_run_id="concurrent-sticky"),
            _selection("api.timeout", 1, beat_run_id="concurrent-sticky"),
        )


def test_public_record_landed_context_captures_and_seals_without_a_prior_call(
    pg_database: str,
) -> None:
    company_id = uuid.uuid4()
    landed_at = datetime(2026, 8, 10, tzinfo=UTC)
    with PostgresLatticeStore.open(pg_database, company_id=company_id) as store:
        store.atoms.write(_atom("api.retry"))
        lattice = store.build_lattice(episodes=_GrowingReader([]))
        context = lattice.context_result("agent-1", "retry")
        result = lattice.record_landed_context(
            "agent-1",
            context,
            beat_run_id="legacy-public-path",
            outcome_phase=LandedOutcomePhase.NEEDS_REWORK,
            landed_at=landed_at,
        )
        expected = _edge(_selection("api.retry", 1, beat_run_id="legacy-public-path"))
        expected = AppliedAtomEdge(
            employee_id=expected.employee_id,
            key=expected.key,
            revision=expected.revision,
            beat_run_id=expected.beat_run_id,
            outcome_phase=LandedOutcomePhase.NEEDS_REWORK,
            landed_at=landed_at,
        )
        assert result == AppliedContextResult((expected,), ())

    with PostgresLatticeStore.open(pg_database, company_id=company_id) as restarted:
        lattice = restarted.build_lattice(episodes=_GrowingReader([]))
        replay = lattice.record_landed_context(
            "agent-1",
            lattice.context_result("agent-1", "retry"),
            beat_run_id="legacy-public-path",
            outcome_phase=LandedOutcomePhase.NEEDS_REWORK,
            landed_at=landed_at,
        )
        assert replay == result


def test_migration_0005_upgrades_databases_with_0003_and_0004_already_applied(
    pg_conninfo: str,
) -> None:
    database = f"lattice_upgrade_{uuid.uuid4().hex}"
    with psycopg.connect(pg_conninfo, autocommit=True) as admin:
        admin.execute(f"CREATE DATABASE {database}")
    conninfo = pg_conninfo.replace("dbname=postgres", f"dbname={database}")
    migrations = load_migrations()
    try:
        with psycopg.connect(conninfo, autocommit=True) as connection:
            for migration in migrations[:4]:
                connection.execute(migration.sql)
            constraint = connection.execute(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conname = 'lattice_atom_applied_beat_selected_count_check'"
            ).fetchone()
            assert constraint is not None
            assert "selected_count > 0" in str(constraint[0])

            company_id = uuid.uuid4()
            connection.execute("SELECT set_config('app.company_id', %s, false)", (str(company_id),))
            connection.execute(
                "INSERT INTO lattice_atom "
                "(employee_id, key, value, created_at, activation) "
                "VALUES (%s, %s, %s, %s, %s)",
                ("agent-1", "legacy.key", "legacy", datetime(2026, 8, 9, tzinfo=UTC), 1.0),
            )
            connection.execute(
                "INSERT INTO lattice_atom_revision "
                "(employee_id, key, version, value, created_at, activation) "
                "VALUES (%s, %s, 1, %s, %s, %s)",
                ("agent-1", "legacy.key", "legacy", datetime(2026, 8, 9, tzinfo=UTC), 1.0),
            )
            connection.execute(
                "INSERT INTO lattice_context_atom_selection "
                "(employee_id, beat_run_id, key, revision) VALUES (%s, %s, %s, 1)",
                ("agent-1", "legacy-beat", "legacy.key"),
            )

            connection.execute(migrations[4].sql)
            assert connection.execute(
                "SELECT selected_count, selected_digest, complete "
                "FROM lattice_context_selection_beat "
                "WHERE employee_id = %s AND beat_run_id = %s",
                ("agent-1", "legacy-beat"),
            ).fetchone() == (1, bytes(32), False)
            connection.execute(
                "INSERT INTO lattice_context_selection_beat "
                "(employee_id, beat_run_id, selected_count, selected_digest, complete) "
                "VALUES (%s, %s, 0, %s, true)",
                ("agent-1", "empty-upgrade", sha256().digest()),
            )
            connection.execute(
                "INSERT INTO lattice_atom_applied_beat "
                "(employee_id, beat_run_id, outcome_phase, landed_at, "
                "selected_count, selected_digest) VALUES (%s, %s, %s, %s, 0, %s)",
                (
                    "agent-1",
                    "empty-upgrade",
                    LandedOutcomePhase.TERMINAL_PASS.value,
                    datetime(2026, 8, 10, tzinfo=UTC),
                    sha256().digest(),
                ),
            )
    finally:
        with psycopg.connect(pg_conninfo, autocommit=True) as admin:
            admin.execute(f"DROP DATABASE IF EXISTS {database} WITH (FORCE)")


def test_empty_selection_seal_and_first_append_are_serialized(pg_database: str) -> None:
    company_id = uuid.uuid4()
    with PostgresAtomStore.open(pg_database, company_id=company_id) as atoms:
        atoms.write(_atom("api.retry"))
    addition = _selection("api.retry", 1, beat_run_id="empty-race")
    outcome = AppliedBeatOutcome(
        employee_id="agent-1",
        beat_run_id="empty-race",
        outcome_phase=LandedOutcomePhase.TERMINAL_PASS,
        landed_at=datetime(2026, 8, 10, tzinfo=UTC),
    )
    barrier = Barrier(2)
    with (
        PostgresContextSelectionJournal.open(pg_database, company_id=company_id) as journal,
        PostgresAppliedEdgeStore.open(pg_database, company_id=company_id) as applied,
        ThreadPoolExecutor(max_workers=2) as executor,
    ):
        append_result = executor.submit(_append_after_barrier, journal, addition, barrier)
        seal_result = executor.submit(_seal_empty_after_barrier, applied, outcome, barrier)
        outcomes = (append_result.result(), seal_result.result())
        assert outcomes.count("conflict") == 1
        if "sealed" in outcomes:
            assert journal.list_for_run("agent-1", "empty-race") == ()
        else:
            assert journal.list_for_run("agent-1", "empty-race") == (addition,)
            assert applied.list_for_run("agent-1", "empty-race") == ()


def _append_after_barrier(
    journal: PostgresContextSelectionJournal,
    selection: ContextAtomSelection,
    barrier: Barrier,
) -> str:
    barrier.wait()
    try:
        journal.append_all((selection,))
    except ContextSelectionConflictError:
        return "conflict"
    return "appended"


def _seal_after_barrier(
    applied: PostgresAppliedEdgeStore,
    edge: AppliedAtomEdge,
    barrier: Barrier,
) -> str:
    barrier.wait()
    try:
        applied.record_all((edge,))
    except AppliedEdgeConflictError:
        return "conflict"
    return "sealed"


def _seal_empty_after_barrier(
    applied: PostgresAppliedEdgeStore,
    outcome: AppliedBeatOutcome,
    barrier: Barrier,
) -> str:
    barrier.wait()
    try:
        applied.seal(outcome, ())
    except AppliedEdgeConflictError:
        return "conflict"
    return "sealed"


def _capture_after_barrier(
    lattice: Lattice,
    context: ContextResult,
    beat_run_id: str,
    barrier: Barrier,
) -> ContextSelectionCaptureResult:
    barrier.wait()
    return lattice.capture_context_selection(
        "agent-1",
        context,
        beat_run_id=beat_run_id,
    )
