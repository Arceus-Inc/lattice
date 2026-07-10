"""adjudicate.py — outcome-grounded Beta updates."""

from __future__ import annotations

from datetime import UTC, datetime

from lattice.adjudicate import (
    adjudicate_atom,
    apply_episode_to_stats,
    fingerprint_overlap,
    key_files_for_atom,
)
from lattice.contracts.atom import Atom
from lattice.contracts.episodic import RawEpisode
from lattice.domain.stats import DEFAULT_ADJUDICATION_PARAMS, PatternStats, Tier
from tests.integration.conftest import BeatSimulator, make_episode, valid_retry_proposal


def _append_retry_cluster(sim: BeatSimulator, *, count: int = 5) -> tuple[str, ...]:
    run_ids = tuple(f"r_b{i}" for i in range(1, count + 1))
    for run_id in run_ids:
        sim.append_beat(make_episode(run_id=run_id))
    return run_ids


def _episode(
    *,
    run_id: str,
    outcome: str = "done",
    files: tuple[str, ...] = ("src/api/client.py",),
) -> RawEpisode:
    return make_episode(run_id=run_id, outcome=outcome, files_touched=files)


def test_same_domain_done_promotes_to_rule() -> None:
    stats = PatternStats.jeffreys_prior()
    key_files = frozenset({"src/api/client.py"})
    for run_id in ("r1", "r2", "r3"):
        stats = apply_episode_to_stats(
            stats,
            _episode(run_id=run_id, outcome="done"),
            key_files,
        )
    assert stats.tier == Tier.RULE
    assert stats.lcb05 > DEFAULT_ADJUDICATION_PARAMS.theta_star


def test_cross_domain_failure_lowers_lcb() -> None:
    stats = PatternStats(alpha_own=3.0, beta_own=0.5, tier=Tier.RULE)
    key_files = frozenset({"src/api/client.py"})
    before = stats.lcb05
    after = apply_episode_to_stats(
        stats,
        _episode(run_id="design", outcome="incomplete", files=("design/tokens.yaml",)),
        key_files,
    )
    assert after.beta_own > stats.beta_own
    assert after.lcb05 < before


def test_irrelevant_done_skips_update() -> None:
    stats = PatternStats.jeffreys_prior()
    key_files = frozenset({"src/api/client.py"})
    after = apply_episode_to_stats(
        stats,
        _episode(run_id="other", outcome="done", files=("docs/readme.md",)),
        key_files,
    )
    assert after.alpha_own == stats.alpha_own
    assert after.beta_own == stats.beta_own


def test_adjudicate_runs_without_gate_open(tmp_path) -> None:
    """Fresh episodes + active atoms update even when gate is closed."""
    sim = BeatSimulator(consolidated_root=tmp_path)
    _append_retry_cluster(sim)

    proposal = valid_retry_proposal()
    assert sim.lattice.apply(proposal).ok
    assert sim.lattice.gate_open("e_be_1") is False

    sim.append_beat(
        make_episode(
            run_id="r6",
            outcome="incomplete",
            files_touched=("design/tokens.yaml",),
        )
    )

    result = sim.lattice.adjudicate("e_be_1")
    assert result.episodes_processed >= 1
    assert result.atoms_updated >= 1

    memory_md = tmp_path / "e_be_1" / "MEMORY.md"
    assert memory_md.exists()
    assert "LCB" in memory_md.read_text()


def test_memory_md_format_snapshot(tmp_path) -> None:
    sim = BeatSimulator(consolidated_root=tmp_path)
    for run_id in ("r1", "r2", "r3"):
        sim.append_beat(make_episode(run_id=run_id, offset_minutes=int(run_id[-1])))

    atom = Atom(
        key="api.retry",
        value="HTTP client retries use exponential backoff capped at 30s",
        employee_id="e_be_1",
        source_run_ids=("r1", "r2", "r3"),
        created_at=datetime.now(UTC),
        stats=PatternStats(alpha_own=3.5, beta_own=0.5, tier=Tier.RULE),
    )
    sim.lattice._atoms.write(atom)  # type: ignore[attr-defined]

    content = (tmp_path / "e_be_1" / "MEMORY.md").read_text()
    assert "**api.retry**" in content or "### api.retry" in content
    assert "LCB" in content
    assert "exponential backoff" in content


def test_key_files_resolved_from_source_runs() -> None:
    episodes = {
        "r1": _episode(run_id="r1", files=("src/api/client.py",)),
        "r2": _episode(run_id="r2", files=("src/api/client.py", "tests/test_client.py")),
    }
    atom = Atom(
        key="api.retry",
        value="claim",
        employee_id="e1",
        source_run_ids=("r1", "r2"),
        created_at=datetime.now(UTC),
    )
    key_files = key_files_for_atom(atom, episodes)
    assert "src/api/client.py" in key_files
    assert "tests/test_client.py" in key_files
    assert fingerprint_overlap(_episode(run_id="x", files=("tests/test_client.py",)), key_files)
