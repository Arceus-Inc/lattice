"""Host-facing Lattice migration contract tests."""

from __future__ import annotations

import hashlib

from lattice.migrations import Migration, load_migrations


def test_load_migrations_preserves_order_checksums_and_created_tables() -> None:
    migrations = load_migrations()

    assert [migration.id for migration in migrations] == [
        "0001_postgres_atoms",
        "0002_postgres_consolidation_cursors",
    ]
    assert [migration.table_names() for migration in migrations] == [
        [
            "lattice_atom",
            "lattice_atom_source_run",
            "lattice_atom_key_file",
            "lattice_atom_revision",
            "lattice_atom_revision_source_run",
            "lattice_atom_revision_key_file",
        ],
        ["lattice_consolidation_cursor"],
    ]
    assert [migration.checksum for migration in migrations] == [
        hashlib.sha256(migration.raw_bytes if migration.raw_bytes is not None else b"").hexdigest()
        for migration in migrations
    ]


def test_migration_statements_strip_comments_before_semicolon_splitting() -> None:
    migration = Migration(
        id="test",
        sql="-- heading; ignored\nCREATE TABLE widget (id integer); -- trailing; ignored\n"
        "CREATE TABLE widget_event (id integer);\n",
    )

    assert migration.statements() == [
        "CREATE TABLE widget (id integer)",
        "CREATE TABLE widget_event (id integer)",
    ]
    assert migration.table_names() == ["widget", "widget_event"]


def test_migration_checksum_uses_raw_package_bytes() -> None:
    raw_bytes = b"CREATE TABLE byte_exact (id integer);\r\n"
    migration = Migration(
        id="test",
        sql="CREATE TABLE byte_exact (id integer);\n",
        raw_bytes=raw_bytes,
    )

    assert migration.checksum == hashlib.sha256(raw_bytes).hexdigest()
