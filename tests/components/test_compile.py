"""compile.py — PatternDraft → ASSERT/SUPERSEDE ops."""

from __future__ import annotations

from lattice.consolidate.compile import compile_proposal
from lattice.domain.proposal import OpKind, PatternDraft, Proposal


def test_compile_assert_op() -> None:
    proposal = Proposal(
        employee_id="e1",
        patterns=(
            PatternDraft(
                key="api.retry",
                claim="HTTP retries use exponential backoff capped at 30s",
                source_run_ids=("r1", "r2"),
            ),
        ),
    )
    ops = compile_proposal(proposal)
    assert len(ops) == 1
    assert ops[0].kind is OpKind.ASSERT
    assert ops[0].key == "api.retry"
    assert ops[0].supersedes is None


def test_compile_supersede_op() -> None:
    proposal = Proposal(
        employee_id="e1",
        patterns=(
            PatternDraft(
                key="api.retry",
                claim="HTTP retries use exponential backoff capped at 60s",
                source_run_ids=("r3",),
                supersedes="api.retry",
            ),
        ),
    )
    ops = compile_proposal(proposal)
    assert ops[0].kind is OpKind.SUPERSEDE
    assert ops[0].supersedes == "api.retry"
