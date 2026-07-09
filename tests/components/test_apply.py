"""apply.py — transactional pattern writes."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from lattice.apply import apply_proposal
from lattice.contracts.atom import Atom
from lattice.domain.proposal import PatternDraft, Proposal
from lattice.domain.result import ValidationResult
from lattice.stores.memory_md import MemoryMdStore


def test_apply_failed_validation_does_not_write(tmp_path: Path) -> None:
    atoms = MemoryMdStore(tmp_path)
    proposal = Proposal(
        employee_id="e1",
        patterns=(
            PatternDraft(key="api.retry", claim="x" * 20, source_run_ids=("r1",)),
        ),
    )
    result = apply_proposal(
        proposal,
        ValidationResult(ok=False, errors=("bad proposal",)),
        atoms=atoms,
    )
    assert result.ok is False
    assert atoms.list_active("e1") == ()


def test_apply_assert_writes_atom(tmp_path: Path) -> None:
    atoms = MemoryMdStore(tmp_path)
    proposal = Proposal(
        employee_id="e1",
        patterns=(
            PatternDraft(
                key="api.retry",
                claim="HTTP retries use exponential backoff capped at 30s",
                source_run_ids=("r1",),
            ),
        ),
    )
    result = apply_proposal(proposal, ValidationResult(ok=True), atoms=atoms)
    assert result.ok is True
    assert result.patterns_written == 1
    active = atoms.list_active("e1")
    assert len(active) == 1
    assert active[0].key == "api.retry"


def test_apply_supersede_invalidates_old(tmp_path: Path) -> None:
    atoms = MemoryMdStore(tmp_path)
    now = datetime.now(UTC)
    atoms.write(
        Atom(
            key="api.retry",
            value="old claim with enough length here",
            employee_id="e1",
            source_run_ids=("r0",),
            created_at=now,
        )
    )

    proposal = Proposal(
        employee_id="e1",
        patterns=(
            PatternDraft(
                key="api.retry",
                claim="HTTP retries use exponential backoff capped at 60s",
                source_run_ids=("r1",),
                supersedes="api.retry",
            ),
        ),
    )
    result = apply_proposal(proposal, ValidationResult(ok=True), atoms=atoms)
    assert result.ok is True

    active = atoms.list_active("e1")
    assert len(active) == 1
    assert "60s" in active[0].value
