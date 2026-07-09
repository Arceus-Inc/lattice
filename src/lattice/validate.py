"""Deterministic proposal validation — no LLM."""

from __future__ import annotations

import re

from lattice.contracts.atom import AtomStore
from lattice.contracts.episodic import RawEpisode
from lattice.domain.proposal import PatternDraft, Proposal
from lattice.domain.result import ValidationResult

KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_.]+$")
DEFAULT_MAX_PATTERNS = 20


def validate_proposal(
    proposal: Proposal,
    *,
    episodes: tuple[RawEpisode, ...],
    atoms: AtomStore,
    max_patterns: int = DEFAULT_MAX_PATTERNS,
) -> ValidationResult:
    """Validate pattern drafts before apply."""
    errors: list[str] = []

    if not proposal.patterns:
        errors.append("proposal must contain at least one pattern")
    if len(proposal.patterns) > max_patterns:
        errors.append(f"proposal exceeds max patterns ({max_patterns})")

    known_runs = {ep.run_id: ep for ep in episodes if ep.employee_id == proposal.employee_id}
    active_keys = {atom.key for atom in atoms.list_active(proposal.employee_id)}

    for index, pattern in enumerate(proposal.patterns):
        prefix = f"patterns[{index}]"
        errors.extend(
            _validate_pattern_draft(pattern, prefix, known_runs=known_runs, active_keys=active_keys)
        )

    return ValidationResult(ok=not errors, errors=tuple(errors))


def _validate_pattern_draft(
    pattern: PatternDraft,
    prefix: str,
    *,
    known_runs: dict[str, RawEpisode],
    active_keys: set[str],
) -> list[str]:
    errors: list[str] = []

    if not pattern.source_run_ids:
        errors.append(f"{prefix}: must cite at least one source_run_id")
        return errors

    for run_id in pattern.source_run_ids:
        if run_id not in known_runs:
            errors.append(f"{prefix}: unknown source_run_id {run_id!r}")

    if not KEY_PATTERN.match(pattern.key):
        errors.append(f"{prefix}: key {pattern.key!r} must match {KEY_PATTERN.pattern}")

    if pattern.supersedes is None:
        if pattern.key in active_keys:
            errors.append(f"{prefix}: key {pattern.key!r} is already active; set supersedes")
        active_keys.add(pattern.key)
    elif pattern.supersedes not in active_keys:
        errors.append(f"{prefix}: supersedes key {pattern.supersedes!r} is not active")
    else:
        active_keys.discard(pattern.supersedes)
        active_keys.add(pattern.key)

    return errors
