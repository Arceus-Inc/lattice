"""Default lattice wiring — file-backed stores."""

from __future__ import annotations

from pathlib import Path

from lattice.contracts.episodic import EpisodicReader
from lattice.directive import DEFAULT_MIN_CLUSTER_SIZE, DEFAULT_MIN_NEW_EPISODES
from lattice.facade import Lattice
from lattice.stores import JsonCursorStore, MemoryMdStore, OverlaySkillStore


def build_default(
    *,
    consolidated_root: str | Path,
    episodes: EpisodicReader,
    min_new_episodes: int = DEFAULT_MIN_NEW_EPISODES,
    min_cluster_size: int = DEFAULT_MIN_CLUSTER_SIZE,
    enable_patches: bool = False,
    canonical_skills_root: Path | None = None,
) -> Lattice:
    """Wire lattice with default file stores."""
    root = Path(consolidated_root)
    atoms = MemoryMdStore(root)
    cursor = JsonCursorStore(root)
    patches = OverlaySkillStore(root) if enable_patches else None
    return Lattice(
        episodes=episodes,
        cursor=cursor,
        atoms=atoms,
        patches=patches,
        min_new_episodes=min_new_episodes,
        min_cluster_size=min_cluster_size,
        canonical_skills_root=canonical_skills_root,
        evolved_skills_root=root,
    )
