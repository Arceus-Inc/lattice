"""PostgreSQL-backed semantic atom persistence."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from types import TracebackType
from typing import Self

import psycopg
from psycopg.rows import tuple_row

from lattice.contracts.atom import Atom
from lattice.domain.stats import PatternStats, Tier


class PostgresAtomStore:
    """Company-scoped atom store; the host applies ``lattice.migrations`` before opening it."""

    def __init__(self, connection: psycopg.Connection[tuple[object, ...]]) -> None:
        self._connection = connection

    @classmethod
    def open(cls, conninfo: str, *, company_id: str) -> Self:
        """Open a dedicated connection whose session GUC scopes every statement by company."""
        connection: psycopg.Connection[tuple[object, ...]] = psycopg.connect(
            conninfo,
            autocommit=True,
            row_factory=tuple_row,
        )
        connection.execute("SET TIME ZONE 'UTC'")
        connection.execute("SELECT set_config('app.company_id', %s, false)", (company_id,))
        return cls(connection)

    def close(self) -> None:
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

    def list_active(self, employee_id: str) -> tuple[Atom, ...]:
        rows = self._connection.execute(
            "SELECT employee_id, key, value, created_at, invalid_at, activation, "
            "alpha_own, beta_own, tier "
            "FROM lattice_atom "
            "WHERE employee_id = %s AND invalid_at IS NULL "
            "ORDER BY created_at DESC, key",
            (employee_id,),
        ).fetchall()
        return tuple(self._atom_from_row(row) for row in rows)

    def write(self, atom: Atom) -> None:
        with self._connection.transaction():
            self._persist(atom)

    def invalidate(self, employee_id: str, key: str, *, at: datetime) -> None:
        with self._connection.transaction():
            atom = self._read_atom(employee_id, key, for_update=True)
            if atom is not None:
                self._persist(replace(atom, invalid_at=at))

    def _read_atom(
        self,
        employee_id: str,
        key: str,
        *,
        for_update: bool = False,
    ) -> Atom | None:
        conditions = "employee_id = %s AND key = %s"
        lock = " FOR UPDATE" if for_update else ""
        row = self._connection.execute(
            "SELECT employee_id, key, value, created_at, invalid_at, activation, "
            f"alpha_own, beta_own, tier FROM lattice_atom WHERE {conditions}{lock}",
            (employee_id, key),
        ).fetchone()
        return self._atom_from_row(row) if row is not None else None

    def _persist(self, atom: Atom) -> None:
        alpha, beta, tier = _stats_values(atom.stats)
        row = self._connection.execute(
            "INSERT INTO lattice_atom "
            "(employee_id, key, value, created_at, invalid_at, activation, alpha_own, beta_own, tier) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (company_id, employee_id, key) DO UPDATE SET "
            "value = EXCLUDED.value, created_at = EXCLUDED.created_at, invalid_at = EXCLUDED.invalid_at, "
            "activation = EXCLUDED.activation, alpha_own = EXCLUDED.alpha_own, "
            "beta_own = EXCLUDED.beta_own, tier = EXCLUDED.tier, "
            "version = lattice_atom.version + 1 "
            "RETURNING version",
            (
                atom.employee_id,
                atom.key,
                atom.value,
                atom.created_at,
                atom.invalid_at,
                atom.activation,
                alpha,
                beta,
                tier,
            ),
        ).fetchone()
        if row is None:
            raise RuntimeError("atom upsert did not return a version")
        version = _as_int(row[0], "version")
        self._replace_children(atom)
        self._record_revision(atom, version, alpha, beta, tier)

    def _replace_children(self, atom: Atom) -> None:
        key = (atom.employee_id, atom.key)
        self._connection.execute(
            "DELETE FROM lattice_atom_source_run WHERE employee_id = %s AND key = %s", key
        )
        self._connection.execute(
            "DELETE FROM lattice_atom_key_file WHERE employee_id = %s AND key = %s", key
        )
        for position, run_id in enumerate(atom.source_run_ids):
            self._connection.execute(
                "INSERT INTO lattice_atom_source_run (employee_id, key, position, run_id) "
                "VALUES (%s, %s, %s, %s)",
                (*key, position, run_id),
            )
        for position, path in enumerate(atom.key_files):
            self._connection.execute(
                "INSERT INTO lattice_atom_key_file (employee_id, key, position, path) "
                "VALUES (%s, %s, %s, %s)",
                (*key, position, path),
            )

    def _record_revision(
        self,
        atom: Atom,
        version: int,
        alpha: float | None,
        beta: float | None,
        tier: str | None,
    ) -> None:
        self._connection.execute(
            "INSERT INTO lattice_atom_revision "
            "(employee_id, key, version, value, created_at, invalid_at, activation, "
            "alpha_own, beta_own, tier) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                atom.employee_id,
                atom.key,
                version,
                atom.value,
                atom.created_at,
                atom.invalid_at,
                atom.activation,
                alpha,
                beta,
                tier,
            ),
        )
        for position, run_id in enumerate(atom.source_run_ids):
            self._connection.execute(
                "INSERT INTO lattice_atom_revision_source_run "
                "(employee_id, key, version, position, run_id) VALUES (%s, %s, %s, %s, %s)",
                (atom.employee_id, atom.key, version, position, run_id),
            )
        for position, path in enumerate(atom.key_files):
            self._connection.execute(
                "INSERT INTO lattice_atom_revision_key_file "
                "(employee_id, key, version, position, path) VALUES (%s, %s, %s, %s, %s)",
                (atom.employee_id, atom.key, version, position, path),
            )

    def _atom_from_row(self, row: tuple[object, ...]) -> Atom:
        employee_id = _as_text(row[0], "employee_id")
        key = _as_text(row[1], "key")
        source_run_ids = tuple(
            _as_text(source_row[0], "run_id")
            for source_row in self._connection.execute(
                "SELECT run_id FROM lattice_atom_source_run "
                "WHERE employee_id = %s AND key = %s ORDER BY position",
                (employee_id, key),
            ).fetchall()
        )
        key_files = tuple(
            _as_text(file_row[0], "path")
            for file_row in self._connection.execute(
                "SELECT path FROM lattice_atom_key_file "
                "WHERE employee_id = %s AND key = %s ORDER BY position",
                (employee_id, key),
            ).fetchall()
        )
        return Atom(
            employee_id=employee_id,
            key=key,
            value=_as_text(row[2], "value"),
            created_at=_as_datetime(row[3], "created_at"),
            invalid_at=_as_optional_datetime(row[4], "invalid_at"),
            activation=_as_float(row[5], "activation"),
            stats=_stats_from_columns(row[6], row[7], row[8]),
            source_run_ids=source_run_ids,
            key_files=key_files,
        )


def _stats_values(stats: PatternStats | None) -> tuple[float | None, float | None, str | None]:
    if stats is None:
        return None, None, None
    return stats.alpha_own, stats.beta_own, stats.tier.value


def _stats_from_columns(
    alpha: object,
    beta: object,
    tier: object,
) -> PatternStats | None:
    if alpha is None and beta is None and tier is None:
        return None
    if alpha is None or beta is None or tier is None:
        raise ValueError("incomplete pattern statistics in lattice_atom")
    return PatternStats(
        alpha_own=_as_float(alpha, "alpha_own"),
        beta_own=_as_float(beta, "beta_own"),
        tier=Tier(_as_text(tier, "tier")),
    )


def _as_text(value: object, column: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{column} must be text")
    return value


def _as_datetime(value: object, column: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{column} must be a datetime")
    return value


def _as_optional_datetime(value: object, column: str) -> datetime | None:
    if value is None:
        return None
    return _as_datetime(value, column)


def _as_float(value: object, column: str) -> float:
    if isinstance(value, (float, int)) and not isinstance(value, bool):
        return float(value)
    raise TypeError(f"{column} must be numeric")


def _as_int(value: object, column: str) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    raise TypeError(f"{column} must be an integer")
