"""Host-facing Lattice migration contract tests."""

from __future__ import annotations

import hashlib

from lattice.migrations import Migration, load_migrations


def test_load_migrations_preserves_order_checksums_and_created_tables() -> None:
    migrations = load_migrations()

    assert [migration.id for migration in migrations] == [
        "0001_postgres_atoms",
        "0002_postgres_consolidation_cursors",
        "0003_postgres_applied_atom_edges",
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
        ["lattice_atom_applied_beat", "lattice_atom_applied_edge"],
    ]
    assert [migration.checksum for migration in migrations] == [
        hashlib.sha256(migration.sql.encode("utf-8")).hexdigest() for migration in migrations
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


def test_migration_statements_preserve_semicolons_inside_dollar_quoted_function_bodies() -> None:
    migration = Migration(
        id="test",
        sql=(
            "CREATE FUNCTION immutable_row() RETURNS trigger LANGUAGE plpgsql AS $function$\n"
            "BEGIN\n"
            "    RAISE EXCEPTION 'immutable';\n"
            "END\n"
            "$function$;\n"
            "CREATE TABLE widget (id integer);\n"
        ),
    )

    assert migration.statements() == [
        "CREATE FUNCTION immutable_row() RETURNS trigger LANGUAGE plpgsql AS $function$\n"
        "BEGIN\n"
        "    RAISE EXCEPTION 'immutable';\n"
        "END\n"
        "$function$",
        "CREATE TABLE widget (id integer)",
    ]


def test_migration_checksum_preserves_crlf_utf8_bytes() -> None:
    sql = "CREATE TABLE byte_exact (id integer);\r\n"
    migration = Migration(
        id="test",
        sql=sql,
    )

    assert migration.checksum == hashlib.sha256(b"CREATE TABLE byte_exact (id integer);\r\n").hexdigest()
