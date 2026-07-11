"""Consolidation packet — ranked engrams plus deterministic hints."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from lattice.contracts.episodic import RawEpisode


class HintKind(StrEnum):
    """What kind of consolidation the cluster suggests."""

    PATTERN = "pattern"
    HABIT = "habit"


class HabitHintAction(StrEnum):
    """Hermes preference: EVOLVE umbrella first; CREATE only for new class-level skills."""

    EVOLVE = "evolve"
    CREATE = "create"


@dataclass(frozen=True)
class PacketHint:
    """Optional cluster hint for the agent — not a write by itself."""

    kind: HintKind
    key_template: str
    run_ids: tuple[str, ...]
    suggested_action: HabitHintAction | None = None
    suggested_skill: str | None = None


@dataclass(frozen=True)
class Packet:
    """Evidence bundle emitted when the consolidation gate opens."""

    employee_id: str
    engrams: tuple[RawEpisode, ...]
    hints: tuple[PacketHint, ...]
