"""Default semantic store — MEMORY.md + atom directory."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from lattice.contracts.semantic import SemanticAtom, SemanticKind
from lattice.domain.operation import MemoryOperation, MemoryOperationKind


class MemoryMdStore:
    """File-backed semantic store under ``<root>/<employee_id>/``."""

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    def list_for(self, employee_id: str) -> tuple[SemanticAtom, ...]:
        atoms_dir = self._employee_dir(employee_id) / "semantic"
        if not atoms_dir.exists():
            return ()
        atoms: list[SemanticAtom] = []
        for path in sorted(atoms_dir.glob("*.json"), reverse=True):
            payload = cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
            atoms.append(_atom_from_json(payload))
        return tuple(atoms)

    def apply(self, operation: MemoryOperation) -> SemanticAtom | None:
        if operation.kind is MemoryOperationKind.NOOP:
            return None
        if operation.kind is MemoryOperationKind.DELETE:
            path = self._atom_path(operation.employee_id, operation.atom_id)
            if path.exists():
                path.unlink()
            self._rewrite_memory_md(operation.employee_id)
            return None

        atom = SemanticAtom(
            id=operation.atom_id,
            employee_id=operation.employee_id,
            kind=SemanticKind.FACT,
            claim=operation.claim,
            source_run_ids=operation.source_run_ids,
            confidence=1.0,
            created_at=datetime.now(UTC),
            metadata={"rationale": operation.rationale},
        )
        path = self._atom_path(atom.employee_id, atom.id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(_atom_to_json(atom), indent=2), encoding="utf-8")
        self._rewrite_memory_md(atom.employee_id)
        return atom

    def _employee_dir(self, employee_id: str) -> Path:
        return self._root / employee_id

    def _atom_path(self, employee_id: str, atom_id: str) -> Path:
        return self._employee_dir(employee_id) / "semantic" / f"{atom_id}.json"

    def _rewrite_memory_md(self, employee_id: str) -> None:
        atoms = self.list_for(employee_id)
        lines = ["# MEMORY", ""]
        for atom in atoms:
            lines.append(f"- ({atom.kind.value}) {atom.claim}")
        memory_md = self._employee_dir(employee_id) / "MEMORY.md"
        memory_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _atom_to_json(atom: SemanticAtom) -> dict[str, object]:
    data = asdict(atom)
    data["kind"] = atom.kind.value
    if atom.created_at is not None:
        data["created_at"] = atom.created_at.isoformat()
    return data


def _atom_from_json(payload: dict[str, Any]) -> SemanticAtom:
    created_raw = payload.get("created_at")
    created_at = datetime.fromisoformat(str(created_raw)) if created_raw else None
    source_ids = payload.get("source_run_ids", ())
    files = payload.get("files_touched", ())
    metadata = payload.get("metadata", {})
    return SemanticAtom(
        id=str(payload["id"]),
        employee_id=str(payload["employee_id"]),
        kind=SemanticKind(str(payload["kind"])),
        claim=str(payload["claim"]),
        source_run_ids=tuple(str(x) for x in cast(tuple[object, ...], source_ids)),
        confidence=float(payload.get("confidence", 1.0)),
        files_touched=tuple(str(x) for x in cast(tuple[object, ...], files)),
        created_at=created_at,
        metadata=cast(dict[str, object], metadata),
    )
