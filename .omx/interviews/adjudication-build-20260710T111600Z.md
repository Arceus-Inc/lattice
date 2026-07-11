# Deep Interview Transcript — adjudication-build

**Profile:** Standard (threshold ≤ 20%)  
**Rounds:** 9  
**Final ambiguity:** ~11%  
**Context:** `.omx/context/adjudication-build-20260710T111600Z.md`  
**Type:** Brownfield (lattice `feat/patterns-only` + chorus `feat/lattice-integration`)

---

## Round 1 — Intent
**Q:** Primary failure to prevent?  
**A:** Retrieval quality — `lattice_context` treats weak patterns like strong ones.

## Round 2 — Outcome pressure
**Q:** Which retrieval failure mode first?  
**A:** Wrong-domain — patterns from unrelated clusters surface (e.g. `api.retry` on design beat).

## Round 3 — Scope
**Q:** Structural match vs adjudication tiers?  
**A:** Adjudication-only path (no structural condition filter in this build).

## Round 4 — Contrarian assumption probe
**Q:** Expected behavior for high-LCB `api.retry` on design beat?  
**A:** Cross-domain beats count as β failures — demote patterns that don't generalize.

## Round 5 — Non-goals
**Q:** Explicit out-of-scope items?  
**A:** **No two-arm lift** (`P(lift>0)` deferred). Other items not excluded.

## Round 6 — Decision boundaries
**Q:** What may OMX decide without confirmation?  
**A:** All adjudication params (`N_rule`, `θ*`, `d`, `θ_floor`) from design doc defaults.

## Round 7 — Success criteria
**Q:** Primary done signal?  
**A:** **MEMORY.md shows tier + LCB** — visible trust level for humans/agents.

## Round 8 — Simplifier / scope lock
**Q:** Smallest build satisfying success?  
**A:** **Full sleep beat** — adjudicate → packet → apply → forget in facade + chorus wire.

## Round 9 — Constraints
**Q:** Landing constraints?  
**A:** Must land in **both lattice + chorus** on existing feature branches.

---

## Pressure-pass finding (Round 4)

Initial scope assumed adjudication improves trust within-domain. User clarified cross-domain β failures are required — beats on non-matching fingerprints should demote patterns. This expands adjudication beyond Slice A-core single-arm counting.

## Residual risks

- Adjudication-only may not fully eliminate wrong-domain surfacing if overlap/recency dominates before enough cross-domain failures accumulate.
- Full sleep + chorus wire is larger than originally discussed “smallest slice.”
- Probe re-run not explicitly required by user (only both-repos constraint stated).
