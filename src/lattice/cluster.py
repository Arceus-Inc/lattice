"""Gate, rank, cluster, and pattern hints — pure algorithms over engrams."""

from __future__ import annotations

from lattice.contracts.cursor import ConsolidationWatermark
from lattice.contracts.episodic import RawEpisode
from lattice.domain.packet import PacketHint


def gate_open(
    episodes: tuple[RawEpisode, ...],
    watermark: ConsolidationWatermark,
    *,
    min_new: int = 1,
    min_cluster: int = 2,
) -> bool:
    """G(c) ⇔ |E_new| ≥ N ∧ max_cluster_size(E_new) ≥ K."""
    new_eps = new_episodes(episodes, watermark)
    if len(new_eps) < min_new:
        return False
    clusters = cluster(new_eps)
    if not clusters:
        return False
    return max(len(group) for group in clusters) >= min_cluster


def new_episodes(
    episodes: tuple[RawEpisode, ...],
    watermark: ConsolidationWatermark,
) -> tuple[RawEpisode, ...]:
    """Episodes accumulated since the last consolidation cursor."""
    new_count = max(0, len(episodes) - watermark.episodes_seen)
    if new_count == 0:
        return ()
    ranked = rank(episodes)
    return tuple(ranked[:new_count])


def rank(episodes: tuple[RawEpisode, ...]) -> tuple[RawEpisode, ...]:
    """Done beats incomplete; preserve recency within tier."""

    def key(ep: RawEpisode) -> tuple[int, float]:
        outcome_rank = 0 if ep.outcome == "done" else 1
        return (outcome_rank, -ep.created_at.timestamp())

    return tuple(sorted(episodes, key=key))


def cluster(episodes: tuple[RawEpisode, ...]) -> tuple[tuple[RawEpisode, ...], ...]:
    """Greedy bucket on primary file prefix (or intent token)."""
    buckets: dict[str, list[RawEpisode]] = {}
    for ep in episodes:
        bucket_key = _bucket_key(ep)
        buckets.setdefault(bucket_key, []).append(ep)
    return tuple(tuple(group) for group in buckets.values())


def build_hints(
    clusters: tuple[tuple[RawEpisode, ...], ...],
    *,
    min_cluster: int = 2,
) -> tuple[PacketHint, ...]:
    """Deterministic pattern hints from clusters large enough to consolidate."""
    hints: list[PacketHint] = []
    for group in clusters:
        if len(group) < min_cluster:
            continue
        hints.append(
            PacketHint(
                key_template=_bucket_key(group[0]),
                run_ids=tuple(ep.run_id for ep in group),
            )
        )
    return tuple(hints)


def _bucket_key(ep: RawEpisode) -> str:
    if ep.files_touched:
        first = ep.files_touched[0]
        return first.split("/")[0] if "/" in first else first
    if ep.intent:
        return ep.intent.lower().split()[0]
    return ep.run_id
