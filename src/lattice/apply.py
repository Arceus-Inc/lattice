"""Transactional proposal application."""

from __future__ import annotations

from datetime import UTC, datetime

from lattice.compile import compile_proposal
from lattice.contracts.atom import Atom, AtomStore
from lattice.domain.proposal import OpKind, Proposal
from lattice.domain.result import ApplyResult, ValidationResult


def apply_proposal(
    proposal: Proposal,
    validation: ValidationResult,
    *,
    atoms: AtomStore,
) -> ApplyResult:
    """Apply a pre-validated pattern proposal."""
    if not validation.ok:
        return ApplyResult.failed(*validation.errors, employee_id=proposal.employee_id)

    now = datetime.now(UTC)
    atoms_written = 0

    for op in compile_proposal(proposal):
        if op.kind is OpKind.SUPERSEDE and op.supersedes is not None:
            atoms.invalidate(proposal.employee_id, op.supersedes, at=now)

        atom = Atom(
            key=op.key,
            value=op.value,
            employee_id=proposal.employee_id,
            source_run_ids=op.source_run_ids,
            created_at=now,
        )
        atoms.write(atom)
        atoms_written += 1

    return ApplyResult(
        employee_id=proposal.employee_id,
        patterns_applied=len(proposal.patterns),
        patterns_written=atoms_written,
    )
