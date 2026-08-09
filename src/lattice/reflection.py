"""Typed, deterministic evidence clustering for managed reflection."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from lattice.contracts.episodic import RawEpisode

MAX_AGENTS_MD_REPLACEMENT_CHARS = 2_000
MAX_SKILL_REPLACEMENT_CHARS = 4_000
MAX_TOOL_DESCRIPTION_REPLACEMENT_CHARS = 1_000

__all__ = [
    "MAX_AGENTS_MD_REPLACEMENT_CHARS",
    "MAX_SKILL_REPLACEMENT_CHARS",
    "MAX_TOOL_DESCRIPTION_REPLACEMENT_CHARS",
    "FailureCategory",
    "ReflectionCluster",
    "ReflectionProposal",
    "ReflectionTargetKind",
    "TrajectoryEvidence",
    "cluster_reflection_evidence",
]


class ReflectionTargetKind(StrEnum):
    """The caller-selected kind of artifact a reflection proposal addresses."""

    AGENTS_MD = "agents_md"
    SKILL = "skill"
    TOOL_DESCRIPTION = "tool_description"


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


@dataclass(frozen=True)
class ReflectionProposal:
    """An immutable, review-only proposed replacement supported by one cluster."""

    proposal_id: str
    proposing_coach_id: str
    target_agent_id: str
    target_kind: ReflectionTargetKind
    target_identity: str
    replacement_text: str
    rationale: str
    evidence_cluster: ReflectionCluster

    def __post_init__(self) -> None:
        if not self.proposal_id.strip():
            raise ValueError("proposal id must not be blank")
        if not self.proposing_coach_id.strip():
            raise ValueError("proposing coach id must not be blank")
        if not self.target_agent_id.strip():
            raise ValueError("target agent id must not be blank")
        if not isinstance(self.target_kind, ReflectionTargetKind):
            raise ValueError("target kind must be a ReflectionTargetKind")
        if not self.target_identity.strip():
            raise ValueError("target identity must not be blank")
        if self.target_agent_id.strip() == self.proposing_coach_id.strip():
            raise ValueError("reflection proposal must not target the proposing coach")
        if any(
            item.episode.employee_id != self.target_agent_id
            for item in self.evidence_cluster.evidence
        ):
            raise ValueError("reflection proposal evidence must belong to the target agent")
        if not self.replacement_text.strip():
            raise ValueError("replacement text must not be blank")
        if len(self.replacement_text) > _replacement_text_limit(self.target_kind):
            raise ValueError("replacement text exceeds size limit for target kind")
        if not self.rationale.strip():
            raise ValueError("proposal rationale must not be blank")
        if len(self.evidence_cluster.trajectory_refs) < 2:
            raise ValueError("reflection proposals require at least two trajectory references")

    @property
    def trajectory_refs(self) -> tuple[str, ...]:
        """Exact supporting trajectory references from the retained evidence cluster."""
        return self.evidence_cluster.trajectory_refs


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
            candidate
            for candidate in evidence
            if candidate.failure_category == item.failure_category
        )
        if len(supporting) >= 2:
            clusters.append(
                ReflectionCluster(failure_category=item.failure_category, evidence=supporting)
            )
    return tuple(clusters)


def _reject_duplicate_trajectory_refs(evidence: tuple[TrajectoryEvidence, ...]) -> None:
    references: list[str] = []
    for item in evidence:
        reference = item.episode.run_id
        if reference in references:
            raise ValueError(f"duplicate trajectory reference: {reference!r}")
        references.append(reference)


def _replacement_text_limit(target_kind: ReflectionTargetKind) -> int:
    if target_kind is ReflectionTargetKind.AGENTS_MD:
        return MAX_AGENTS_MD_REPLACEMENT_CHARS
    if target_kind is ReflectionTargetKind.SKILL:
        return MAX_SKILL_REPLACEMENT_CHARS
    return MAX_TOOL_DESCRIPTION_REPLACEMENT_CHARS
