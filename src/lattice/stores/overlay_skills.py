"""Default procedural store — evolved SKILL.md overlays."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, cast

from lattice.contracts.procedural import SkillDraft, SkillPatch


class OverlaySkillStore:
    """File-backed skill overlays under ``<root>/<employee_id>/evolved-skills/``."""

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    def list_patches(self, employee_id: str) -> tuple[SkillPatch, ...]:
        meta = self._meta_path(employee_id)
        if not meta.exists():
            return ()
        payload = cast(dict[str, Any], json.loads(meta.read_text(encoding="utf-8")))
        patches = [_patch_from_json(item) for item in payload.get("patches", [])]
        return tuple(patches)

    def promote_patch(self, employee_id: str, patch: SkillPatch) -> str:
        dest = self._skills_dir(employee_id) / patch.skill_slug / "SKILL.md"
        dest.parent.mkdir(parents=True, exist_ok=True)
        body = f"# {patch.skill_slug}\n\n## {patch.section}\n\n{patch.new_content}\n"
        dest.write_text(body, encoding="utf-8")
        self._append_meta(employee_id, patch=patch)
        return str(dest)

    def promote_draft(self, employee_id: str, draft: SkillDraft) -> str:
        dest = self._skills_dir(employee_id) / draft.slug / "SKILL.md"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(draft.body, encoding="utf-8")
        self._append_meta(employee_id, draft=draft)
        return str(dest)

    def _skills_dir(self, employee_id: str) -> Path:
        return self._root / employee_id / "evolved-skills"

    def _meta_path(self, employee_id: str) -> Path:
        return self._root / employee_id / "procedural-meta.json"

    def _append_meta(
        self,
        employee_id: str,
        *,
        patch: SkillPatch | None = None,
        draft: SkillDraft | None = None,
    ) -> None:
        meta = self._meta_path(employee_id)
        payload: dict[str, list[dict[str, object]]] = {"patches": [], "drafts": []}
        if meta.exists():
            payload = cast(
                dict[str, list[dict[str, object]]],
                json.loads(meta.read_text(encoding="utf-8")),
            )
        if patch is not None:
            payload.setdefault("patches", []).append(asdict(patch))
        if draft is not None:
            payload.setdefault("drafts", []).append(asdict(draft))
        meta.parent.mkdir(parents=True, exist_ok=True)
        meta.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _patch_from_json(payload: dict[str, Any]) -> SkillPatch:
    source_ids = payload.get("source_run_ids", ())
    metadata = payload.get("metadata", {})
    return SkillPatch(
        skill_slug=str(payload["skill_slug"]),
        section=str(payload["section"]),
        new_content=str(payload["new_content"]),
        rationale=str(payload["rationale"]),
        source_run_ids=tuple(str(x) for x in cast(tuple[object, ...], source_ids)),
        confidence=float(payload.get("confidence", 1.0)),
        metadata=cast(dict[str, object], metadata),
    )
