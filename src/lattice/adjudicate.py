"""Outcome-grounded adjudication — Beta updates without LLM."""

from __future__ import annotations

from dataclasses import replace

from lattice.cluster import new_episodes
from lattice.contracts.atom import Atom
from lattice.contracts.cursor import ConsolidationWatermark
from lattice.contracts.episodic import RawEpisode
from lattice.domain.stats import (
    DEFAULT_ADJUDICATION_PARAMS,
    AdjudicationParams,
    PatternStats,
    is_success_outcome,
    tier_from_stats,
)


def key_files_for_atom(
    atom: Atom,
    episodes_by_run_id: dict[str, RawEpisode],
) -> frozenset[str]:
    """Union of files_touched from cited source runs."""
    files: set[str] = set()
    for run_id in atom.source_run_ids:
        episode = episodes_by_run_id.get(run_id)
        if episode is None:
            continue
        files.update(episode.files_touched)
    return frozenset(files)


def fingerprint_overlap(episode: RawEpisode, key_files: frozenset[str]) -> bool:
    if not key_files:
        return False
    return bool(set(episode.files_touched) & key_files)


def apply_episode_to_stats(
    stats: PatternStats,
    episode: RawEpisode,
    key_files: frozenset[str],
    *,
    params: AdjudicationParams = DEFAULT_ADJUDICATION_PARAMS,
) -> PatternStats:
    """Update own-evidence counts for one fresh episode."""
    overlaps = fingerprint_overlap(episode, key_files)
    success = is_success_outcome(episode.outcome)

    alpha = stats.alpha_own
    beta = stats.beta_own

    if overlaps and success:
        alpha += 1.0
    elif overlaps and not success:
        beta += 1.0
    elif not overlaps and not success:
        beta += params.w_cross
    # non-overlapping success: no update

    updated = PatternStats(alpha_own=alpha, beta_own=beta, tier=stats.tier)
    tier = tier_from_stats(updated, params=params)
    return replace(updated, tier=tier)


def adjudicate_atom(
    atom: Atom,
    fresh_episodes: tuple[RawEpisode, ...],
    episodes_by_run_id: dict[str, RawEpisode],
    *,
    params: AdjudicationParams = DEFAULT_ADJUDICATION_PARAMS,
) -> Atom:
    """Apply fresh episodic evidence to one atom's posterior."""
    stats = atom.stats or PatternStats.jeffreys_prior()
    key_files = key_files_for_atom(atom, episodes_by_run_id)

    for episode in fresh_episodes:
        stats = apply_episode_to_stats(stats, episode, key_files, params=params)

    return replace(atom, stats=stats)


def adjudicate_atoms(
    atoms: tuple[Atom, ...],
    all_episodes: tuple[RawEpisode, ...],
    watermark: ConsolidationWatermark,
    *,
    params: AdjudicationParams = DEFAULT_ADJUDICATION_PARAMS,
) -> tuple[Atom, ...]:
    """Adjudicate all active atoms against episodes since consolidation cursor."""
    fresh = new_episodes(all_episodes, watermark)
    if not fresh or not atoms:
        return atoms

    episodes_by_run_id = {ep.run_id: ep for ep in all_episodes}
    return tuple(
        adjudicate_atom(atom, fresh, episodes_by_run_id, params=params) for atom in atoms
    )
