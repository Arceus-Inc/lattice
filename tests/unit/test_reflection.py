"""Reflection evidence clustering."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from lattice.contracts.episodic import RawEpisode
from lattice.reflection import (
    MAX_AGENTS_MD_REPLACEMENT_CHARS,
    MAX_SKILL_REPLACEMENT_CHARS,
    MAX_TOOL_DESCRIPTION_REPLACEMENT_CHARS,
    FailureCategory,
    ReflectionCluster,
    ReflectionProposal,
    ReflectionTargetKind,
    TrajectoryEvidence,
    cluster_reflection_evidence,
)


def _episode(run_id: str) -> RawEpisode:
    now = datetime.now(UTC)
    return RawEpisode(
        run_id=run_id,
        task_id="task",
        employee_id="employee",
        role="backend_engineer",
        scope="project",
        intent="update the retry client",
        outcome="failed",
        score=0.0,
        created_at=now,
        recorded_at=now,
        artifacts=("pytest output",),
        files_touched=("src/client.py",),
        body="The retry client did not handle a 429 response.",
    )


def test_clusters_distinct_trajectory_evidence_for_one_failure_category() -> None:
    category = FailureCategory(code="retry-policy")
    evidence = (
        TrajectoryEvidence(
            episode=_episode("run-1"),
            failure_category=category,
            observation="The client retried an invalid request.",
        ),
        TrajectoryEvidence(
            episode=_episode("run-2"),
            failure_category=category,
            observation="The client retried an invalid request again.",
        ),
        TrajectoryEvidence(
            episode=_episode("run-3"),
            failure_category=FailureCategory(code="missing-test"),
            observation="A required regression test was absent.",
        ),
    )

    clusters = cluster_reflection_evidence(evidence)

    assert len(clusters) == 1
    assert clusters[0].failure_category == category
    assert clusters[0].trajectory_refs == ("run-1", "run-2")
    assert clusters[0].evidence == evidence[:2]


def test_does_not_cluster_one_trajectory() -> None:
    evidence = (
        TrajectoryEvidence(
            episode=_episode("run-1"),
            failure_category=FailureCategory(code="retry-policy"),
            observation="The client retried an invalid request.",
        ),
    )

    assert cluster_reflection_evidence(evidence) == ()


def test_rejects_duplicate_trajectory_references() -> None:
    category = FailureCategory(code="retry-policy")
    duplicate = _episode("run-1")
    evidence = (
        TrajectoryEvidence(
            episode=duplicate,
            failure_category=category,
            observation="The client retried an invalid request.",
        ),
        TrajectoryEvidence(
            episode=duplicate,
            failure_category=category,
            observation="The client retried an invalid request again.",
        ),
    )

    try:
        cluster_reflection_evidence(evidence)
    except ValueError as error:
        assert str(error) == "duplicate trajectory reference: 'run-1'"
    else:
        raise AssertionError("duplicate trajectory references must be rejected")


def test_rejects_whitespace_only_trajectory_references() -> None:
    with pytest.raises(ValueError, match="trajectory reference must not be blank"):
        TrajectoryEvidence(
            episode=_episode("  \t"),
            failure_category=FailureCategory(code="retry-policy"),
            observation="The client retried an invalid request.",
        )


def _cluster() -> ReflectionCluster:
    category = FailureCategory(code="retry-policy")
    return ReflectionCluster(
        failure_category=category,
        evidence=(
            TrajectoryEvidence(
                episode=_episode("run-1"),
                failure_category=category,
                observation="The client retried an invalid request.",
            ),
            TrajectoryEvidence(
                episode=_episode("run-2"),
                failure_category=category,
                observation="The client retried an invalid request again.",
            ),
        ),
    )


def _proposal(
    *,
    target_agent_id: str = "agent-a",
    target_kind: ReflectionTargetKind = ReflectionTargetKind.SKILL,
    target_identity: str = "retry-guidance",
    replacement_text: str = "Do not retry validation errors.",
    rationale: str = "Two runs retried invalid requests.",
    evidence_cluster: ReflectionCluster | None = None,
) -> ReflectionProposal:
    return ReflectionProposal(
        proposal_id="reflection-001",
        proposing_coach_id="coach-a",
        target_agent_id=target_agent_id,
        target_kind=target_kind,
        target_identity=target_identity,
        replacement_text=replacement_text,
        rationale=rationale,
        evidence_cluster=evidence_cluster or _cluster(),
    )


def test_proposal_is_immutable_and_retains_exact_cluster_provenance() -> None:
    evidence_cluster = _cluster()
    proposal = _proposal(evidence_cluster=evidence_cluster)

    assert proposal.target_kind is ReflectionTargetKind.SKILL
    assert proposal.evidence_cluster is evidence_cluster
    assert proposal.trajectory_refs == ("run-1", "run-2")
    with pytest.raises(AttributeError):
        proposal.rationale = "different rationale"  # type: ignore[misc]


def test_proposal_rejects_self_coaching() -> None:
    with pytest.raises(ValueError, match="must not target the proposing coach"):
        _proposal(target_agent_id="coach-a")


def test_proposal_requires_a_caller_supplied_target_kind() -> None:
    with pytest.raises(ValueError, match="target kind must be a ReflectionTargetKind"):
        ReflectionProposal(
            proposal_id="reflection-001",
            proposing_coach_id="coach-a",
            target_agent_id="agent-a",
            target_kind="skill",  # type: ignore[arg-type]
            target_identity="retry-guidance",
            replacement_text="Do not retry validation errors.",
            rationale="Two runs retried invalid requests.",
            evidence_cluster=_cluster(),
        )


@pytest.mark.parametrize(
    ("target_kind", "limit"),
    (
        (ReflectionTargetKind.AGENTS_MD, MAX_AGENTS_MD_REPLACEMENT_CHARS),
        (ReflectionTargetKind.SKILL, MAX_SKILL_REPLACEMENT_CHARS),
        (ReflectionTargetKind.TOOL_DESCRIPTION, MAX_TOOL_DESCRIPTION_REPLACEMENT_CHARS),
    ),
)
def test_proposal_enforces_target_replacement_size_limits(
    target_kind: ReflectionTargetKind,
    limit: int,
) -> None:
    assert _proposal(target_kind=target_kind, replacement_text="x" * limit).replacement_text
    with pytest.raises(ValueError, match="replacement text exceeds size limit"):
        _proposal(target_kind=target_kind, replacement_text="x" * (limit + 1))


@pytest.mark.parametrize(
    (
        "proposal_id",
        "proposing_coach_id",
        "target_agent_id",
        "target_identity",
        "replacement_text",
        "rationale",
        "message",
    ),
    (
        ("  ", "coach-a", "agent-a", "retry-guidance", "Do not retry validation errors.", "Two runs.", "proposal id must not be blank"),
        ("reflection-001", "  ", "agent-a", "retry-guidance", "Do not retry validation errors.", "Two runs.", "proposing coach id must not be blank"),
        ("reflection-001", "coach-a", "  ", "retry-guidance", "Do not retry validation errors.", "Two runs.", "target agent id must not be blank"),
        ("reflection-001", "coach-a", "agent-a", "  ", "Do not retry validation errors.", "Two runs.", "target identity must not be blank"),
        ("reflection-001", "coach-a", "agent-a", "retry-guidance", "  ", "Two runs.", "replacement text must not be blank"),
        ("reflection-001", "coach-a", "agent-a", "retry-guidance", "Do not retry validation errors.", "  ", "proposal rationale must not be blank"),
    ),
)
def test_proposal_rejects_blank_required_text(
    proposal_id: str,
    proposing_coach_id: str,
    target_agent_id: str,
    target_identity: str,
    replacement_text: str,
    rationale: str,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        ReflectionProposal(
            proposal_id=proposal_id,
            proposing_coach_id=proposing_coach_id,
            target_agent_id=target_agent_id,
            target_kind=ReflectionTargetKind.SKILL,
            target_identity=target_identity,
            replacement_text=replacement_text,
            rationale=rationale,
            evidence_cluster=_cluster(),
        )


def test_reflection_proposal_has_no_application_api() -> None:
    assert not hasattr(ReflectionProposal, "apply")
    assert not hasattr(ReflectionProposal, "mutate")
