"""No-op skill evolver — L0 scaffold."""

from __future__ import annotations

from pathlib import Path

from lattice.contracts.episodic import EpisodeBatch
from lattice.contracts.procedural import SkillDraft, SkillPatch


class NoopSkillEvolver:
    """Returns no patches until L2 wires a real LLM evolver."""

    def evolve(
        self,
        batch: EpisodeBatch,
        *,
        canonical_skills_root: Path | None,
    ) -> tuple[SkillPatch, ...]:
        _ = batch, canonical_skills_root
        return ()

    def propose_drafts(
        self,
        batch: EpisodeBatch,
        *,
        canonical_skills_root: Path | None,
    ) -> tuple[SkillDraft, ...]:
        _ = batch, canonical_skills_root
        return ()
