"""Promotion gate — accept/reject procedural writes."""

from __future__ import annotations

from lattice.contracts.procedural import SkillDraft, SkillPatch
from lattice.domain.operation import PromotionVerdict, PromotionVerdictKind


class RejectAllPromotionGate:
    """L0/L1 default: propose but never promote until L3 two-arm critic."""

    def review_patch(self, patch: SkillPatch) -> PromotionVerdict:
        _ = patch
        return PromotionVerdict(kind=PromotionVerdictKind.REJECT, rationale="scaffold: gate closed")

    def review_draft(self, draft: SkillDraft) -> PromotionVerdict:
        _ = draft
        return PromotionVerdict(kind=PromotionVerdictKind.REJECT, rationale="scaffold: gate closed")


class AcceptAllPromotionGate:
    """Test helper — promotes every proposal."""

    def review_patch(self, patch: SkillPatch) -> PromotionVerdict:
        _ = patch
        return PromotionVerdict(kind=PromotionVerdictKind.ACCEPT, rationale="test gate")

    def review_draft(self, draft: SkillDraft) -> PromotionVerdict:
        _ = draft
        return PromotionVerdict(kind=PromotionVerdictKind.ACCEPT, rationale="test gate")
