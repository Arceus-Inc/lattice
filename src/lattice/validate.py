"""Deterministic proposal validation — no LLM."""

from __future__ import annotations

import re

from lattice.contracts.atom import AtomStore
from lattice.contracts.episodic import RawEpisode
from lattice.domain.proposal import Op, OpKind, Proposal
from lattice.domain.result import ValidationResult

KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_.]+$")
DEFAULT_MAX_OPS = 20


def validate_proposal(
    proposal: Proposal,
    *,
    episodes: tuple[RawEpisode, ...],
    atoms: AtomStore,
    max_ops: int = DEFAULT_MAX_OPS,
) -> ValidationResult:
    """Apply the v1 validation rule set."""
    errors: list[str] = []

    if not proposal.ops:
        errors.append("proposal must contain at least one op")
    if len(proposal.ops) > max_ops:
        errors.append(f"proposal exceeds max ops ({max_ops})")

    known_runs = {ep.run_id: ep for ep in episodes if ep.employee_id == proposal.employee_id}
    active_keys = {atom.key for atom in atoms.list_active(proposal.employee_id)}

    for index, op in enumerate(proposal.ops):
        prefix = f"ops[{index}]"
        errors.extend(_validate_op(op, prefix, known_runs=known_runs, active_keys=active_keys))

    return ValidationResult(ok=not errors, errors=tuple(errors))


def _validate_op(
    op: Op,
    prefix: str,
    *,
    known_runs: dict[str, RawEpisode],
    active_keys: set[str],
) -> list[str]:
    errors: list[str] = []

    if not op.source_run_ids:
        errors.append(f"{prefix}: every op must cite at least one source_run_id")
        return errors

    for run_id in op.source_run_ids:
        if run_id not in known_runs:
            errors.append(f"{prefix}: unknown source_run_id {run_id!r}")

    if op.kind is OpKind.PATCH:
        if not op.skill or not op.section:
            errors.append(f"{prefix}: patch op requires skill and section")
        if not any(
            known_runs[run_id].outcome == "done"
            for run_id in op.source_run_ids
            if run_id in known_runs
        ):
            errors.append(f"{prefix}: patch op requires a cited engram with outcome=done")
        return errors

    if not KEY_PATTERN.match(op.key):
        errors.append(f"{prefix}: key {op.key!r} must match {KEY_PATTERN.pattern}")

    if op.kind is OpKind.ASSERT:
        if op.key in active_keys:
            errors.append(f"{prefix}: key {op.key!r} is already active; use supersede")
        active_keys.add(op.key)

    if op.kind is OpKind.SUPERSEDE:
        if op.supersedes is None:
            errors.append(f"{prefix}: supersede op requires supersedes key")
        elif op.supersedes not in active_keys:
            errors.append(f"{prefix}: supersedes key {op.supersedes!r} is not active")
        else:
            active_keys.discard(op.supersedes)
            active_keys.add(op.key)

    return errors
