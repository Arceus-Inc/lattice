"""Harness wiring — brief directives and beat notices for chorus."""

from __future__ import annotations

from lattice.harness.directive import (
    BEAT_END_GATE_OPEN,
    DEFAULT_MIN_CLUSTER_SIZE,
    DEFAULT_MIN_NEW_EPISODES,
    LATTICE_CONSOLIDATE_DIRECTIVE,
    LATTICE_CONTEXT_DIRECTIVE,
    beat_end_notice,
    beat_start_notice,
)

__all__ = [
    "BEAT_END_GATE_OPEN",
    "DEFAULT_MIN_CLUSTER_SIZE",
    "DEFAULT_MIN_NEW_EPISODES",
    "LATTICE_CONSOLIDATE_DIRECTIVE",
    "LATTICE_CONTEXT_DIRECTIVE",
    "beat_end_notice",
    "beat_start_notice",
]
