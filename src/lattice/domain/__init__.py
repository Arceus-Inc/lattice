"""Pure domain types."""

from __future__ import annotations

from lattice.domain.packet import Packet, PacketHint
from lattice.domain.proposal import Op, OpKind, PatternDraft, Proposal
from lattice.domain.result import ApplyResult, ValidationResult

__all__ = [
    "ApplyResult",
    "Op",
    "OpKind",
    "Packet",
    "PacketHint",
    "PatternDraft",
    "Proposal",
    "ValidationResult",
]
