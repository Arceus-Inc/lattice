"""Default semantic store — atoms on disk + MEMORY.md view."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from lattice.contracts.atom import Atom
from lattice.domain.stats import PatternStats, Tier
from lattice.stores._safe_path import assert_safe_store_id


class MemoryMdStore:
    """File-backed atom store under ``<root>/<employee_id>/semantic/``."""

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    def list_active(self, employee_id: str) -> tuple[Atom, ...]:
        atoms = self._read_all(employee_id)
        active = [atom for atom in atoms if atom.invalid_at is None]
        return tuple(sorted(active, key=lambda atom: atom.created_at, reverse=True))

    def get_active(self, employee_id: str, key: str) -> Atom | None:
        for atom in self.list_active(employee_id):
            if atom.key == key:
                return atom
        return None

    def write(self, atom: Atom) -> None:
        path = self._atom_path(atom.employee_id, atom.key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(_atom_to_json(atom), indent=2), encoding="utf-8")
        self._rewrite_memory_md(atom.employee_id)

    def invalidate(self, employee_id: str, key: str, *, at: datetime) -> None:
        path = self._atom_path(employee_id, key)
        if not path.exists():
            return
        payload = cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
        atom = _atom_from_json(payload)
        invalidated = Atom(
            key=atom.key,
            value=atom.value,
            employee_id=atom.employee_id,
            source_run_ids=atom.source_run_ids,
            created_at=atom.created_at,
            invalid_at=at,
            activation=atom.activation,
            stats=atom.stats,
        )
        path.write_text(json.dumps(_atom_to_json(invalidated), indent=2), encoding="utf-8")
        self._rewrite_memory_md(employee_id)

    def _read_all(self, employee_id: str) -> tuple[Atom, ...]:
        atoms_dir = self._employee_dir(employee_id) / "semantic"
        if not atoms_dir.exists():
            return ()
        atoms: list[Atom] = []
        for path in sorted(atoms_dir.glob("*.json")):
            payload = cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
            atoms.append(_atom_from_json(payload))
        return tuple(atoms)

    def _employee_dir(self, employee_id: str) -> Path:
        safe_id = assert_safe_store_id(employee_id)
        return self._root / safe_id

    def _atom_path(self, employee_id: str, key: str) -> Path:
        safe = key.replace(".", "__")
        return self._employee_dir(employee_id) / "semantic" / f"{safe}.json"

    def _rewrite_memory_md(self, employee_id: str) -> None:
        blocks = ["# MEMORY", ""]
        active = self.list_active(employee_id)
        for index, atom in enumerate(active):
            if index > 0:
                blocks.append("")
            blocks.append(_format_memory_block(atom))
        memory_md = self._employee_dir(employee_id) / "MEMORY.md"
        memory_md.parent.mkdir(parents=True, exist_ok=True)
        memory_md.write_text("\n".join(blocks) + "\n", encoding="utf-8")


def _format_memory_block(atom: Atom) -> str:
    stats = atom.stats or PatternStats.jeffreys_prior()
    tier_label = stats.tier.value
    lcb = stats.lcb05
    header = f"### {atom.key} ({tier_label}, LCB {lcb:.2f})"
    body = atom.value.strip()
    return f"{header}\n\n{body}"


def _format_memory_line(atom: Atom) -> str:
    """Compact single-line view — kept for callers that expect the legacy shape."""
    stats = atom.stats or PatternStats.jeffreys_prior()
    tier_label = stats.tier.value
    lcb = stats.lcb05
    return f"- **{atom.key}** [{tier_label}, LCB {lcb:.2f}]: {atom.value}"


def _atom_to_json(atom: Atom) -> dict[str, object]:
    data: dict[str, object] = {
        "key": atom.key,
        "value": atom.value,
        "employee_id": atom.employee_id,
        "source_run_ids": list(atom.source_run_ids),
        "created_at": atom.created_at.isoformat(),
        "activation": atom.activation,
    }
    if atom.invalid_at is not None:
        data["invalid_at"] = atom.invalid_at.isoformat()
    if atom.stats is not None:
        data["stats"] = _stats_to_json(atom.stats)
    return data


def _stats_to_json(stats: PatternStats) -> dict[str, object]:
    return {
        "alpha_own": stats.alpha_own,
        "beta_own": stats.beta_own,
        "tier": stats.tier.value,
    }


def _atom_from_json(payload: dict[str, Any]) -> Atom:
    invalid_raw = payload.get("invalid_at")
    invalid_at = datetime.fromisoformat(str(invalid_raw)) if invalid_raw else None
    source_ids = payload.get("source_run_ids", ())
    stats_raw = payload.get("stats")
    stats = _stats_from_json(cast(dict[str, Any], stats_raw)) if isinstance(stats_raw, dict) else None
    return Atom(
        key=str(payload["key"]),
        value=str(payload["value"]),
        employee_id=str(payload["employee_id"]),
        source_run_ids=tuple(str(item) for item in cast(tuple[object, ...], source_ids)),
        created_at=datetime.fromisoformat(str(payload["created_at"])),
        invalid_at=invalid_at,
        activation=float(payload.get("activation", 1.0)),
        stats=stats,
    )


def _stats_from_json(payload: dict[str, Any]) -> PatternStats:
    tier_raw = str(payload.get("tier", Tier.HINT.value))
    tier = Tier.RULE if tier_raw == Tier.RULE.value else Tier.HINT
    return PatternStats(
        alpha_own=float(payload.get("alpha_own", 0.5)),
        beta_own=float(payload.get("beta_own", 0.5)),
        tier=tier,
    )
