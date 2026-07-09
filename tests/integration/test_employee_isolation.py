"""E2E-06 — cross-employee isolation."""

from __future__ import annotations

from pathlib import Path

from lattice.compose import build_default
from lattice.domain.proposal import PatternDraft, Proposal
from tests.integration.conftest import _GrowingReader, make_episode


def test_cross_employee_run_id_rejected(tmp_path: Path) -> None:
    episodes = (
        make_episode(run_id="r_be", employee_id="e_be_1"),
        make_episode(run_id="r_fe", employee_id="e_fe_1", files_touched=("src/ui/app.tsx",)),
    )
    lattice = build_default(
        consolidated_root=tmp_path,
        episodes=_GrowingReader(list(episodes)),
    )

    proposal = Proposal(
        employee_id="e_fe_1",
        patterns=(
            PatternDraft(
                key="api.retry",
                claim="HTTP client retries use exponential backoff capped at 30s",
                source_run_ids=("r_be",),
            ),
        ),
    )
    validation = lattice.validate(proposal)
    assert validation.ok is False
    assert any("unknown source_run_id" in err for err in validation.errors)


def test_context_is_per_employee(tmp_path: Path) -> None:
    episodes = (
        make_episode(run_id="r_be", employee_id="e_be_1"),
        make_episode(run_id="r_fe", employee_id="e_fe_1", files_touched=("src/ui/app.tsx",)),
    )
    lattice = build_default(
        consolidated_root=tmp_path,
        episodes=_GrowingReader(list(episodes)),
        min_new_episodes=1,
        min_cluster_size=1,
    )

    lattice.apply(
        Proposal(
            employee_id="e_be_1",
            patterns=(
                PatternDraft(
                    key="api.retry",
                    claim="HTTP client retries use exponential backoff capped at 30s",
                    source_run_ids=("r_be",),
                ),
            ),
        )
    )

    be_context = lattice.context("e_be_1", "retry")
    fe_context = lattice.context("e_fe_1", "retry")

    assert "api.retry" in be_context
    assert "api.retry" not in fe_context
