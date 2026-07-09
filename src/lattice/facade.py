"""Lattice facade — pattern consolidation and retrieval."""

from __future__ import annotations

from lattice.apply import apply_proposal
from lattice.cluster import build_hints, cluster, gate_open, new_episodes, rank
from lattice.contracts.atom import AtomStore
from lattice.contracts.cursor import ConsolidationCursor
from lattice.contracts.episodic import EpisodicReader
from lattice.directive import (
    DEFAULT_MIN_CLUSTER_SIZE,
    DEFAULT_MIN_NEW_EPISODES,
    beat_end_notice,
    beat_start_notice,
)
from lattice.domain.packet import Packet
from lattice.domain.proposal import Proposal
from lattice.domain.result import ApplyResult, ValidationResult
from lattice.retrieve import render_context
from lattice.validate import validate_proposal


class Lattice:
    """The consolidation SDK entry point — patterns only on this branch."""

    def __init__(
        self,
        *,
        episodes: EpisodicReader,
        cursor: ConsolidationCursor,
        atoms: AtomStore,
        min_new_episodes: int = DEFAULT_MIN_NEW_EPISODES,
        min_cluster_size: int = DEFAULT_MIN_CLUSTER_SIZE,
        packet_limit: int = 20,
    ) -> None:
        self._episodes = episodes
        self._cursor = cursor
        self._atoms = atoms
        self._min_new = min_new_episodes
        self._min_cluster = min_cluster_size
        self._packet_limit = packet_limit

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
        return validate_proposal(proposal, episodes=episodes, atoms=self._atoms)

    def apply(self, proposal: Proposal) -> ApplyResult:
        validation = self.validate(proposal)
        result = apply_proposal(proposal, validation, atoms=self._atoms)
        if result.ok:
            self._advance_cursor(proposal.employee_id)
        return result

    def context(self, employee_id: str, query: str, *, k: int = 5) -> str:
        patterns = self._atoms.list_active(employee_id)
        return render_context(query, patterns, k=k)

    def beat_end_teaser(self, employee_id: str) -> str:
        return beat_end_notice(gate_open=self.gate_open(employee_id))

    def beat_start_teaser(self, employee_id: str, query: str, *, k: int = 3) -> str:
        return beat_start_notice(context=self.context(employee_id, query, k=k))

    def _advance_cursor(self, employee_id: str) -> None:
        episodes = self._episodes.records_for(employee_id)
        if not episodes:
            return
        latest = max(episodes, key=lambda ep: ep.created_at)
        self._cursor.advance(
            employee_id,
            last_run_id=latest.run_id,
            episodes_seen=len(episodes),
        )
