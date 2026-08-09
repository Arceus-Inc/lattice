"""Typed, deterministic evidence clustering for managed reflection."""

from __future__ import annotations

from dataclasses import dataclass

from lattice.contracts.episodic import RawEpisode


@dataclass(frozen=True)
class FailureCategory:
    """Caller-supplied failure category; Lattice does not infer it from prose."""

    code: str

    def __post_init__(self) -> None:
        if not self.code.strip():
            raise ValueError("failure category code must not be blank")


@dataclass(frozen=True)
class TrajectoryEvidence:
    """One concrete trajectory and its caller-classified failure observation."""

    episode: RawEpisode
    failure_category: FailureCategory
    observation: str

    def __post_init__(self) -> None:
        if not self.episode.run_id.strip():
            raise ValueError("trajectory reference must not be blank")
        if not self.observation.strip():
            raise ValueError("failure observation must not be blank")


@dataclass(frozen=True)
class ReflectionCluster:
    """A failure category supported by at least two distinct trajectories."""

    failure_category: FailureCategory
    evidence: tuple[TrajectoryEvidence, ...]

    def __post_init__(self) -> None:
        if len(self.evidence) < 2:
            raise ValueError("reflection clusters require at least two trajectory references")
        if any(item.failure_category != self.failure_category for item in self.evidence):
            raise ValueError("reflection cluster evidence must share one failure category")
        _reject_duplicate_trajectory_refs(self.evidence)

    @property
    def trajectory_refs(self) -> tuple[str, ...]:
        """Provenance references suitable for a Chorus proposal or Podium display."""
        return tuple(item.episode.run_id for item in self.evidence)


def cluster_reflection_evidence(
    evidence: tuple[TrajectoryEvidence, ...],
) -> tuple[ReflectionCluster, ...]:
    """Return only categories with support from at least two distinct trajectories."""
    _reject_duplicate_trajectory_refs(evidence)
    categories: list[FailureCategory] = []
    clusters: list[ReflectionCluster] = []
    for item in evidence:
        if item.failure_category in categories:
            continue
        categories.append(item.failure_category)
        supporting = tuple(
            candidate for candidate in evidence if candidate.failure_category == item.failure_category
        )
        if len(supporting) >= 2:
            clusters.append(ReflectionCluster(failure_category=item.failure_category, evidence=supporting))
    return tuple(clusters)


def _reject_duplicate_trajectory_refs(evidence: tuple[TrajectoryEvidence, ...]) -> None:
    references: list[str] = []
    for item in evidence:
        reference = item.episode.run_id
        if reference in references:
            raise ValueError(f"duplicate trajectory reference: {reference!r}")
        references.append(reference)
