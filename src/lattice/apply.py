"""Transactional proposal application."""

from __future__ import annotations

from datetime import UTC, datetime

from lattice.contracts.atom import Atom, AtomStore
from lattice.contracts.patch import PatchStore, SkillPatch
from lattice.domain.proposal import OpKind, Proposal
from lattice.domain.result import ApplyResult, ValidationResult


def apply_proposal(
    proposal: Proposal,
    validation: ValidationResult,
    *,
    atoms: AtomStore,
    patches: PatchStore | None = None,
) -> ApplyResult:
    """Apply a pre-validated proposal."""
    if not validation.ok:
        return ApplyResult.failed(*validation.errors, employee_id=proposal.employee_id)

    now = datetime.now(UTC)
    atoms_written = 0
    patches_written = 0

    for op in proposal.ops:
        if op.kind is OpKind.PATCH:
            if patches is None:
                return ApplyResult.failed(
                    "patch store not configured",
                    employee_id=proposal.employee_id,
                )
            patch = SkillPatch(
                skill_slug=op.skill or "",
                section=op.section or "",
                new_content=op.value,
                source_run_ids=op.source_run_ids,
            )
            patches.apply_patch(proposal.employee_id, patch)
            patches_written += 1
            continue

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
        ops_applied=len(proposal.ops),
        atoms_written=atoms_written,
        patches_written=patches_written,
    )
