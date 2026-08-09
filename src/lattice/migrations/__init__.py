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

    @property
    def checksum(self) -> str:
        """SHA-256 of the immutable UTF-8 migration bytes."""
        return hashlib.sha256(self.sql.encode("utf-8")).hexdigest()

    def statements(self) -> list[str]:
        """Executable statements in source order, with SQL comments removed."""
        return _split_statements(self.sql)

    def table_names(self) -> list[str]:
        """Tables this migration creates, in statement order, for host role grants."""
        matches = (_CREATE_TABLE.match(statement) for statement in self.statements())
        return [match.group(1) for match in matches if match is not None]


def load_migrations() -> tuple[Migration, ...]:
    """Return the SQL deltas for the host application's migration runner."""
    directory = files(__name__)
    return tuple(
        Migration(id=entry.name.removesuffix(".sql"), sql=entry.read_bytes().decode("utf-8"))
        for entry in sorted(directory.iterdir(), key=lambda item: item.name)
        if entry.name.endswith(".sql")
    )


def _split_statements(sql: str) -> list[str]:
    """Split SQL only on unquoted semicolons while discarding line comments."""
    statements: list[str] = []
    current: list[str] = []
    quote: str | None = None
    position = 0
    while position < len(sql):
        if quote is None:
            if sql.startswith("--", position):
                newline = sql.find("\n", position)
                position = len(sql) if newline == -1 else newline
                continue
            if sql[position] in {"'", '"'}:
                quote = sql[position]
                current.append(sql[position])
                position += 1
                continue
            dollar_quote = _dollar_quote_at(sql, position)
            if dollar_quote is not None:
                quote = dollar_quote
                current.append(dollar_quote)
                position += len(dollar_quote)
                continue
            if sql[position] == ";":
                statement = "".join(current).strip()
                if statement:
                    statements.append(statement)
                current = []
                position += 1
                continue
            current.append(sql[position])
            position += 1
            continue

        if quote in {"'", '"'}:
            current.append(sql[position])
            if sql[position] == quote:
                if position + 1 < len(sql) and sql[position + 1] == quote:
                    current.append(sql[position + 1])
                    position += 2
                    continue
                quote = None
            position += 1
            continue

        if sql.startswith(quote, position):
            current.append(quote)
            position += len(quote)
            quote = None
            continue
        current.append(sql[position])
        position += 1

    statement = "".join(current).strip()
    if statement:
        statements.append(statement)
    return statements


def _dollar_quote_at(sql: str, position: int) -> str | None:
    if sql[position] != "$":
        return None
    closing = sql.find("$", position + 1)
    if closing == -1:
        return None
    tag = sql[position + 1 : closing]
    if tag and not (tag[0].isalpha() or tag[0] == "_"):
        return None
    if any(not (character.isalnum() or character == "_") for character in tag):
        return None
    return sql[position : closing + 1]


__all__ = ["Migration", "load_migrations"]
