"""Hermes-aligned habit validation — EVOLVE-first, CREATE rare, no diary skills."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from lattice.compose import build_default
from lattice.contracts.episodic import RawEpisode
from lattice.domain.proposal import HabitAction, HabitDraft, Proposal


class _Reader:
    def __init__(self, episodes: tuple[RawEpisode, ...]) -> None:
        self._episodes = episodes

    def records_for(self, employee_id: str) -> tuple[RawEpisode, ...]:
        return tuple(ep for ep in self._episodes if ep.employee_id == employee_id)

    def count_for(self, employee_id: str) -> int:
        return len(self.records_for(employee_id))


def _episode(run_id: str, *, outcome: str = "done") -> RawEpisode:
    now = datetime.now(UTC)
    return RawEpisode(
        run_id=run_id,
        task_id="t",
        employee_id="e1",
        role="backend_engineer",
        scope="project",
        intent="retry",
        outcome=outcome,
        score=1.0,
        created_at=now,
        recorded_at=now,
        artifacts=(),
        files_touched=("src/api/client.py",),
        body="beat",
    )


def _evolve_body() -> str:
    return (
        "## Before patching HTTP clients\n\n"
        "1. Call `get_run(run_id)` for each cited beat and recall the failure shape.\n"
        "2. Classify transient (429/503) versus logic error before editing.\n"
        "3. Only then edit `src/api/client.py`.\n\n"
        "## Pitfalls\n"
        "- Patching without reading prior beat prose repeats the same mistake.\n\n"
        "## Verification\n"
        "- `test_evidence` passes after the patch.\n"
    )


def _create_body() -> str:
    return (
        "## Overview\n"
        "Class-level playbook for HTTP client retry work across services.\n"
        "Use this when the agent must implement durable retry behaviour, not one-off greps.\n\n"
        "## When to Use\n"
        "- Implementing or fixing HTTP retry / backoff behaviour.\n"
        "- Do not use for one-off log greps or billing investigations.\n\n"
        "## Procedure\n"
        "1. Recall prior failure shape via `get_run`.\n"
        "2. Classify transient vs logic error.\n"
        "3. Patch client, then verify with `test_evidence`.\n\n"
        "## Pitfalls\n"
        "- Treating session-specific counts as durable policy.\n\n"
        "## Verification\n"
        "- Green `test_evidence` bundle on disk.\n"
    )


def _lattice(tmp_path: Path, *, canonical: Path | None = None):
    return build_default(
        consolidated_root=tmp_path / "store",
        episodes=_Reader((_episode("r1"), _episode("r2"))),
        enable_patches=True,
        canonical_skills_root=canonical,
        min_new_episodes=1,
        min_cluster_size=1,
    )


def test_accepts_evolve_into_canonical_skill(tmp_path: Path) -> None:
    canonical = tmp_path / "canonical"
    skill = canonical / "structuring-any-service"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# structuring\n", encoding="utf-8")

    lattice = _lattice(tmp_path, canonical=canonical)
    proposal = Proposal(
        employee_id="e1",
        habits=(
            HabitDraft(
                action=HabitAction.EVOLVE,
                skill="structuring-any-service",
                section="Before patching HTTP clients",
                body=_evolve_body(),
                source_run_ids=("r1", "r2"),
            ),
        ),
    )
    validation = lattice.validate(proposal)
    assert validation.ok is True, validation.errors


def test_rejects_short_evolve_body(tmp_path: Path) -> None:
    canonical = tmp_path / "canonical"
    skill = canonical / "structuring-any-service"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# structuring\n", encoding="utf-8")

    lattice = _lattice(tmp_path, canonical=canonical)
    proposal = Proposal(
        employee_id="e1",
        habits=(
            HabitDraft(
                action=HabitAction.EVOLVE,
                skill="structuring-any-service",
                section="Before patching",
                body="Recall failure shape.",
                source_run_ids=("r1",),
            ),
        ),
    )
    validation = lattice.validate(proposal)
    assert validation.ok is False
    assert any("too short" in err for err in validation.errors)


def test_rejects_diary_habit_body(tmp_path: Path) -> None:
    canonical = tmp_path / "canonical"
    skill = canonical / "structuring-any-service"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# structuring\n", encoding="utf-8")

    lattice = _lattice(tmp_path, canonical=canonical)
    diary = (
        "## Before patching\n\n"
        "Today we found 86 calls to Gemini on 2026-04-18 while grepping logs.\n"
        "This is what we discovered in this session about billing.\n"
        "Always recall the failure shape before patching the client.\n"
        "Classify transient versus logic errors carefully every time.\n"
    )
    proposal = Proposal(
        employee_id="e1",
        habits=(
            HabitDraft(
                action=HabitAction.EVOLVE,
                skill="structuring-any-service",
                section="Before patching",
                body=diary,
                source_run_ids=("r1",),
            ),
        ),
    )
    validation = lattice.validate(proposal)
    assert validation.ok is False
    assert any("diary" in err.lower() or "one-off" in err.lower() for err in validation.errors)


def test_rejects_evolve_unknown_skill_when_canonical_configured(tmp_path: Path) -> None:
    canonical = tmp_path / "canonical"
    skill = canonical / "structuring-any-service"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# structuring\n", encoding="utf-8")

    lattice = _lattice(tmp_path, canonical=canonical)
    proposal = Proposal(
        employee_id="e1",
        habits=(
            HabitDraft(
                action=HabitAction.EVOLVE,
                skill="does-not-exist",
                section="Before patching",
                body=_evolve_body(),
                source_run_ids=("r1",),
            ),
        ),
    )
    validation = lattice.validate(proposal)
    assert validation.ok is False
    assert any("unknown skill" in err for err in validation.errors)


def test_rejects_short_create_without_sections(tmp_path: Path) -> None:
    lattice = _lattice(tmp_path)
    proposal = Proposal(
        employee_id="e1",
        habits=(
            HabitDraft(
                action=HabitAction.CREATE,
                slug="retry-discipline",
                title="Retry discipline",
                body="Recall failure shape before patching.",
                source_run_ids=("r1", "r2"),
            ),
        ),
    )
    validation = lattice.validate(proposal)
    assert validation.ok is False
    assert any("too short" in err or "When to Use" in err for err in validation.errors)


def test_accepts_class_level_create(tmp_path: Path) -> None:
    lattice = _lattice(tmp_path)
    proposal = Proposal(
        employee_id="e1",
        habits=(
            HabitDraft(
                action=HabitAction.CREATE,
                slug="http-retry-playbook",
                title="HTTP retry playbook",
                body=_create_body(),
                source_run_ids=("r1", "r2"),
            ),
        ),
    )
    validation = lattice.validate(proposal)
    assert validation.ok is True, validation.errors


def test_rejects_file_prefix_create_slug(tmp_path: Path) -> None:
    lattice = _lattice(tmp_path)
    proposal = Proposal(
        employee_id="e1",
        habits=(
            HabitDraft(
                action=HabitAction.CREATE,
                slug="src",
                title="Src",
                body=_create_body(),
                source_run_ids=("r1", "r2"),
            ),
        ),
    )
    validation = lattice.validate(proposal)
    assert validation.ok is False
    assert any("class-level" in err or "too short" in err for err in validation.errors)
