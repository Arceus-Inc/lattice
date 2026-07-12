"""Offline consolidation pipeline — gate, compile, validate, apply."""

from __future__ import annotations

from lattice.consolidate.apply import apply_proposal
from lattice.consolidate.cluster import (
    build_hints,
    cluster,
    gate_open,
    new_episodes,
    rank,
)
from lattice.consolidate.compile import compile_proposal
from lattice.consolidate.validate import validate_proposal

__all__ = [
    "apply_proposal",
    "build_hints",
    "cluster",
    "compile_proposal",
    "gate_open",
    "new_episodes",
    "rank",
    "validate_proposal",
]
