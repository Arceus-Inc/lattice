"""THE LOOP — cross-cutting consolidation orchestration."""

from __future__ import annotations

from lattice.consolidate.pass_ import ConsolidationPass
from lattice.consolidate.prune import NoopPruner

__all__ = ["ConsolidationPass", "NoopPruner"]
