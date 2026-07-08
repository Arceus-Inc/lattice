"""Procedural promotion — write accepted patches to overlay store."""

from __future__ import annotations

from lattice.contracts.procedural import (
    ProceduralStore,
    PromotionGate,
    SkillDraft,
    SkillPatch,
)
from lattice.domain.operation import PromotionVerdictKind
from lattice.domain.result import ProceduralOutcome


class ProceduralPromoter:
    """Apply gate-approved patches and drafts."""

    def __init__(self, *, store: ProceduralStore, gate: PromotionGate) -> None:
        self._store = store
        self._gate = gate

    def apply(
        self,
        employee_id: str,
        *,
        patches: tuple[SkillPatch, ...],
        drafts: tuple[SkillDraft, ...],
    ) -> ProceduralOutcome:
        promoted_patches: list[SkillPatch] = []
        promoted_drafts: list[SkillDraft] = []

        for patch in patches:
            verdict = self._gate.review_patch(patch)
            if verdict.kind is PromotionVerdictKind.ACCEPT:
                self._store.promote_patch(employee_id, patch)
                promoted_patches.append(patch)

        for draft in drafts:
            verdict = self._gate.review_draft(draft)
            if verdict.kind is PromotionVerdictKind.ACCEPT:
                self._store.promote_draft(employee_id, draft)
                promoted_drafts.append(draft)

        return ProceduralOutcome(
            patches_proposed=patches,
            patches_promoted=tuple(promoted_patches),
            drafts_proposed=drafts,
            drafts_promoted=tuple(promoted_drafts),
        )
