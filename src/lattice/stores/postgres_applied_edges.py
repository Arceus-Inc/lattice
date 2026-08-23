"""PostgreSQL persistence for exact atom-revision APPLIED outcome edges."""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from types import TracebackType
from typing import Self
from uuid import UUID

import psycopg
from psycopg.rows import tuple_row

from lattice.contracts.applied import (
    AppliedAtomEdge,
    AppliedBeatOutcome,
    AppliedEdgeConflictError,
    LandedOutcomePhase,
)
from lattice.stores._postgres_beat_lock import lock_beat


class PostgresAppliedEdgeStore:
    """Company-scoped APPLIED edge store; the host applies ``lattice.migrations`` first."""

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

    def record(self, edge: AppliedAtomEdge) -> None:
        self.record_all((edge,))

    def record_all(self, edges: tuple[AppliedAtomEdge, ...]) -> tuple[AppliedAtomEdge, ...]:
        canonical = _validate_complete_batch(edges)
        if not canonical:
            return ()
        first = canonical[0]
        return self.seal(
            AppliedBeatOutcome(
                employee_id=first.employee_id,
                beat_run_id=first.beat_run_id,
                outcome_phase=first.outcome_phase,
                landed_at=first.landed_at,
            ),
            canonical,
        )

    def seal(
        self,
        outcome: AppliedBeatOutcome,
        edges: tuple[AppliedAtomEdge, ...],
    ) -> tuple[AppliedAtomEdge, ...]:
        canonical = _validate_complete_batch(edges)
        if any(
            (edge.employee_id, edge.beat_run_id, edge.outcome_phase, edge.landed_at)
            != (
                outcome.employee_id,
                outcome.beat_run_id,
                outcome.outcome_phase,
                outcome.landed_at,
            )
            for edge in canonical
        ):
            raise AppliedEdgeConflictError("APPLIED edges must match their beat outcome identity")
        digest = _selected_digest(canonical)
        with self._connection.transaction():
            lock_beat(self._connection, outcome.employee_id, outcome.beat_run_id)
            self._require_exact_journal(outcome, canonical)
            self._record_header(outcome, selected_count=len(canonical), selected_digest=digest)
            for edge in canonical:
                self._record_one(edge)
        return canonical

    def list_for_run(self, employee_id: str, beat_run_id: str) -> tuple[AppliedAtomEdge, ...]:
        rows = self._connection.execute(
            "SELECT employee_id, key, revision, beat_run_id, outcome_phase, landed_at "
            "FROM lattice_atom_applied_edge WHERE employee_id = %s AND beat_run_id = %s "
            "ORDER BY key, revision",
            (employee_id, beat_run_id),
        ).fetchall()
        return tuple(
            AppliedAtomEdge(
                employee_id=_as_text(row[0], "employee_id"),
                key=_as_text(row[1], "key"),
                revision=_as_positive_int(row[2], "revision"),
                beat_run_id=_as_text(row[3], "beat_run_id"),
                outcome_phase=LandedOutcomePhase(_as_text(row[4], "outcome_phase")),
                landed_at=_as_datetime(row[5], "landed_at"),
            )
            for row in rows
        )

    def _require_exact_journal(
        self,
        outcome: AppliedBeatOutcome,
        edges: tuple[AppliedAtomEdge, ...],
    ) -> None:
        header = self._connection.execute(
            "SELECT selected_count, selected_digest, complete "
            "FROM lattice_context_selection_beat "
            "WHERE employee_id = %s AND beat_run_id = %s FOR SHARE",
            (outcome.employee_id, outcome.beat_run_id),
        ).fetchone()
        expected_header = (len(edges), _selected_digest(edges), True)
        if header is None or (
            _as_nonnegative_int(header[0], "selected_count"),
            _as_bytes(header[1], "selected_digest"),
            _as_bool(header[2], "complete"),
        ) != expected_header:
            raise AppliedEdgeConflictError(
                f"APPLIED beat {outcome.employee_id!r}/{outcome.beat_run_id!r} "
                "requires a complete durable context selection capture"
            )
        rows = self._connection.execute(
            "SELECT key, revision FROM lattice_context_atom_selection "
            "WHERE employee_id = %s AND beat_run_id = %s ORDER BY key FOR SHARE",
            (outcome.employee_id, outcome.beat_run_id),
        ).fetchall()
        persisted = tuple(
            (_as_text(row[0], "key"), _as_positive_int(row[1], "revision")) for row in rows
        )
        requested = tuple((edge.key, edge.revision) for edge in edges)
        if persisted != requested:
            raise AppliedEdgeConflictError(
                f"APPLIED beat {outcome.employee_id!r}/{outcome.beat_run_id!r} "
                "does not match its durable context selection journal"
            )

    def _record_header(
        self,
        outcome: AppliedBeatOutcome,
        *,
        selected_count: int,
        selected_digest: bytes,
    ) -> None:
        inserted = self._connection.execute(
            "INSERT INTO lattice_atom_applied_beat "
            "(employee_id, beat_run_id, outcome_phase, landed_at, selected_count, selected_digest) "
            "VALUES (%s, %s, %s, %s, %s, %s) "
            "ON CONFLICT DO NOTHING "
            "RETURNING selected_count",
            (
                outcome.employee_id,
                outcome.beat_run_id,
                outcome.outcome_phase.value,
                outcome.landed_at,
                selected_count,
                selected_digest,
            ),
        ).fetchone()
        if inserted is not None:
            return
        existing = self._connection.execute(
            "SELECT outcome_phase, landed_at, selected_count, selected_digest "
            "FROM lattice_atom_applied_beat WHERE employee_id = %s AND beat_run_id = %s FOR UPDATE",
            (outcome.employee_id, outcome.beat_run_id),
        ).fetchone()
        if existing is None:
            raise RuntimeError("APPLIED beat insert did not return a persisted header")
        persisted = (
            LandedOutcomePhase(_as_text(existing[0], "outcome_phase")),
            _as_datetime(existing[1], "landed_at"),
            _as_nonnegative_int(existing[2], "selected_count"),
            _as_bytes(existing[3], "selected_digest"),
        )
        requested = (
            outcome.outcome_phase,
            outcome.landed_at,
            selected_count,
            selected_digest,
        )
        if persisted != requested:
            raise AppliedEdgeConflictError(
                f"APPLIED beat {outcome.employee_id!r}/{outcome.beat_run_id!r} "
                "already has a different selected set or outcome"
            )

    def _record_one(self, edge: AppliedAtomEdge) -> None:
        inserted = self._connection.execute(
            "INSERT INTO lattice_atom_applied_edge "
            "(employee_id, key, revision, beat_run_id, outcome_phase, landed_at) "
            "VALUES (%s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (company_id, employee_id, key, revision, beat_run_id) DO NOTHING "
            "RETURNING outcome_phase, landed_at",
            (
                edge.employee_id,
                edge.key,
                edge.revision,
                edge.beat_run_id,
                edge.outcome_phase.value,
                edge.landed_at,
            ),
        ).fetchone()
        if inserted is not None:
            return
        existing = self._connection.execute(
            "SELECT outcome_phase, landed_at FROM lattice_atom_applied_edge "
            "WHERE employee_id = %s AND key = %s AND revision = %s AND beat_run_id = %s "
            "FOR UPDATE",
            (edge.employee_id, edge.key, edge.revision, edge.beat_run_id),
        ).fetchone()
        if existing is None:
            raise RuntimeError("APPLIED edge insert did not return a persisted edge")
        phase = LandedOutcomePhase(_as_text(existing[0], "outcome_phase"))
        landed_at = _as_datetime(existing[1], "landed_at")
        if (phase, landed_at) != (edge.outcome_phase, edge.landed_at):
            raise AppliedEdgeConflictError(
                f"APPLIED edge for {edge.employee_id!r}/{edge.key!r} revision {edge.revision} "
                f"and beat {edge.beat_run_id!r} already has a different outcome"
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


def _as_datetime(value: object, column: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{column} must be a datetime")
    return value


def _as_bytes(value: object, column: str) -> bytes:
    if not isinstance(value, bytes):
        raise TypeError(f"{column} must be bytes")
    return value


def _as_bool(value: object, column: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{column} must be boolean")
    return value


def _validate_complete_batch(
    edges: tuple[AppliedAtomEdge, ...],
) -> tuple[AppliedAtomEdge, ...]:
    canonical = tuple(sorted(edges, key=lambda edge: (edge.key, edge.revision)))
    if not canonical:
        return ()
    first = canonical[0]
    identity = (first.employee_id, first.beat_run_id, first.outcome_phase, first.landed_at)
    if any(
        (edge.employee_id, edge.beat_run_id, edge.outcome_phase, edge.landed_at) != identity
        for edge in canonical[1:]
    ):
        raise AppliedEdgeConflictError(
            "one APPLIED batch must have a uniform employee, beat, outcome phase, and landed time"
        )
    members = tuple((edge.key, edge.revision) for edge in canonical)
    if len(set(members)) != len(members):
        raise AppliedEdgeConflictError("one APPLIED batch cannot contain duplicate atom revisions")
    return canonical


def _selected_digest(edges: tuple[AppliedAtomEdge, ...]) -> bytes:
    digest = sha256()
    for edge in edges:
        encoded_key = edge.key.encode("utf-8")
        digest.update(len(encoded_key).to_bytes(8, byteorder="big"))
        digest.update(encoded_key)
        digest.update(edge.revision.to_bytes(8, byteorder="big"))
    return digest.digest()
