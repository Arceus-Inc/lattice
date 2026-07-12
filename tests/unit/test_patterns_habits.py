"""Pattern and habit compile + apply."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from lattice.compile import compile_proposal
from lattice.compose import build_default
from lattice.contracts.episodic import RawEpisode
from lattice.domain.packet import HabitHintAction, HintKind
from lattice.domain.proposal import HabitAction, HabitDraft, OpKind, PatternDraft, Proposal


class _Reader:
    def __init__(self, episodes: tuple[RawEpisode, ...]) -> None:
        self._episodes = episodes

    def records_for(self, employee_id: str) -> tuple[RawEpisode, ...]:
        return tuple(ep for ep in self._episodes if ep.employee_id == employee_id)

    def count_for(self, employee_id: str) -> int:
        return len(self.records_for(employee_id))


def _episode(run_id: str) -> RawEpisode:
    now = datetime.now(UTC)
    return RawEpisode(
        run_id=run_id,
        task_id="t",
        employee_id="e1",
        role="backend_engineer",
        scope="project",
        intent="retry",
        outcome="done",
        score=1.0,
        created_at=now,
        recorded_at=now,
        artifacts=(),
        files_touched=("src/api/client.py",),
        body="loaded structuring-any-service skill",
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


def test_compile_pattern_and_habit() -> None:
    proposal = Proposal(
        employee_id="e1",
        patterns=(PatternDraft(key="api.retry", claim="backoff", source_run_ids=("r1",)),),
        habits=(
            HabitDraft(
                action=HabitAction.EVOLVE,
                skill="structuring-any-service",
                section="Before patching",
                body=_evolve_body(),
                source_run_ids=("r1",),
            ),
            HabitDraft(
                action=HabitAction.CREATE,
                slug="http-retry-playbook",
                title="HTTP retry playbook",
                body=_create_body(),
                source_run_ids=("r1",),
            ),
        ),
    )
    ops = compile_proposal(proposal)
    assert ops[0].kind is OpKind.ASSERT
    assert ops[1].kind is OpKind.PATCH
    assert ops[2].kind is OpKind.DRAFT


def test_habit_evolve_and_create(tmp_path: Path) -> None:
    episodes = (_episode("r1"), _episode("r2"))
    lattice = build_default(
        consolidated_root=tmp_path,
        episodes=_Reader(episodes),
        enable_patches=True,
        min_new_episodes=2,
        min_cluster_size=2,
    )
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
    result = lattice.apply(proposal)
    assert result.ok is True, result.errors
    assert result.patches_written == 1
    skill_path = tmp_path / "e1" / "evolved-skills" / "http-retry-playbook" / "SKILL.md"
    assert skill_path.exists()
    text = skill_path.read_text(encoding="utf-8")
    assert text.startswith("---")
    assert "name: http-retry-playbook" in text
    assert "HTTP retry playbook" in text or "When to Use" in text


def test_rejects_canonical_skill_collision(tmp_path: Path) -> None:
    canonical = tmp_path / "canonical"
    skill_dir = canonical / "structuring-any-service"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# canonical\n", encoding="utf-8")

    episodes = (_episode("r1"),)
    lattice = build_default(
        consolidated_root=tmp_path / "store",
        episodes=_Reader(episodes),
        enable_patches=True,
        canonical_skills_root=canonical,
    )
    proposal = Proposal(
        employee_id="e1",
        habits=(
            HabitDraft(
                action=HabitAction.CREATE,
                slug="structuring-any-service",
                title="Collision",
                body=_create_body(),
                source_run_ids=("r1",),
            ),
        ),
    )
    validation = lattice.validate(proposal)
    assert validation.ok is False
    assert any("collides with a canonical" in err for err in validation.errors)


def test_packet_emits_pattern_and_habit_hints(tmp_path: Path) -> None:
    episodes = (_episode("r1"), _episode("r2"))
    lattice = build_default(
        consolidated_root=tmp_path,
        episodes=_Reader(episodes),
        min_new_episodes=2,
        min_cluster_size=2,
    )
    packet = lattice.packet("e1")
    assert packet is not None
    kinds = {hint.kind for hint in packet.hints}
    assert HintKind.PATTERN in kinds
    assert HintKind.HABIT in kinds
    habit_hints = [h for h in packet.hints if h.kind is HintKind.HABIT]
    assert all(h.suggested_action is HabitHintAction.EVOLVE for h in habit_hints)
