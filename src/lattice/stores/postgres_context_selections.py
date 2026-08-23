"""PostgreSQL journal of exact atom revisions selected during a beat."""

from __future__ import annotations

from types import TracebackType
from typing import Self
from uuid import UUID

import psycopg
from psycopg.rows import tuple_row

from lattice.contracts.selection import (
    ContextAtomSelection,
    ContextSelectionCaptureOutcome,
    ContextSelectionConflictError,
    ContextSelectionSnapshot,
    context_selection_digest,
)
from lattice.stores._postgres_beat_lock import lock_beat


class PostgresContextSelectionJournal:
    """Company-scoped append-only context selection journal."""

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

    def capture(
        self,
        snapshot: ContextSelectionSnapshot,
    ) -> ContextSelectionCaptureOutcome:
        canonical = _canonical_batch(snapshot.selections)
        requested = ContextSelectionSnapshot(
            employee_id=snapshot.employee_id,
            beat_run_id=snapshot.beat_run_id,
            selections=canonical,
            complete=snapshot.complete,
        )
        with self._connection.transaction():
            lock_beat(self._connection, requested.employee_id, requested.beat_run_id)
            if self._is_sealed(requested.employee_id, requested.beat_run_id):
                self._require_exact_existing(requested)
                return ContextSelectionCaptureOutcome(
                    employee_id=requested.employee_id,
                    beat_run_id=requested.beat_run_id,
                    selections=canonical,
                    complete=True,
                )
            prior_complete = self._ensure_header(requested.employee_id, requested.beat_run_id)
            for selection in canonical:
                self._append_one(selection)
            persisted = self.list_for_run(requested.employee_id, requested.beat_run_id)
            complete = prior_complete and requested.complete
            self._update_header(
                requested.employee_id,
                requested.beat_run_id,
                persisted,
                complete=complete,
            )
        return ContextSelectionCaptureOutcome(
            employee_id=requested.employee_id,
            beat_run_id=requested.beat_run_id,
            selections=persisted,
            complete=complete,
        )

    def append_all(
        self,
        selections: tuple[ContextAtomSelection, ...],
    ) -> tuple[ContextAtomSelection, ...]:
        """Compatibility helper for non-empty, fully versioned capture batches."""
        canonical = _canonical_batch(selections)
        if not canonical:
            return ()
        first = canonical[0]
        self.capture(
            ContextSelectionSnapshot(
                employee_id=first.employee_id,
                beat_run_id=first.beat_run_id,
                selections=canonical,
                complete=True,
            )
        )
        return canonical

    def list_for_run(
        self,
        employee_id: str,
        beat_run_id: str,
    ) -> tuple[ContextAtomSelection, ...]:
        rows = self._connection.execute(
            "SELECT employee_id, beat_run_id, key, revision "
            "FROM lattice_context_atom_selection "
            "WHERE employee_id = %s AND beat_run_id = %s ORDER BY key",
            (employee_id, beat_run_id),
        ).fetchall()
        return tuple(_selection_from_row(row) for row in rows)

    def _is_sealed(self, employee_id: str, beat_run_id: str) -> bool:
        row = self._connection.execute(
            "SELECT 1 FROM lattice_atom_applied_beat "
            "WHERE employee_id = %s AND beat_run_id = %s",
            (employee_id, beat_run_id),
        ).fetchone()
        return row is not None

    def _require_exact_existing(
        self,
        snapshot: ContextSelectionSnapshot,
    ) -> None:
        header = self._connection.execute(
            "SELECT selected_count, selected_digest, complete "
            "FROM lattice_context_selection_beat "
            "WHERE employee_id = %s AND beat_run_id = %s FOR SHARE",
            (snapshot.employee_id, snapshot.beat_run_id),
        ).fetchone()
        persisted = self.list_for_run(snapshot.employee_id, snapshot.beat_run_id)
        expected_header = (
            snapshot.selected_count,
            snapshot.selected_digest,
            True,
        )
        if header is None or _header_from_row(header) != expected_header or persisted != snapshot.selections:
            raise ContextSelectionConflictError(
                f"APPLIED beat {snapshot.employee_id!r}/{snapshot.beat_run_id!r} "
                "only accepts an exact full selection replay"
            )

    def _ensure_header(self, employee_id: str, beat_run_id: str) -> bool:
        self._connection.execute(
            "INSERT INTO lattice_context_selection_beat "
            "(employee_id, beat_run_id, selected_count, selected_digest, complete) "
            "VALUES (%s, %s, 0, %s, true) ON CONFLICT DO NOTHING",
            (employee_id, beat_run_id, context_selection_digest(())),
        )
        row = self._connection.execute(
            "SELECT selected_count, selected_digest, complete "
            "FROM lattice_context_selection_beat "
            "WHERE employee_id = %s AND beat_run_id = %s FOR UPDATE",
            (employee_id, beat_run_id),
        ).fetchone()
        if row is None:
            raise RuntimeError("context selection header was not persisted")
        return _header_from_row(row)[2]

    def _update_header(
        self,
        employee_id: str,
        beat_run_id: str,
        selections: tuple[ContextAtomSelection, ...],
        *,
        complete: bool,
    ) -> None:
        updated = self._connection.execute(
            "UPDATE lattice_context_selection_beat "
            "SET selected_count = %s, selected_digest = %s, complete = %s "
            "WHERE employee_id = %s AND beat_run_id = %s",
            (
                len(selections),
                context_selection_digest(selections),
                complete,
                employee_id,
                beat_run_id,
            ),
        )
        if updated.rowcount != 1:
            raise RuntimeError("context selection header update did not affect one row")

    def _append_one(self, selection: ContextAtomSelection) -> None:
        inserted = self._connection.execute(
            "INSERT INTO lattice_context_atom_selection "
            "(employee_id, beat_run_id, key, revision) VALUES (%s, %s, %s, %s) "
            "ON CONFLICT (company_id, employee_id, beat_run_id, key) DO NOTHING "
            "RETURNING revision",
            (
                selection.employee_id,
                selection.beat_run_id,
                selection.key,
                selection.revision,
            ),
        ).fetchone()
        if inserted is not None:
            return
        existing = self._connection.execute(
            "SELECT revision FROM lattice_context_atom_selection "
            "WHERE employee_id = %s AND beat_run_id = %s AND key = %s FOR UPDATE",
            (selection.employee_id, selection.beat_run_id, selection.key),
        ).fetchone()
        if existing is None:
            raise RuntimeError("context selection insert did not return a persisted row")
        if _as_positive_int(existing[0], "revision") != selection.revision:
            raise ContextSelectionConflictError(
                f"context selection {selection.employee_id!r}/{selection.beat_run_id!r}/"
                f"{selection.key!r} already records a different revision"
            )


def _canonical_batch(
    selections: tuple[ContextAtomSelection, ...],
) -> tuple[ContextAtomSelection, ...]:
    canonical = tuple(sorted(set(selections), key=lambda selection: selection.key))
    if not canonical:
        return ()
    first = canonical[0]
    if any(
        (selection.employee_id, selection.beat_run_id)
        != (first.employee_id, first.beat_run_id)
        for selection in canonical[1:]
    ):
        raise ContextSelectionConflictError(
            "one context selection batch must have a uniform employee and beat"
        )
    if len({selection.key for selection in canonical}) != len(canonical):
        raise ContextSelectionConflictError(
            "one context selection batch cannot contain multiple revisions of one atom key"
        )
    return canonical


def _header_from_row(row: tuple[object, ...]) -> tuple[int, bytes, bool]:
    return (
        _as_nonnegative_int(row[0], "selected_count"),
        _as_bytes(row[1], "selected_digest"),
        _as_bool(row[2], "complete"),
    )


def _selection_from_row(row: tuple[object, ...]) -> ContextAtomSelection:
    return ContextAtomSelection(
        employee_id=_as_text(row[0], "employee_id"),
        beat_run_id=_as_text(row[1], "beat_run_id"),
        key=_as_text(row[2], "key"),
        revision=_as_positive_int(row[3], "revision"),
    )


def _as_text(value: object, column: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{column} must be text")
    return value


def _as_positive_int(value: object, column: str) -> int:
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    raise TypeError(f"{column} must be a positive integer")


def _as_nonnegative_int(value: object, column: str) -> int:
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    raise TypeError(f"{column} must be a non-negative integer")


def _as_bytes(value: object, column: str) -> bytes:
    if not isinstance(value, bytes):
        raise TypeError(f"{column} must be bytes")
    return value


def _as_bool(value: object, column: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{column} must be boolean")
    return value
