"""Public API pins."""

from __future__ import annotations

import lattice


def test_public_exports() -> None:
    assert hasattr(lattice, "Lattice")
    assert hasattr(lattice, "Proposal")
    assert hasattr(lattice, "Packet")
    assert hasattr(lattice, "ApplyResult")
    assert hasattr(lattice, "ValidationResult")
