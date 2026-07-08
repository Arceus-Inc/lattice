"""lattice errors — specific, chainable, no bare Exception."""

from __future__ import annotations


class LatticeError(Exception):
    """Base for lattice failures."""


class ConsolidationError(LatticeError):
    """A curator pass failed after partial progress."""


class PortError(LatticeError):
    """A bound port returned an unexpected shape or violated an invariant."""
