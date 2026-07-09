"""Default file-backed store adapters."""

from __future__ import annotations

from lattice.stores.json_cursor import JsonCursorStore
from lattice.stores.memory_md import MemoryMdStore

__all__ = ["JsonCursorStore", "MemoryMdStore"]
