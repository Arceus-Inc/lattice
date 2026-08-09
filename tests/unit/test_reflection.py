"""Reflection evidence clustering."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from lattice.contracts.episodic import RawEpisode
from lattice.reflection import FailureCategory, TrajectoryEvidence, cluster_reflection_evidence


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
