"""Pruner — FORGET stage of THE LOOP (L2+)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Pruner(Protocol):
    """Demote stale semantic atoms and procedural overlays."""

    def prune(self, employee_id: str) -> int:
        """Returns count of items pruned."""
        ...


class NoopPruner:
    """L0 scaffold — no forgetting yet."""

    def prune(self, employee_id: str) -> int:
        _ = employee_id
        return 0
