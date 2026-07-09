"""Consolidation packet — ranked engrams plus deterministic hints."""

from __future__ import annotations

from dataclasses import dataclass

from lattice.contracts.episodic import RawEpisode


@dataclass(frozen=True)
class PacketHint:
    """Optional cluster hint for the agent — not a write by itself."""

    key_template: str
    run_ids: tuple[str, ...]


@dataclass(frozen=True)
class Packet:
    """Evidence bundle emitted when the consolidation gate opens."""

    employee_id: str
    engrams: tuple[RawEpisode, ...]
    hints: tuple[PacketHint, ...]
