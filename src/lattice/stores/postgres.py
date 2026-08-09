"""Shared PostgreSQL composition for one company's atom and cursor state."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import TracebackType
from typing import Self
from uuid import UUID

import psycopg
from psycopg.rows import tuple_row

from lattice.contracts.episodic import EpisodicReader
from lattice.contracts.patch import PatchStore
from lattice.directive import DEFAULT_MIN_CLUSTER_SIZE, DEFAULT_MIN_NEW_EPISODES
from lattice.facade import Lattice
from lattice.stores.postgres_applied_edges import PostgresAppliedEdgeStore
from lattice.stores.postgres_atoms import PostgresAtomStore
from lattice.stores.postgres_context_selections import PostgresContextSelectionJournal
from lattice.stores.postgres_cursor import PostgresCursorStore


class PostgresLatticeStore:
    """Own one company-scoped connection and its atom/cursor adapters."""

    def __init__(self, connection: psycopg.Connection[tuple[object, ...]]) -> None:
        self._connection = connection
        self.atoms = PostgresAtomStore(connection, owns_connection=False)
        self.cursor = PostgresCursorStore(connection, owns_connection=False)
        self.applied_edges = PostgresAppliedEdgeStore(connection, owns_connection=False)
        self.context_selections = PostgresContextSelectionJournal(connection, owns_connection=False)

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

    def build_lattice(
        self,
        *,
        episodes: EpisodicReader,
        patches: PatchStore | None = None,
        min_new_episodes: int = DEFAULT_MIN_NEW_EPISODES,
        min_cluster_size: int = DEFAULT_MIN_CLUSTER_SIZE,
        packet_limit: int = 20,
        canonical_skills_root: Path | None = None,
        evolved_skills_root: Path | None = None,
    ) -> Lattice:
        """Build the complete typed Postgres facade without parallel constructor wiring."""
        return Lattice(
            episodes=episodes,
            cursor=self.cursor,
            atoms=self.atoms,
            patches=patches,
            min_new_episodes=min_new_episodes,
            min_cluster_size=min_cluster_size,
            packet_limit=packet_limit,
            canonical_skills_root=canonical_skills_root,
            evolved_skills_root=evolved_skills_root,
            apply_scope=self.apply_scope,
            atom_hits=self.atoms,
            applied_edges=self.applied_edges,
            context_selections=self.context_selections,
        )

    @contextmanager
    def apply_scope(self, employee_id: str) -> Iterator[None]:
        with self._connection.transaction():
            self._connection.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended("
                "current_setting('app.company_id', true) || E'\\x1f' || %s, 0))",
                (employee_id,),
            )
            yield
