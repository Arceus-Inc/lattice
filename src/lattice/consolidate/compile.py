"""Compile agent-facing patterns and habits into internal ops."""

from __future__ import annotations

from lattice.domain.proposal import (
    HabitAction,
    HabitDraft,
    Op,
    OpKind,
    PatternDraft,
    Proposal,
)


def compile_proposal(proposal: Proposal) -> tuple[Op, ...]:
    """Translate patterns → assert/supersede; habits → patch/draft."""
    ops: list[Op] = []
    for pattern in proposal.patterns:
        ops.append(_compile_pattern(pattern))
    for habit in proposal.habits:
        ops.append(_compile_habit(habit))
    return tuple(ops)


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


def _compile_habit(habit: HabitDraft) -> Op:
    if habit.action is HabitAction.EVOLVE:
        return Op(
            kind=OpKind.PATCH,
            key=habit.skill or "",
            value=habit.body,
            source_run_ids=habit.source_run_ids,
            skill=habit.skill,
            section=habit.section,
        )
    return Op(
        kind=OpKind.DRAFT,
        key=habit.slug or "",
        value=habit.body,
        source_run_ids=habit.source_run_ids,
        slug=habit.slug,
        title=habit.title,
    )
