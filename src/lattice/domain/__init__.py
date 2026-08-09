"""Pure domain types."""

from __future__ import annotations

from lattice.domain.packet import HabitHintAction, HintKind, Packet, PacketHint
from lattice.domain.proposal import HabitAction, HabitDraft, Op, OpKind, PatternDraft, Proposal
from lattice.domain.result import AppliedContextResult, ApplyResult, ContextResult, ValidationResult

__all__ = [
    "AppliedContextResult",
    "ApplyResult",
    "ContextResult",
    "HabitAction",
    "HabitDraft",
    "HabitHintAction",
    "HintKind",
    "Op",
    "OpKind",
    "Packet",
    "PacketHint",
    "PatternDraft",
    "Proposal",
    "ValidationResult",
]
