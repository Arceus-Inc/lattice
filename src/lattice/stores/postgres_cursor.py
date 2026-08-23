"""PostgreSQL-backed consolidation watermark persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from types import TracebackType
from typing import Self
from uuid import UUID

import psycopg
from psycopg.rows import tuple_row

from lattice.contracts.cursor import ConsolidationWatermark, CursorConflictError


class PostgresCursorStore:
    """Company-scoped cursor store; the host applies ``lattice.migrations`` before opening it."""

    def __init__(
        self,
        connection: psycopg.Connection[tuple[object, ...]],
        *,
        owns_connection: bool = True,
    ) -> None:
        self._connection = connection
        self._owns_connection = owns_connection

    @classmethod
    def open(cls, conninfo: str, *, company_id: UUID) -> Self:
        """Open a dedicated connection whose session GUC scopes every statement by company."""
        connection: psycopg.Connection[tuple[object, ...]] = psycopg.connect(
            conninfo,
            autocommit=True,
            row_factory=tuple_row,
        )
        connection.execute("SET TIME ZONE 'UTC'")
        connection.execute("SELECT set_config('app.company_id', %s, false)", (str(company_id),))
        return cls(connection)

    def close(self) -> None:
        if self._owns_connection:
            self._connection.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def get(self, employee_id: str) -> ConsolidationWatermark:
        row = self._connection.execute(
            "SELECT last_run_id, episodes_seen, consolidated_at "
            "FROM lattice_consolidation_cursor WHERE employee_id = %s",
            (employee_id,),
        ).fetchone()
        if row is None:
            return ConsolidationWatermark(
                employee_id=employee_id,
                last_run_id=None,
                episodes_seen=0,
                consolidated_at=None,
            )
        return ConsolidationWatermark(
            employee_id=employee_id,
            last_run_id=_as_text(row[0], "last_run_id"),
            episodes_seen=_as_nonnegative_int(row[1], "episodes_seen"),
            consolidated_at=_as_datetime(row[2], "consolidated_at"),
        )

    def advance(self, employee_id: str, *, last_run_id: str, episodes_seen: int) -> None:
        if episodes_seen < 0:
            raise ValueError("episodes_seen must be nonnegative")
        with self._connection.transaction():
            advanced = self._connection.execute(
                "INSERT INTO lattice_consolidation_cursor "
                "(employee_id, last_run_id, episodes_seen, consolidated_at) VALUES (%s, %s, %s, %s) "
                "ON CONFLICT (company_id, employee_id) DO UPDATE SET "
                "last_run_id = EXCLUDED.last_run_id, episodes_seen = EXCLUDED.episodes_seen, "
                "consolidated_at = EXCLUDED.consolidated_at "
                "WHERE lattice_consolidation_cursor.episodes_seen < EXCLUDED.episodes_seen "
                "RETURNING last_run_id, episodes_seen",
                (employee_id, last_run_id, episodes_seen, datetime.now(UTC)),
            ).fetchone()
            if advanced is not None:
                return

            current = self._connection.execute(
                "SELECT last_run_id, episodes_seen FROM lattice_consolidation_cursor "
                "WHERE employee_id = %s FOR UPDATE",
                (employee_id,),
            ).fetchone()
            if current is None:
                raise RuntimeError("cursor upsert did not return a persisted watermark")
            current_run_id = _as_text(current[0], "last_run_id")
            current_episodes_seen = _as_nonnegative_int(current[1], "episodes_seen")
            if current_episodes_seen == episodes_seen and current_run_id != last_run_id:
                raise CursorConflictError(
                    f"cursor for {employee_id!r} already records {current_run_id!r} "
                    f"at episodes_seen={episodes_seen}"
                )


def _as_text(value: object, column: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{column} must be text")
    return value


def _as_nonnegative_int(value: object, column: str) -> int:
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    raise TypeError(f"{column} must be a nonnegative integer")


def _as_datetime(value: object, column: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{column} must be a datetime")
    return value
