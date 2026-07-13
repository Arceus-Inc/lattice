"""Default procedural store — evolved SKILL.md overlays.

Legacy / test path: Chorus ``skill_manage`` + SkillStore is the production SoT for
procedural memory. Keep this store for unit tests and optional ``enable_patches`` demos.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, cast

from lattice.contracts.patch import SkillDraft, SkillPatch


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
        return tuple(_patch_from_json(item) for item in payload.get("patches", []))

    def apply_patch(self, employee_id: str, patch: SkillPatch) -> str:
        dest = self._skills_dir(employee_id) / patch.skill_slug / "SKILL.md"
        dest.parent.mkdir(parents=True, exist_ok=True)
        # Quote description — section titles often contain ':' which breaks YAML.
        description = f"Evolved overlay for {patch.skill_slug} (section: {patch.section})"
        body = (
            f"---\n"
            f"name: {patch.skill_slug}\n"
            f'description: "{description}"\n'
            f"---\n\n"
            f"# {patch.skill_slug}\n\n"
            f"## {patch.section}\n\n"
            f"{patch.new_content}\n"
        )
        dest.write_text(body, encoding="utf-8")
        self._append_meta(employee_id, patch=patch)
        return str(dest)

    def apply_draft(self, employee_id: str, draft: SkillDraft) -> str:
        dest = self._skills_dir(employee_id) / draft.slug / "SKILL.md"
        dest.parent.mkdir(parents=True, exist_ok=True)
        body = draft.body
        if not body.lstrip().startswith("---"):
            description = (draft.title.strip() or draft.slug).replace('"', "'")
            when = f"Use when performing the {draft.slug} workflow."
            frontmatter = (
                f"---\n"
                f"name: {draft.slug}\n"
                f'description: "{description}"\n'
                f'when_to_use: "{when}"\n'
                f"---\n\n"
            )
            header = f"# {draft.title}\n\n" if not body.lstrip().startswith("#") else ""
            body = frontmatter + header + body
        dest.write_text(body, encoding="utf-8")
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
        source_run_ids=tuple(str(item) for item in cast(tuple[object, ...], source_ids)),
        metadata=cast(dict[str, object], metadata),
    )
