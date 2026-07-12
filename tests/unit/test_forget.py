"""forget.py — discount and invalidate weak patterns."""

from __future__ import annotations

from datetime import UTC, datetime

from lattice.contracts.atom import Atom
from lattice.domain.stats import PatternStats, Tier
from lattice.forget import discount_stats
from tests.integration.conftest import BeatSimulator, make_episode, valid_retry_proposal


def _append_retry_cluster(sim: BeatSimulator, *, count: int = 5) -> tuple[str, ...]:
    run_ids = tuple(f"r_b{i}" for i in range(1, count + 1))
    for run_id in run_ids:
        sim.append_beat(make_episode(run_id=run_id))
    return run_ids


def test_discount_reduces_counts() -> None:
    stats = PatternStats(alpha_own=2.0, beta_own=2.0, tier=Tier.HINT)
    discounted = discount_stats(stats)
    assert discounted.alpha_own < stats.alpha_own
    assert discounted.beta_own < stats.beta_own


def test_weak_hint_invalidated_after_forget(tmp_path) -> None:
    sim = BeatSimulator(consolidated_root=tmp_path)
    _append_retry_cluster(sim, count=3)

    sim.lattice.apply(valid_retry_proposal(run_ids=("r_b1", "r_b2", "r_b3")))

    atom = Atom(
        key="weak.hint",
        value="A weak pattern that should be forgotten after discount",
        employee_id="e_be_1",
        source_run_ids=("r1",),
        created_at=datetime.now(UTC),
        stats=PatternStats(alpha_own=0.2, beta_own=0.2, tier=Tier.HINT),
    )
    sim.lattice._atoms.write(atom)  # type: ignore[attr-defined]

    result = sim.lattice.forget("e_be_1")
    assert result.atoms_invalidated >= 1
    assert sim.lattice._atoms.get_active("e_be_1", "weak.hint") is None  # type: ignore[attr-defined]


def test_forget_preserves_strong_patterns(tmp_path) -> None:
    sim = BeatSimulator(consolidated_root=tmp_path)
    run_ids = _append_retry_cluster(sim, count=2)
    assert sim.lattice.apply(valid_retry_proposal(run_ids=run_ids)).ok

    result = sim.lattice.forget("e_be_1")
    assert sim.lattice._atoms.get_active("e_be_1", "api.retry") is not None  # type: ignore[attr-defined]
    assert result.atoms_discounted >= 0
