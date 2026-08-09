"""Immutable Lattice-owned PostgreSQL migrations."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files


@dataclass(frozen=True)
class Migration:
    """One ordered, immutable SQL migration export."""

    id: str
    sql: str


def load_migrations() -> tuple[Migration, ...]:
    """Return the SQL deltas for the host application's migration runner."""
    directory = files(__name__)
    return tuple(
        Migration(id=entry.name.removesuffix(".sql"), sql=entry.read_text())
        for entry in sorted(directory.iterdir(), key=lambda item: item.name)
        if entry.name.endswith(".sql")
    )


__all__ = ["Migration", "load_migrations"]
