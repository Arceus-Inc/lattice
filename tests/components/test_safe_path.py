"""stores/_safe_path.py — reject path traversal in store ids."""

from __future__ import annotations

import pytest

from lattice.stores._safe_path import UnsafeStoreIdError, assert_safe_store_id
from lattice.stores.json_cursor import JsonCursorStore
from lattice.stores.memory_md import MemoryMdStore


def test_rejects_path_traversal_employee_id(tmp_path) -> None:
    store = MemoryMdStore(tmp_path)
    with pytest.raises(UnsafeStoreIdError):
        store.list_active("../escape")


def test_rejects_slash_in_employee_id(tmp_path) -> None:
    cursor = JsonCursorStore(tmp_path)
    with pytest.raises(UnsafeStoreIdError):
        cursor.get("e/evil")


def test_accepts_normal_employee_id(tmp_path) -> None:
    assert assert_safe_store_id("e_be_1") == "e_be_1"
