"""Deterministic proposal validation — no LLM."""

from __future__ import annotations

import re
from pathlib import Path

from lattice.contracts.atom import AtomStore
from lattice.contracts.episodic import RawEpisode
from lattice.domain.proposal import HabitAction, HabitDraft, PatternDraft, Proposal
from lattice.domain.result import ValidationResult

KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_.]+$")
SLUG_PATTERN = re.compile(r"^[a-z][a-z0-9-]+$")
DEFAULT_MAX_OPS = 20


def validate_proposal(
    proposal: Proposal,
    *,
    episodes: tuple[RawEpisode, ...],
    atoms: AtomStore,
    max_ops: int = DEFAULT_MAX_OPS,
    canonical_skills_root: Path | None = None,
) -> ValidationResult:
    """Apply the v1 validation rule set to patterns and habits."""
    errors: list[str] = []

    total = len(proposal.patterns) + len(proposal.habits)
    if total == 0:
        errors.append("proposal must contain at least one pattern or habit")
    if total > max_ops:
        errors.append(f"proposal exceeds max items ({max_ops})")

    known_runs = {ep.run_id: ep for ep in episodes if ep.employee_id == proposal.employee_id}
    active_keys = {atom.key for atom in atoms.list_active(proposal.employee_id)}
    canonical_slugs = _canonical_slugs(canonical_skills_root)

    for index, pattern in enumerate(proposal.patterns):
        prefix = f"patterns[{index}]"
        errors.extend(
            _validate_pattern_draft(pattern, prefix, known_runs=known_runs, active_keys=active_keys)
        )

    for index, habit in enumerate(proposal.habits):
        prefix = f"habits[{index}]"
        errors.extend(
            _validate_habit_draft(
                habit,
                prefix,
                known_runs=known_runs,
                canonical_slugs=canonical_slugs,
            )
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


def _validate_habit_draft(
    habit: HabitDraft,
    prefix: str,
    *,
    known_runs: dict[str, RawEpisode],
    canonical_slugs: set[str],
) -> list[str]:
    errors: list[str] = []

    if not habit.source_run_ids:
        errors.append(f"{prefix}: must cite at least one source_run_id")
        return errors

    for run_id in habit.source_run_ids:
        if run_id not in known_runs:
            errors.append(f"{prefix}: unknown source_run_id {run_id!r}")

    if not any(
        known_runs[run_id].outcome == "done"
        for run_id in habit.source_run_ids
        if run_id in known_runs
    ):
        errors.append(f"{prefix}: habit requires a cited engram with outcome=done")

    if not habit.body.strip():
        errors.append(f"{prefix}: body must not be empty")

    if habit.action is HabitAction.EVOLVE:
        if not habit.skill or not habit.section:
            errors.append(f"{prefix}: evolve habit requires skill and section")
        if habit.skill and not SLUG_PATTERN.match(habit.skill):
            errors.append(f"{prefix}: skill {habit.skill!r} must match {SLUG_PATTERN.pattern}")
        return errors

    if habit.action is HabitAction.CREATE:
        if not habit.slug or not habit.title:
            errors.append(f"{prefix}: create habit requires slug and title")
        if habit.slug and not SLUG_PATTERN.match(habit.slug):
            errors.append(f"{prefix}: slug {habit.slug!r} must match {SLUG_PATTERN.pattern}")
        if habit.slug and habit.slug in canonical_slugs:
            errors.append(f"{prefix}: slug {habit.slug!r} collides with a canonical role skill")

    return errors


def _canonical_slugs(root: Path | None) -> set[str]:
    if root is None or not root.is_dir():
        return set()
    return {path.name for path in root.iterdir() if path.is_dir() and (path / "SKILL.md").exists()}
