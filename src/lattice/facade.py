"""Lattice facade — five-function consolidation SDK."""

from __future__ import annotations

from pathlib import Path

from lattice.consolidate.apply import apply_proposal
from lattice.consolidate.cluster import build_hints, cluster, gate_open, new_episodes, rank
from lattice.consolidate.validate import validate_proposal
from lattice.contracts.episodic import EpisodicReader
from lattice.contracts.patch import PatchStore
from lattice.directive import (
    DEFAULT_MIN_CLUSTER_SIZE,
    DEFAULT_MIN_NEW_EPISODES,
    beat_end_notice,
    beat_start_notice,
)
from lattice.domain.packet import Packet
from lattice.domain.proposal import Proposal
from lattice.domain.result import AdjudicateResult, ApplyResult, ForgetResult, ValidationResult
from lattice.semantic.adjudicate import adjudicate_atoms
from lattice.semantic.forget import forget_employee
from lattice.semantic.retrieve import render_context
from lattice.stores.json_cursor import JsonCursorStore
from lattice.stores.memory_md import MemoryMdStore


class Lattice:
    """The consolidation SDK entry point."""

    def __init__(
        self,
        *,
        episodes: EpisodicReader,
        cursor: JsonCursorStore,
        atoms: MemoryMdStore,
        patches: PatchStore | None = None,
        min_new_episodes: int = DEFAULT_MIN_NEW_EPISODES,
        min_cluster_size: int = DEFAULT_MIN_CLUSTER_SIZE,
        packet_limit: int = 20,
        canonical_skills_root: Path | None = None,
    ) -> None:
        self._episodes = episodes
        self._cursor = cursor
        self._atoms = atoms
        self._patches = patches
        self._min_new = min_new_episodes
        self._min_cluster = min_cluster_size
        self._packet_limit = packet_limit
        self._canonical_skills_root = canonical_skills_root

    def gate_open(self, employee_id: str) -> bool:
        watermark = self._cursor.get(employee_id)
        episodes = self._episodes.records_for(employee_id)
        return gate_open(
            episodes,
            watermark,
            min_new=self._min_new,
            min_cluster=self._min_cluster,
        )

    def packet(self, employee_id: str) -> Packet | None:
        if not self.gate_open(employee_id):
            return None
        watermark = self._cursor.get(employee_id)
        all_episodes = self._episodes.records_for(employee_id)
        fresh = new_episodes(all_episodes, watermark)
        ranked = rank(fresh)[: self._packet_limit]
        clusters = cluster(tuple(ranked))
        hints = build_hints(clusters, min_cluster=self._min_cluster)
        return Packet(employee_id=employee_id, engrams=tuple(ranked), hints=hints)

    def validate(self, proposal: Proposal) -> ValidationResult:
        episodes = self._episodes.records_for(proposal.employee_id)
        return validate_proposal(
            proposal,
            episodes=episodes,
            atoms=self._atoms,
            canonical_skills_root=self._canonical_skills_root,
        )

    def apply(self, proposal: Proposal) -> ApplyResult:
        validation = self.validate(proposal)
        episodes = self._episodes.records_for(proposal.employee_id)
        episodes_by_run_id = {episode.run_id: episode for episode in episodes}
        result = apply_proposal(
            proposal,
            validation,
            atoms=self._atoms,
            episodes_by_run_id=episodes_by_run_id,
            patches=self._patches,
        )
        if result.ok:
            self._advance_cursor(proposal.employee_id)
        return result

    def adjudicate(self, employee_id: str) -> AdjudicateResult:
        """Update pattern posteriors from episodic outcomes since last consolidation."""
        watermark = self._cursor.get(employee_id)
        episodes = self._episodes.records_for(employee_id)
        fresh = new_episodes(episodes, watermark)
        active = self._atoms.list_active(employee_id)
        if not fresh or not active:
            return AdjudicateResult(
                employee_id=employee_id,
                atoms_updated=0,
                episodes_processed=len(fresh),
            )

        updated_atoms = adjudicate_atoms(active, episodes, watermark)
        atoms_updated = 0
        for before, after in zip(active, updated_atoms, strict=True):
            if after.stats != before.stats:
                self._atoms.write(after)
                atoms_updated += 1

        return AdjudicateResult(
            employee_id=employee_id,
            atoms_updated=atoms_updated,
            episodes_processed=len(fresh),
        )

    def forget(self, employee_id: str) -> ForgetResult:
        """Discount own-evidence counts and invalidate patterns below floor."""
        discounted, invalidated = forget_employee(employee_id, atoms=self._atoms)
        return ForgetResult(
            employee_id=employee_id,
            atoms_discounted=discounted,
            atoms_invalidated=invalidated,
        )

    def has_fresh_episodes(self, employee_id: str) -> bool:
        """True when episodic deltas exist since the consolidation cursor."""
        watermark = self._cursor.get(employee_id)
        episodes = self._episodes.records_for(employee_id)
        return len(new_episodes(episodes, watermark)) > 0

    def context(self, employee_id: str, query: str, *, k: int = 5) -> str:
        atoms = self._atoms.list_active(employee_id)
        return render_context(query, atoms, k=k)

    def beat_end_teaser(self, employee_id: str) -> str:
        """Short beat-end notice — empty when gate closed (no consolidation nudge)."""
        return beat_end_notice(gate_open=self.gate_open(employee_id))

    def beat_start_teaser(self, employee_id: str, query: str, *, k: int = 3) -> str:
        """Optional distilled-memory lines for beat-start injection."""
        return beat_start_notice(context=self.context(employee_id, query, k=k))

    def _advance_cursor(self, employee_id: str) -> None:
        episodes = self._episodes.records_for(employee_id)
        if not episodes:
            return
        latest = max(episodes, key=lambda episode: episode.created_at)
        self._cursor.advance(
            employee_id,
            last_run_id=latest.run_id,
            episodes_seen=len(episodes),
        )
