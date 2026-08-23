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
    "ApplicationAuthorization",
    "FailureCategory",
    "ReflectionCluster",
    "ReflectionDiff",
    "ReflectionProposal",
    "ReflectionReview",
    "ReflectionRunRef",
    "ReflectionTargetKind",
    "ReplayOutcome",
    "ReplayResult",
    "ReplaySeverity",
    "RepresentativeSuccessEvidence",
    "ReviewDecision",
    "TrajectoryEvidence",
    "cluster_reflection_evidence",
]


class ReflectionTargetKind(StrEnum):
    """The caller-selected kind of artifact a reflection proposal addresses."""

    AGENTS_MD = "agents_md"
    SKILL = "skill"
    TOOL_DESCRIPTION = "tool_description"


class ReviewDecision(StrEnum):
    """A human review outcome for a reflection proposal."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"


class ReplayOutcome(StrEnum):
    """Caller-supplied result of replaying a representative success."""

    PRESERVED = "preserved"
    REGRESSED = "regressed"


class ReplaySeverity(StrEnum):
    """Caller-supplied severity of a replay outcome."""

    NON_CRITICAL = "non_critical"
    CRITICAL = "critical"


@dataclass(frozen=True)
class ReflectionRunRef:
    """A run identity plus its trusted monotonic order in one execution lineage."""

    run_id: str
    sequence: int

    def __post_init__(self) -> None:
        if not self.run_id.strip():
            raise ValueError("reflection run id must not be blank")
        if self.sequence < 0:
            raise ValueError("reflection run sequence must be nonnegative")


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
class RepresentativeSuccessEvidence:
    """A caller-designated past success retained as replay provenance."""

    episode: RawEpisode

    def __post_init__(self) -> None:
        if not self.episode.run_id.strip():
            raise ValueError("representative success trajectory reference must not be blank")

    @property
    def trajectory_ref(self) -> str:
        """Exact trajectory reference for this representative success."""
        return self.episode.run_id


@dataclass(frozen=True)
class ReplayResult:
    """A typed replay assessment for one representative success trajectory."""

    evidence: RepresentativeSuccessEvidence
    outcome: ReplayOutcome
    severity: ReplaySeverity

    def __post_init__(self) -> None:
        if not isinstance(self.outcome, ReplayOutcome):
            raise ValueError("replay outcome must be a ReplayOutcome")
        if not isinstance(self.severity, ReplaySeverity):
            raise ValueError("replay severity must be a ReplaySeverity")

    @property
    def trajectory_ref(self) -> str:
        """Exact representative success provenance used for this replay."""
        return self.evidence.trajectory_ref

    @property
    def is_critical_regression(self) -> bool:
        """Whether this caller-supplied assessment blocks authorization."""
        return self.outcome is ReplayOutcome.REGRESSED and self.severity is ReplaySeverity.CRITICAL


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
    proposal_run: ReflectionRunRef
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

    @property
    def proposal_run_id(self) -> str:
        """Run that authored the proposal."""
        return self.proposal_run.run_id


@dataclass(frozen=True)
class ReflectionDiff:
    """The human-visible artifact change considered during review."""

    before_text: str
    after_text: str

    def __post_init__(self) -> None:
        if self.before_text == self.after_text:
            raise ValueError("reflection diff must show a change")


@dataclass(frozen=True)
class ReflectionReview:
    """An immutable human decision over one proposal and its visible diff."""

    proposal: ReflectionProposal
    diff: ReflectionDiff
    reviewer_id: str
    decision: ReviewDecision

    def __post_init__(self) -> None:
        if not self.reviewer_id.strip():
            raise ValueError("reviewer id must not be blank")
        if self.reviewer_id.strip() == self.proposal.proposing_coach_id.strip():
            raise ValueError("reflection reviewer must be independent from the proposing coach")
        if not isinstance(self.decision, ReviewDecision):
            raise ValueError("review decision must be a ReviewDecision")
        if self.diff.after_text != self.proposal.replacement_text:
            raise ValueError("review diff after text must match the proposal replacement text")

    @property
    def proposal_run_id(self) -> str:
        """Run that authored the reviewed proposal."""
        return self.proposal.proposal_run_id

    @property
    def trajectory_refs(self) -> tuple[str, ...]:
        """Exact evidence provenance retained by the reviewed proposal."""
        return self.proposal.trajectory_refs


@dataclass(frozen=True)
class ApplicationAuthorization:
    """An accepted human review cleared for a later application run."""

    review: ReflectionReview
    application_run: ReflectionRunRef
    replay_results: tuple[ReplayResult, ...]

    def __post_init__(self) -> None:
        if self.review.decision is not ReviewDecision.ACCEPTED:
            raise ValueError("application authorization requires an accepted review")
        if self.application_run.sequence <= self.review.proposal.proposal_run.sequence:
            raise ValueError("application run must be later than the proposal run")
        if not self.replay_results:
            raise ValueError(
                "application authorization requires at least one representative success replay result"
            )
        _reject_duplicate_replay_trajectory_refs(self.replay_results)
        failure_refs = self.review.trajectory_refs
        if any(result.trajectory_ref in failure_refs for result in self.replay_results):
            raise ValueError(
                "representative success trajectory reference must not duplicate proposal failure "
                "trajectory reference"
            )
        target_agent_id = self.review.proposal.target_agent_id
        if any(
            result.evidence.episode.employee_id != target_agent_id for result in self.replay_results
        ):
            raise ValueError("representative success evidence must belong to the target agent")
        if any(result.is_critical_regression for result in self.replay_results):
            raise ValueError("critical replay regression blocks application authorization")

    @property
    def proposal(self) -> ReflectionProposal:
        """Reviewed proposal, including its exact evidence provenance."""
        return self.review.proposal

    @property
    def proposal_run_id(self) -> str:
        """Run that authored the reviewed proposal."""
        return self.review.proposal_run_id

    @property
    def application_run_id(self) -> str:
        """Later run authorized to apply the reviewed proposal."""
        return self.application_run.run_id

    @property
    def trajectory_refs(self) -> tuple[str, ...]:
        """Exact evidence provenance retained by the accepted review."""
        return self.review.trajectory_refs

    @property
    def representative_success_refs(self) -> tuple[str, ...]:
        """Exact replayed representative success provenance."""
        return tuple(result.trajectory_ref for result in self.replay_results)


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


def _reject_duplicate_replay_trajectory_refs(results: tuple[ReplayResult, ...]) -> None:
    references: list[str] = []
    for result in results:
        reference = result.trajectory_ref
        if reference in references:
            raise ValueError(
                f"duplicate representative success trajectory reference: {reference!r}"
            )
        references.append(reference)


def _replacement_text_limit(target_kind: ReflectionTargetKind) -> int:
    if target_kind is ReflectionTargetKind.AGENTS_MD:
        return MAX_AGENTS_MD_REPLACEMENT_CHARS
    if target_kind is ReflectionTargetKind.SKILL:
        return MAX_SKILL_REPLACEMENT_CHARS
    return MAX_TOOL_DESCRIPTION_REPLACEMENT_CHARS
