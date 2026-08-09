"""Reflection evidence clustering."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from lattice.contracts.episodic import RawEpisode
from lattice.reflection import (
    MAX_AGENTS_MD_REPLACEMENT_CHARS,
    MAX_SKILL_REPLACEMENT_CHARS,
    MAX_TOOL_DESCRIPTION_REPLACEMENT_CHARS,
    ApplicationAuthorization,
    FailureCategory,
    ReflectionCluster,
    ReflectionDiff,
    ReflectionProposal,
    ReflectionReview,
    ReflectionRunRef,
    ReflectionTargetKind,
    ReplayOutcome,
    ReplayResult,
    ReplaySeverity,
    RepresentativeSuccessEvidence,
    ReviewDecision,
    TrajectoryEvidence,
    cluster_reflection_evidence,
)


def _episode(run_id: str, *, employee_id: str = "agent-a") -> RawEpisode:
    now = datetime.now(UTC)
    return RawEpisode(
        run_id=run_id,
        task_id="task",
        employee_id=employee_id,
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
    proposal_run_id: str = "proposal-run",
    proposal_run_sequence: int = 1,
    target_agent_id: str = "agent-a",
    target_kind: ReflectionTargetKind = ReflectionTargetKind.SKILL,
    target_identity: str = "retry-guidance",
    replacement_text: str = "Do not retry validation errors.",
    rationale: str = "Two runs retried invalid requests.",
    evidence_cluster: ReflectionCluster | None = None,
) -> ReflectionProposal:
    return ReflectionProposal(
        proposal_id="reflection-001",
        proposal_run=ReflectionRunRef(
            run_id=proposal_run_id,
            sequence=proposal_run_sequence,
        ),
        proposing_coach_id="coach-a",
        target_agent_id=target_agent_id,
        target_kind=target_kind,
        target_identity=target_identity,
        replacement_text=replacement_text,
        rationale=rationale,
        evidence_cluster=evidence_cluster or _cluster(),
    )


def _review(
    *,
    decision: ReviewDecision = ReviewDecision.ACCEPTED,
    proposal: ReflectionProposal | None = None,
    reviewer_id: str = "reviewer-a",
) -> ReflectionReview:
    return ReflectionReview(
        proposal=proposal or _proposal(),
        diff=ReflectionDiff(
            before_text="Retry every failed request.",
            after_text="Do not retry validation errors.",
        ),
        reviewer_id=reviewer_id,
        decision=decision,
    )


def _representative_success(run_id: str = "success-run-1") -> RepresentativeSuccessEvidence:
    return RepresentativeSuccessEvidence(episode=_episode(run_id))


def _replay_results(
    *,
    outcome: ReplayOutcome = ReplayOutcome.PRESERVED,
    severity: ReplaySeverity = ReplaySeverity.NON_CRITICAL,
) -> tuple[ReplayResult, ...]:
    return (
        ReplayResult(
            evidence=_representative_success(),
            outcome=outcome,
            severity=severity,
        ),
    )


def _authorization(
    *,
    review: ReflectionReview | None = None,
    application_run_id: str = "application-run",
    application_run_sequence: int = 2,
    replay_results: tuple[ReplayResult, ...] | None = None,
) -> ApplicationAuthorization:
    return ApplicationAuthorization(
        review=review or _review(),
        application_run=ReflectionRunRef(
            run_id=application_run_id,
            sequence=application_run_sequence,
        ),
        replay_results=replay_results or _replay_results(),
    )


def test_proposal_is_immutable_and_retains_exact_cluster_provenance() -> None:
    evidence_cluster = _cluster()
    proposal = _proposal(evidence_cluster=evidence_cluster)

    assert proposal.target_kind is ReflectionTargetKind.SKILL
    assert proposal.evidence_cluster is evidence_cluster
    assert proposal.proposal_run_id == "proposal-run"
    assert proposal.trajectory_refs == ("run-1", "run-2")
    with pytest.raises(AttributeError):
        proposal.rationale = "different rationale"  # type: ignore[misc]


def test_proposal_rejects_self_coaching() -> None:
    with pytest.raises(ValueError, match="must not target the proposing coach"):
        _proposal(target_agent_id="coach-a")


def test_proposal_rejects_evidence_from_another_agent() -> None:
    category = FailureCategory(code="retry-policy")
    foreign_cluster = ReflectionCluster(
        failure_category=category,
        evidence=(
            TrajectoryEvidence(
                episode=_episode("run-1", employee_id="agent-b"),
                failure_category=category,
                observation="The client retried an invalid request.",
            ),
            TrajectoryEvidence(
                episode=_episode("run-2", employee_id="agent-b"),
                failure_category=category,
                observation="The client retried an invalid request again.",
            ),
        ),
    )

    with pytest.raises(ValueError, match="evidence must belong to the target agent"):
        _proposal(evidence_cluster=foreign_cluster)


def test_proposal_requires_a_caller_supplied_target_kind() -> None:
    with pytest.raises(ValueError, match="target kind must be a ReflectionTargetKind"):
        ReflectionProposal(
            proposal_id="reflection-001",
            proposal_run=ReflectionRunRef(run_id="proposal-run", sequence=1),
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
        (
            "  ",
            "coach-a",
            "agent-a",
            "retry-guidance",
            "Do not retry validation errors.",
            "Two runs.",
            "proposal id must not be blank",
        ),
        (
            "reflection-001",
            "  ",
            "agent-a",
            "retry-guidance",
            "Do not retry validation errors.",
            "Two runs.",
            "proposing coach id must not be blank",
        ),
        (
            "reflection-001",
            "coach-a",
            "  ",
            "retry-guidance",
            "Do not retry validation errors.",
            "Two runs.",
            "target agent id must not be blank",
        ),
        (
            "reflection-001",
            "coach-a",
            "agent-a",
            "  ",
            "Do not retry validation errors.",
            "Two runs.",
            "target identity must not be blank",
        ),
        (
            "reflection-001",
            "coach-a",
            "agent-a",
            "retry-guidance",
            "  ",
            "Two runs.",
            "replacement text must not be blank",
        ),
        (
            "reflection-001",
            "coach-a",
            "agent-a",
            "retry-guidance",
            "Do not retry validation errors.",
            "  ",
            "proposal rationale must not be blank",
        ),
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
            proposal_run=ReflectionRunRef(run_id="proposal-run", sequence=1),
            proposing_coach_id=proposing_coach_id,
            target_agent_id=target_agent_id,
            target_kind=ReflectionTargetKind.SKILL,
            target_identity=target_identity,
            replacement_text=replacement_text,
            rationale=rationale,
            evidence_cluster=_cluster(),
        )


def test_proposal_rejects_blank_proposal_run_id() -> None:
    with pytest.raises(ValueError, match="reflection run id must not be blank"):
        _proposal(proposal_run_id="  ")


def test_reflection_proposal_has_no_application_api() -> None:
    assert not hasattr(ReflectionProposal, "apply")
    assert not hasattr(ReflectionProposal, "mutate")


def test_accepted_human_review_mints_application_authorization_with_exact_provenance() -> None:
    proposal = _proposal()
    review = _review(proposal=proposal)
    replay_results = _replay_results()

    authorization = _authorization(review=review, replay_results=replay_results)

    assert authorization.review is review
    assert authorization.proposal is proposal
    assert authorization.proposal_run_id == "proposal-run"
    assert authorization.trajectory_refs == ("run-1", "run-2")
    assert authorization.representative_success_refs == ("success-run-1",)
    assert authorization.replay_results is replay_results


def test_application_authorization_requires_representative_success_replay_results() -> None:
    with pytest.raises(ValueError, match="at least one representative success replay result"):
        ApplicationAuthorization(
            review=_review(),
            application_run=ReflectionRunRef(run_id="application-run", sequence=2),
            replay_results=(),
        )


def test_application_authorization_rejects_duplicate_or_failure_replay_trajectory_references() -> (
    None
):
    duplicate_results = (
        ReplayResult(
            evidence=_representative_success("success-run-1"),
            outcome=ReplayOutcome.PRESERVED,
            severity=ReplaySeverity.NON_CRITICAL,
        ),
        ReplayResult(
            evidence=_representative_success("success-run-1"),
            outcome=ReplayOutcome.PRESERVED,
            severity=ReplaySeverity.NON_CRITICAL,
        ),
    )

    with pytest.raises(ValueError, match="duplicate representative success trajectory reference"):
        _authorization(replay_results=duplicate_results)
    with pytest.raises(
        ValueError, match="must not duplicate proposal failure trajectory reference"
    ):
        _authorization(
            replay_results=(
                ReplayResult(
                    evidence=_representative_success("run-1"),
                    outcome=ReplayOutcome.PRESERVED,
                    severity=ReplaySeverity.NON_CRITICAL,
                ),
            )
        )


def test_critical_replay_regression_blocks_application_authorization() -> None:
    with pytest.raises(ValueError, match="critical replay regression"):
        _authorization(
            replay_results=_replay_results(
                outcome=ReplayOutcome.REGRESSED,
                severity=ReplaySeverity.CRITICAL,
            )
        )


def test_representative_success_evidence_must_belong_to_the_target_agent() -> None:
    foreign_result = ReplayResult(
        evidence=RepresentativeSuccessEvidence(
            episode=_episode("foreign-success", employee_id="agent-b")
        ),
        outcome=ReplayOutcome.PRESERVED,
        severity=ReplaySeverity.NON_CRITICAL,
    )

    with pytest.raises(ValueError, match="success evidence must belong to the target agent"):
        _authorization(replay_results=(foreign_result,))


def test_review_carries_a_visible_before_after_diff() -> None:
    review = _review()

    assert review.diff.before_text == "Retry every failed request."
    assert review.diff.after_text == review.proposal.replacement_text


def test_reflection_diff_rejects_an_unchanged_artifact() -> None:
    with pytest.raises(ValueError, match="must show a change"):
        ReflectionDiff(before_text="unchanged", after_text="unchanged")


def test_review_rejects_a_diff_for_different_replacement_text() -> None:
    with pytest.raises(ValueError, match="must match the proposal replacement text"):
        ReflectionReview(
            proposal=_proposal(),
            diff=ReflectionDiff(before_text="Before", after_text="Different proposal"),
            reviewer_id="reviewer-a",
            decision=ReviewDecision.ACCEPTED,
        )


def test_review_rejects_the_proposing_coach_as_reviewer() -> None:
    with pytest.raises(ValueError, match="reviewer must be independent"):
        _review(reviewer_id="coach-a")


def test_rejected_review_cannot_mint_application_authorization() -> None:
    review = _review(decision=ReviewDecision.REJECTED)

    with pytest.raises(ValueError, match="requires an accepted review"):
        _authorization(review=review)


def test_application_authorization_requires_a_later_application_run() -> None:
    review = _review(proposal=_proposal(proposal_run_sequence=4))

    with pytest.raises(ValueError, match="must be later"):
        _authorization(review=review, application_run_id="earlier-run", application_run_sequence=3)
    with pytest.raises(ValueError, match="must be later"):
        _authorization(
            review=review,
            application_run_id="same-order-run",
            application_run_sequence=4,
        )


@pytest.mark.parametrize(
    ("reviewer_id", "application_run_id", "message"),
    (
        ("  ", "application-run", "reviewer id must not be blank"),
        ("reviewer-a", "  ", "reflection run id must not be blank"),
    ),
)
def test_review_and_authorization_reject_blank_identities(
    reviewer_id: str,
    application_run_id: str,
    message: str,
) -> None:
    if not reviewer_id.strip():
        with pytest.raises(ValueError, match=message):
            _review(reviewer_id=reviewer_id)
    else:
        with pytest.raises(ValueError, match=message):
            _authorization(
                review=_review(reviewer_id=reviewer_id),
                application_run_id=application_run_id,
            )


def test_review_and_authorization_are_immutable_and_have_no_application_api() -> None:
    review = _review()
    application_run = ReflectionRunRef(run_id="application-run", sequence=2)
    representative_success = _representative_success()
    replay_result = ReplayResult(
        evidence=representative_success,
        outcome=ReplayOutcome.PRESERVED,
        severity=ReplaySeverity.NON_CRITICAL,
    )
    authorization = ApplicationAuthorization(
        review=review,
        application_run=application_run,
        replay_results=(replay_result,),
    )

    assert authorization.application_run is application_run
    with pytest.raises(AttributeError):
        review.reviewer_id = "different reviewer"  # type: ignore[misc]
    with pytest.raises(AttributeError):
        application_run.sequence = 3  # type: ignore[misc]
    with pytest.raises(AttributeError):
        representative_success.episode = _episode("other-success")  # type: ignore[misc]
    with pytest.raises(AttributeError):
        replay_result.outcome = ReplayOutcome.REGRESSED  # type: ignore[misc]
    assert not hasattr(ApplicationAuthorization, "apply")
    assert not hasattr(ApplicationAuthorization, "mutate")
