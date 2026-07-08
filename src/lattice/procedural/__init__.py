"""P1 procedural consolidation."""

from __future__ import annotations

from lattice.procedural.consolidator import ProceduralConsolidator
from lattice.procedural.evolve import NoopSkillEvolver
from lattice.procedural.gate import AcceptAllPromotionGate, RejectAllPromotionGate
from lattice.procedural.promote import ProceduralPromoter

__all__ = [
    "AcceptAllPromotionGate",
    "NoopSkillEvolver",
    "ProceduralConsolidator",
    "ProceduralPromoter",
    "RejectAllPromotionGate",
]
