"""stores/json_cursor.py — consolidation watermark persistence."""

from __future__ import annotations

import json
from pathlib import Path

from lattice.stores.json_cursor import JsonCursorStore


def test_get_returns_zero_watermark_by_default(tmp_path: Path) -> None:
    cursor = JsonCursorStore(tmp_path)
    wm = cursor.get("e1")
    assert wm.episodes_seen == 0
    assert wm.last_run_id is None


def test_advance_persists_to_disk(tmp_path: Path) -> None:
    cursor = JsonCursorStore(tmp_path)
    cursor.advance("e1", last_run_id="r_b5", episodes_seen=5)

    reloaded = JsonCursorStore(tmp_path)
    wm = reloaded.get("e1")
    assert wm.episodes_seen == 5
    assert wm.last_run_id == "r_b5"
    assert wm.consolidated_at is not None

    payload = json.loads((tmp_path / ".cursor.json").read_text())
    assert payload["e1"]["episodes_seen"] == 5
