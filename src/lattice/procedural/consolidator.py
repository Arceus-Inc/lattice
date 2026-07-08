"""P1 procedural consolidation — evolve → gate → promote."""

from __future__ import annotations

from pathlib import Path

from lattice.contracts.episodic import EpisodeBatch
from lattice.contracts.procedural import ProceduralStore, PromotionGate, SkillEvolver
from lattice.domain.result import ProceduralOutcome
from lattice.procedural.promote import ProceduralPromoter


class ProceduralConsolidator:
    """Owns the procedural vertical slice for one episode batch."""

    def __init__(
        self,
        *,
        evolver: SkillEvolver,
        gate: PromotionGate,
        store: ProceduralStore,
        canonical_skills_root: Path | None = None,
    ) -> None:
        self._evolver = evolver
        self._promoter = ProceduralPromoter(store=store, gate=gate)
        self._canonical_skills_root = canonical_skills_root

    def run(self, batch: EpisodeBatch) -> ProceduralOutcome:
        patches = self._evolver.evolve(batch, canonical_skills_root=self._canonical_skills_root)
        drafts = self._evolver.propose_drafts(
            batch,
            canonical_skills_root=self._canonical_skills_root,
        )
        return self._promoter.apply(
            batch.employee_id,
            patches=patches,
            drafts=drafts,
        )
