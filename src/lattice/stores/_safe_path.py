"""Path safety for store identifiers."""

from __future__ import annotations

import re

_SAFE_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}$")


class UnsafeStoreIdError(ValueError):
    """Raised when an employee_id would escape the store root."""


def assert_safe_store_id(employee_id: str) -> str:
    """Reject path traversal and unsafe characters in store-scoped ids."""
    if not employee_id or employee_id in {".", ".."}:
        raise UnsafeStoreIdError(f"unsafe employee_id: {employee_id!r}")
    if "/" in employee_id or "\\" in employee_id or "\0" in employee_id:
        raise UnsafeStoreIdError(f"unsafe employee_id: {employee_id!r}")
    if not _SAFE_ID.match(employee_id):
        raise UnsafeStoreIdError(f"unsafe employee_id: {employee_id!r}")
    return employee_id
