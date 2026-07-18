"""Deterministic proposal validation — no LLM.

Hermes-aligned habit gates (see docs/research/hermes-skill-granularity-research.md):
- Facts belong in patterns[]; sticky-note / diary content is rejected as habits.
- EVOLVE (patch existing umbrella) is the default path; CREATE is rare and strict.
"""

from __future__ import annotations

import re
from pathlib import Path

from lattice.contracts.episodic import RawEpisode
from lattice.domain.proposal import HabitAction, HabitDraft, PatternDraft, Proposal
from lattice.domain.result import ValidationResult
from lattice.stores.memory_md import MemoryMdStore

KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_.]+$")
SLUG_PATTERN = re.compile(r"^[a-z][a-z0-9-]+$")
MIN_CLAIM_CHARS = 20
MIN_EVOLVE_BODY_CHARS = 200
MIN_CREATE_BODY_CHARS = 500
DEFAULT_MAX_OPS = 20
REQUIRED_CREATE_MARKERS = ("## When to Use", "## Pitfalls")
# Session diary / one-off narrative markers (Hermes #12812 / #23004).
_DIARY_PATTERNS = (
    re.compile(r"\bwe found\b", re.IGNORECASE),
    re.compile(r"\btoday we\b", re.IGNORECASE),
    re.compile(r"\bon \d{4}-\d{2}-\d{2}\b"),
    re.compile(r"\bin this session\b", re.IGNORECASE),
)
# CREATE slugs that look like file-prefix / session artifacts, not class-level names.
_FILE_PREFIX_SLUGS = frozenset({"src", "lib", "app", "pkg", "cmd", "test", "tests"})


def validate_proposal(
    proposal: Proposal,
    *,
    episodes: tuple[RawEpisode, ...],
    atoms: MemoryMdStore,
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
    evolved_slugs = _evolved_slugs(atoms, proposal.employee_id)

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
                known_skill_slugs=canonical_slugs | evolved_slugs,
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

    claim = pattern.claim.strip()
    if len(claim) < MIN_CLAIM_CHARS:
        errors.append(
            f"{prefix}: claim too short ({len(claim)} chars); "
            "write 2–3 plain-English sentences a teammate could read without decoding "
            f"parentheticals or shorthand (min {MIN_CLAIM_CHARS})"
        )

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
    known_skill_slugs: set[str],
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

    body = habit.body.strip()
    if not body:
        errors.append(f"{prefix}: body must not be empty")
        return errors

    diary_hit = _diary_match(body)
    if diary_hit is not None:
        errors.append(
            f"{prefix}: body looks like a one-off diary entry ({diary_hit!r}); "
            "put facts in patterns[] or evolve a class-level procedure — not a session narrative"
        )

    if habit.action is HabitAction.EVOLVE:
        errors.extend(
            _validate_evolve(
                habit,
                prefix,
                body=body,
                known_skill_slugs=known_skill_slugs,
            )
        )
        return errors

    if habit.action is HabitAction.CREATE:
        errors.extend(
            _validate_create(
                habit,
                prefix,
                body=body,
                canonical_slugs=canonical_slugs,
            )
        )

    return errors


def _validate_evolve(
    habit: HabitDraft,
    prefix: str,
    *,
    body: str,
    known_skill_slugs: set[str],
) -> list[str]:
    errors: list[str] = []
    if not habit.skill or not habit.section:
        errors.append(f"{prefix}: evolve habit requires skill and section")
    if habit.skill and not SLUG_PATTERN.match(habit.skill):
        errors.append(f"{prefix}: skill {habit.skill!r} must match {SLUG_PATTERN.pattern}")
    if habit.skill and known_skill_slugs and habit.skill not in known_skill_slugs:
        errors.append(
            f"{prefix}: unknown skill {habit.skill!r}; "
            "evolve targets a canonical role skill or prior evolved overlay"
        )
    if len(body) < MIN_EVOLVE_BODY_CHARS:
        errors.append(
            f"{prefix}: evolve body too short ({len(body)} chars); "
            f"write a procedure section with steps/pitfalls (min {MIN_EVOLVE_BODY_CHARS})"
        )
    return errors


def _validate_create(
    habit: HabitDraft,
    prefix: str,
    *,
    body: str,
    canonical_slugs: set[str],
) -> list[str]:
    errors: list[str] = []
    if not habit.slug or not habit.title:
        errors.append(f"{prefix}: create habit requires slug and title")
    if habit.slug and not SLUG_PATTERN.match(habit.slug):
        errors.append(f"{prefix}: slug {habit.slug!r} must match {SLUG_PATTERN.pattern}")
    if habit.slug and habit.slug in canonical_slugs:
        errors.append(f"{prefix}: slug {habit.slug!r} collides with a canonical role skill")
    if habit.slug and (habit.slug in _FILE_PREFIX_SLUGS or len(habit.slug) < 8):
        errors.append(
            f"{prefix}: slug {habit.slug!r} is not class-level; "
            "prefer a reusable playbook name (e.g. http-retry-playbook), not a file prefix"
        )
    if len(body) < MIN_CREATE_BODY_CHARS:
        errors.append(
            f"{prefix}: create body too short ({len(body)} chars); "
            f"class-level skills need Overview/When to Use/Procedure/Pitfalls "
            f"(min {MIN_CREATE_BODY_CHARS})"
        )
    for marker in REQUIRED_CREATE_MARKERS:
        if marker not in body:
            errors.append(
                f"{prefix}: create body missing {marker!r}; "
                "CREATE is for class-level umbrellas, not sticky notes — prefer EVOLVE"
            )
    return errors


def _diary_match(body: str) -> str | None:
    for pattern in _DIARY_PATTERNS:
        match = pattern.search(body)
        if match is not None:
            return match.group(0)
    return None


def _canonical_slugs(root: Path | None) -> set[str]:
    if root is None or not root.is_dir():
        return set()
    return {path.name for path in root.iterdir() if path.is_dir() and (path / "SKILL.md").exists()}


def _evolved_slugs(atoms: MemoryMdStore, employee_id: str) -> set[str]:
    """Discover prior evolved overlays when the atom store exposes a root path."""
    root = getattr(atoms, "root", None)
    if root is None:
        return set()
    evolved = Path(root) / employee_id / "evolved-skills"
    if not evolved.is_dir():
        return set()
    return {
        path.name
        for path in evolved.iterdir()
        if path.is_dir() and (path / "SKILL.md").exists()
    }
