"""E2E-07 — validation rejection matrix."""

from __future__ import annotations

from pathlib import Path

from lattice.compose import build_default
from lattice.domain.proposal import PatternDraft, Proposal
from tests.integration.conftest import _GrowingReader, make_episode, valid_retry_proposal


def _lattice_with_one_episode(tmp_path: Path):
    episodes = [make_episode(run_id="r1")]
    return build_default(
        consolidated_root=tmp_path,
        episodes=_GrowingReader(episodes),
        min_new_episodes=1,
        min_cluster_size=1,
    )


def test_rejects_empty_patterns(tmp_path: Path) -> None:
    lattice = _lattice_with_one_episode(tmp_path)
    result = lattice.validate(Proposal(employee_id="e_be_1", patterns=()))
    assert result.ok is False
    assert any("at least one pattern" in e for e in result.errors)


def test_rejects_too_many_patterns(tmp_path: Path) -> None:
    lattice = _lattice_with_one_episode(tmp_path)
    patterns = tuple(
        PatternDraft(
            key=f"key.{i}",
            claim="x" * 20,
            source_run_ids=("r1",),
        )
        for i in range(21)
    )
    result = lattice.validate(Proposal(employee_id="e_be_1", patterns=patterns))
    assert result.ok is False
    assert any("exceeds max patterns" in e for e in result.errors)


def test_rejects_empty_source_run_ids(tmp_path: Path) -> None:
    lattice = _lattice_with_one_episode(tmp_path)
    proposal = Proposal(
        employee_id="e_be_1",
        patterns=(PatternDraft(key="api.retry", claim="x" * 20, source_run_ids=()),),
    )
    result = lattice.validate(proposal)
    assert result.ok is False
    assert any("at least one source_run_id" in e for e in result.errors)


def test_rejects_unknown_run_id(tmp_path: Path) -> None:
    lattice = _lattice_with_one_episode(tmp_path)
    proposal = valid_retry_proposal(run_ids=("ghost",))
    result = lattice.validate(proposal)
    assert result.ok is False
    assert any("unknown source_run_id" in e for e in result.errors)


def test_rejects_invalid_key(tmp_path: Path) -> None:
    lattice = _lattice_with_one_episode(tmp_path)
    proposal = Proposal(
        employee_id="e_be_1",
        patterns=(
            PatternDraft(key="API.Retry", claim="x" * 20, source_run_ids=("r1",)),
        ),
    )
    result = lattice.validate(proposal)
    assert result.ok is False
    assert any("must match" in e for e in result.errors)


def test_rejects_short_claim(tmp_path: Path) -> None:
    lattice = _lattice_with_one_episode(tmp_path)
    proposal = Proposal(
        employee_id="e_be_1",
        patterns=(PatternDraft(key="api.retry", claim="short", source_run_ids=("r1",)),),
    )
    result = lattice.validate(proposal)
    assert result.ok is False
    assert any("claim too short" in e for e in result.errors)


def test_rejects_duplicate_active_key(tmp_path: Path) -> None:
    lattice = _lattice_with_one_episode(tmp_path)
    lattice.apply(valid_retry_proposal(run_ids=("r1",)))

    proposal = valid_retry_proposal(run_ids=("r1",))
    result = lattice.validate(proposal)
    assert result.ok is False
    assert any("already active" in e for e in result.errors)


def test_rejects_invalid_supersedes(tmp_path: Path) -> None:
    lattice = _lattice_with_one_episode(tmp_path)
    proposal = valid_retry_proposal(run_ids=("r1",), supersedes="missing.key")
    result = lattice.validate(proposal)
    assert result.ok is False
    assert any("is not active" in e for e in result.errors)
