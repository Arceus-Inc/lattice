"""Default lattice wiring — file-backed pattern store."""

from __future__ import annotations

from pathlib import Path

from lattice.contracts.episodic import EpisodicReader
from lattice.directive import DEFAULT_MIN_CLUSTER_SIZE, DEFAULT_MIN_NEW_EPISODES
from lattice.facade import Lattice
from lattice.stores import JsonCursorStore, MemoryMdStore


def build_default(
    *,
    consolidated_root: str | Path,
    episodes: EpisodicReader,
    min_new_episodes: int = DEFAULT_MIN_NEW_EPISODES,
    min_cluster_size: int = DEFAULT_MIN_CLUSTER_SIZE,
) -> Lattice:
    """Wire lattice with default file stores (patterns only)."""
    root = Path(consolidated_root)
    atoms = MemoryMdStore(root)
    cursor = JsonCursorStore(root)
    return Lattice(
        episodes=episodes,
        cursor=cursor,
        atoms=atoms,
        min_new_episodes=min_new_episodes,
        min_cluster_size=min_cluster_size,
    )
