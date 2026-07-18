"""Sleep forget pass — discount weak hints."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from lattice.contracts.atom import Atom
from lattice.domain.stats import (
    DEFAULT_ADJUDICATION_PARAMS,
    AdjudicationParams,
    PatternStats,
    tier_from_stats,
)
from lattice.stores.memory_md import MemoryMdStore


def discount_stats(
    stats: PatternStats,
    *,
    params: AdjudicationParams = DEFAULT_ADJUDICATION_PARAMS,
) -> PatternStats:
    """Decay own-evidence counts one sleep cycle."""
    alpha = stats.alpha_own * params.decay
    beta = stats.beta_own * params.decay
    updated = PatternStats(alpha_own=alpha, beta_own=beta, tier=stats.tier)
    tier = tier_from_stats(updated, params=params)
    return replace(updated, tier=tier)


def should_invalidate(
    stats: PatternStats,
    *,
    params: AdjudicationParams = DEFAULT_ADJUDICATION_PARAMS,
) -> bool:
    return stats.lcb05 < params.theta_floor


def forget_atoms(
    atoms: tuple[Atom, ...],
    *,
    params: AdjudicationParams = DEFAULT_ADJUDICATION_PARAMS,
) -> tuple[tuple[Atom, ...], tuple[str, ...]]:
    """Discount stats; return (updated_atoms, keys_to_invalidate)."""
    updated: list[Atom] = []
    invalidate_keys: list[str] = []

    for atom in atoms:
        stats = atom.stats or PatternStats.jeffreys_prior()
        discounted = discount_stats(stats, params=params)
        if should_invalidate(discounted, params=params):
            invalidate_keys.append(atom.key)
        else:
            updated.append(replace(atom, stats=discounted))

    return tuple(updated), tuple(invalidate_keys)


def forget_employee(
    employee_id: str,
    *,
    atoms: MemoryMdStore,
    params: AdjudicationParams = DEFAULT_ADJUDICATION_PARAMS,
) -> tuple[int, int]:
    """Run forget pass; returns (discounted_count, invalidated_count)."""
    active = atoms.list_active(employee_id)
    if not active:
        return 0, 0

    updated, invalidate_keys = forget_atoms(active, params=params)
    now = datetime.now(UTC)

    for atom in updated:
        atoms.write(atom)

    for key in invalidate_keys:
        atoms.invalidate(employee_id, key, at=now)

    return len(updated), len(invalidate_keys)
