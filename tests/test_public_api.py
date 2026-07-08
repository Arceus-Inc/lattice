"""Public API pins."""

from __future__ import annotations

import lattice


def test_public_exports() -> None:
    assert hasattr(lattice, "Lattice")
    assert hasattr(lattice, "ConsolidationResult")
