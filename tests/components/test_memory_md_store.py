"""stores/memory_md.py — atom persistence and MEMORY.md view."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from lattice.contracts.atom import Atom
from lattice.stores.memory_md import MemoryMdStore


def test_write_sanitizes_key_in_filename(tmp_path: Path) -> None:
    atoms = MemoryMdStore(tmp_path)
    now = datetime.now(UTC)
    atoms.write(
        Atom(
            key="api.retry",
            value="HTTP retries use exponential backoff capped at 30s",
            employee_id="e1",
            source_run_ids=("r1",),
            created_at=now,
        )
    )
    assert (tmp_path / "e1" / "semantic" / "api__retry.json").exists()


def test_invalidate_marks_atom_inactive(tmp_path: Path) -> None:
    atoms = MemoryMdStore(tmp_path)
    now = datetime.now(UTC)
    atoms.write(
        Atom(
            key="api.retry",
            value="HTTP retries use exponential backoff capped at 30s",
            employee_id="e1",
            source_run_ids=("r1",),
            created_at=now,
        )
    )
    atoms.invalidate("e1", "api.retry", at=now)
    assert atoms.list_active("e1") == ()


def test_memory_md_regenerated_on_write(tmp_path: Path) -> None:
    atoms = MemoryMdStore(tmp_path)
    now = datetime.now(UTC)
    atoms.write(
        Atom(
            key="api.retry",
            value="HTTP retries use exponential backoff capped at 30s",
            employee_id="e1",
            source_run_ids=("r1",),
            created_at=now,
        )
    )
    content = (tmp_path / "e1" / "MEMORY.md").read_text()
    assert "api.retry" in content
    assert "exponential backoff" in content
