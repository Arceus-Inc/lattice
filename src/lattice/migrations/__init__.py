"""Immutable Lattice-owned PostgreSQL migrations."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from importlib.resources import files

_CREATE_TABLE = re.compile(r"^CREATE TABLE (\w+)", re.IGNORECASE)


@dataclass(frozen=True)
class Migration:
    """One ordered, immutable SQL migration export."""

    id: str
    sql: str
    raw_bytes: bytes | None = None

    @property
    def checksum(self) -> str:
        """SHA-256 of the immutable migration bytes supplied by the package."""
        contents = self.raw_bytes if self.raw_bytes is not None else self.sql.encode("utf-8")
        return hashlib.sha256(contents).hexdigest()

    def statements(self) -> list[str]:
        """Executable statements in source order, with line comments removed."""
        without_comments = "\n".join(line.split("--", 1)[0] for line in self.sql.splitlines())
        return [statement.strip() for statement in without_comments.split(";") if statement.strip()]

    def table_names(self) -> list[str]:
        """Tables this migration creates, in statement order, for host role grants."""
        matches = (_CREATE_TABLE.match(statement) for statement in self.statements())
        return [match.group(1) for match in matches if match is not None]


def load_migrations() -> tuple[Migration, ...]:
    """Return the SQL deltas for the host application's migration runner."""
    directory = files(__name__)
    return tuple(
        Migration(
            id=entry.name.removesuffix(".sql"),
            sql=(raw_bytes := entry.read_bytes()).decode("utf-8"),
            raw_bytes=raw_bytes,
        )
        for entry in sorted(directory.iterdir(), key=lambda item: item.name)
        if entry.name.endswith(".sql")
    )


__all__ = ["Migration", "load_migrations"]
