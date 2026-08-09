"""Real-Postgres conformance tests for consolidation cursor persistence."""

from __future__ import annotations

import uuid

import pytest
from tests.integration.conftest import app_role_conninfo

from lattice.contracts.cursor import ConsolidationWatermark, CursorConflictError, CursorStore
from lattice.stores.postgres_cursor import PostgresCursorStore


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


def test_postgres_cursor_rejects_divergent_same_count(pg_database: str) -> None:
    with PostgresCursorStore.open(pg_database, company_id=uuid.uuid4()) as store:
        store.advance("agent-1", last_run_id="run-5", episodes_seen=5)
        first = store.get("agent-1")
        with pytest.raises(CursorConflictError):
            store.advance("agent-1", last_run_id="run-other", episodes_seen=5)
        assert store.get("agent-1") == first


def test_postgres_cursor_isolates_companies_with_force_rls(pg_database: str) -> None:
    app_conninfo = app_role_conninfo(pg_database)
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
