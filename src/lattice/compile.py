"""Compile agent-facing patterns into internal ops."""

from __future__ import annotations

from lattice.domain.proposal import Op, OpKind, PatternDraft, Proposal


def compile_proposal(proposal: Proposal) -> tuple[Op, ...]:
    """Translate patterns → assert/supersede ops."""
    return tuple(_compile_pattern(pattern) for pattern in proposal.patterns)


def _compile_pattern(pattern: PatternDraft) -> Op:
    if pattern.supersedes is not None:
        return Op(
            kind=OpKind.SUPERSEDE,
            key=pattern.key,
            value=pattern.claim,
            source_run_ids=pattern.source_run_ids,
            supersedes=pattern.supersedes,
        )
    return Op(
        kind=OpKind.ASSERT,
        key=pattern.key,
        value=pattern.claim,
        source_run_ids=pattern.source_run_ids,
    )
