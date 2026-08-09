"""Shared PostgreSQL transaction lock for one tenant-scoped employee beat."""

from __future__ import annotations

import psycopg


def lock_beat(
    connection: psycopg.Connection[tuple[object, ...]],
    employee_id: str,
    beat_run_id: str,
) -> None:
    connection.execute(
        "SELECT pg_advisory_xact_lock(hashtextextended("
        "current_setting('app.company_id', true) || E'\\x1f' || %s || E'\\x1f' || %s, 0))",
        (employee_id, beat_run_id),
    )
