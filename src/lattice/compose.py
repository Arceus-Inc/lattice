"""Default lattice wiring — noop extractors, file-backed stores."""

from __future__ import annotations

from pathlib import Path

from lattice.contracts.episodic import EpisodicReader
from lattice.facade import Lattice
from lattice.procedural.consolidator import ProceduralConsolidator
from lattice.procedural.evolve import NoopSkillEvolver
from lattice.procedural.gate import RejectAllPromotionGate
from lattice.semantic.consolidator import SemanticConsolidator
from lattice.semantic.extract import NoopSemanticExtractor
from lattice.semantic.reconcile import AddOnlySemanticReconciler
from lattice.stores import JsonCursorStore, MemoryMdStore, OverlaySkillStore


def build_default(
    *,
    consolidated_root: str | Path,
    episodes: EpisodicReader,
    canonical_skills_root: Path | None = None,
    min_new_episodes: int = 1,
) -> Lattice:
    """Wire lattice with L0 noop extractors and default file stores."""
    root = Path(consolidated_root)
    semantic_store = MemoryMdStore(root)
    procedural_store = OverlaySkillStore(root)
    cursor = JsonCursorStore(root)

    semantic = SemanticConsolidator(
        extractor=NoopSemanticExtractor(),
        reconciler=AddOnlySemanticReconciler(),
        store=semantic_store,
    )
    procedural = ProceduralConsolidator(
        evolver=NoopSkillEvolver(),
        gate=RejectAllPromotionGate(),
        store=procedural_store,
        canonical_skills_root=canonical_skills_root,
    )
    return Lattice(
        episodes=episodes,
        cursor=cursor,
        semantic=semantic,
        procedural=procedural,
        min_new_episodes=min_new_episodes,
    )
