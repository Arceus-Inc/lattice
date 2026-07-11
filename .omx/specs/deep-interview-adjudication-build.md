# Deep Interview Spec — Adjudication Build

**Generated:** 2026-07-10  
**Profile:** Standard | Rounds: 9 | Final ambiguity: ~11% | Threshold: 20%  
**Context snapshot:** `.omx/context/adjudication-build-20260710T111600Z.md`  
**Transcript:** `.omx/interviews/adjudication-build-20260710T111600Z.md`

---

## Clarity breakdown

| Dimension | Score | Notes |
|-----------|-------|-------|
| Intent | 0.90 | Fix retrieval trust — weak/unproven patterns rank like strong ones |
| Outcome | 0.90 | MEMORY.md exposes tier + LCB; cross-domain failures demote patterns |
| Scope | 0.90 | Full sleep beat in lattice facade + chorus wire; both repos |
| Constraints | 0.85 | Existing feature branches; lattice must not import chorus |
| Success criteria | 0.90 | MEMORY.md tier/LCB visibility is primary done signal |
| Context | 0.90 | Shipped loop + v3 probe + adjudication design doc |

---

## Intent (why)

`lattice_context` today ranks patterns by token overlap + recency + activation. Agent-applied patterns are durable at full weight with no outcome grounding. The user wants **retrieval to reflect earned trust**, starting with the failure mode where **wrong-domain patterns surface** (e.g. `api.retry` appearing on non-API beats).

**Epistemic rule (locked):** prose proposes (agent `claim`), outcomes dispose (`done`/`incomplete` → Bernoulli updates). `c_p = 0`.

---

## Desired outcome

After consolidation and subsequent beats:

1. Each active pattern atom carries **tier** (`hint` | `rule`) and **posterior stats** (at minimum mean + LCB05).
2. **`MEMORY.md` renders tier + LCB** on each bullet — primary human/agent trust signal.
3. **Cross-domain generalization is tested:** beats whose fingerprints do **not** overlap a pattern's key files increment **β** (failure), demoting patterns that don't generalize.
4. **Full sleep beat ordering** runs in lattice facade:
   ```text
   gate_open? → adjudicate existing → packet → agent apply → forget → advance cursor
   ```
5. Chorus harness invokes this ordering on consolidation beats (wire on `feat/lattice-integration`).

---

## In-scope

| ID | Deliverable | Repo |
|----|-------------|------|
| S1 | `lattice/adjudicate.py` — `PatternOutcomeTracker`, cross-domain β logic | lattice |
| S2 | Atom stats sidecar (`tier`, `alpha_own`, `beta_own`, `lcb05`) in `semantic/*.json` | lattice |
| S3 | `MEMORY.md` regeneration with `[tier, LCB x.xx]` per pattern | lattice |
| S4 | `facade` sleep path: adjudicate → (existing apply flow) → forget/discount | lattice |
| S5 | Forget cycle: discount `α/β` by `d`; invalidate below `θ_floor` | lattice |
| S6 | Chorus factory/scheduler wire to call adjudicate+forget on sleep beat | chorus |
| S7 | Unit tests: tier flip, cross-domain demotion, forget invalidation | lattice |
| S8 | Integration test extending five-beat golden path | lattice |

**Params:** OMX may use design-doc defaults (`N_rule=3`, `θ*=0.6`, `θ_floor=0.3`, `d=0.95`) without further confirmation.

---

## Out-of-scope / Non-goals

| Item | Status |
|------|--------|
| Two-arm lift gate `P(lift>0) > 0.95` | **Explicit non-goal** |
| Structural `condition` field + retrieval domain filter | Deferred (user chose adjudication-only) |
| Greplica graph / BM25 / embeddings | Not in scope |
| Sibling pooling `λ` | Deferred |
| Belief tier (immutable founder rules) | Deferred |
| Auto-supersede conflict preflight (Slice C) | Not requested |
| `retrieve.py` tier×LCB reweighting | Not primary success signal (may follow) |
| PR merge | Not requested |
| Multi-role probes beyond existing backend engineer | Not required for done |

---

## Decision boundaries

| OMX may decide alone | Requires user confirmation |
|----------------------|----------------------------|
| Adjudication params from design doc §10 | Atom schema shape beyond tier+LCB if breaking |
| Test fixtures and synthetic episodes | `retrieve.py` scoring changes |
| Implementation module layout | New chorus tools or skill rewrites |
| | Cross-repo API changes beyond sleep ordering wire |

---

## Testable acceptance criteria

1. **MEMORY.md format:** After adjudicate runs, file contains lines like:
   ```markdown
   - **api.retry** [hint, LCB 0.41]: <claim>
   ```
   and after sufficient same-domain `done` beats:
   ```markdown
   - **api.retry** [rule, LCB 0.72]: <claim>
   ```

2. **Cross-domain demotion:** Given pattern keyed to `src/api/client.py`, append N beats on unrelated files with `outcome != done` → LCB drops; tier stays or reverts to `hint`.

3. **Forget:** After sleep forget phase, atom with LCB below `θ_floor` is invalidated (removed from active list / MEMORY.md).

4. **Sleep ordering:** Integration test asserts `adjudicate` runs before `packet` when gate open.

5. **Regression:** Existing lattice test suite stays green (53+ tests).

6. **Chorus wire:** Factory/scheduler calls full sleep path; no lattice tool crash on beat (E2E-14 class).

---

## Assumptions exposed

| Assumption | Resolution |
|------------|------------|
| Adjudication alone fixes wrong-domain retrieval | **Accepted with risk** — cross-domain β failures demote; structural filter deferred |
| Smallest build was A-core only | **Rejected** — user chose full sleep + chorus |
| Success = probe pass | **Rejected** — success = MEMORY.md tier/LCB visible |
| Lattice-only first | **Rejected** — both repos on feature branches |

---

## Technical context (brownfield)

- Shipped: `gate_open`, `packet`, `validate`, `apply`, `context` — per-employee isolation
- Atom store: `lattice/<employee_id>/semantic/*.json` + `MEMORY.md` view
- Chorus: 7 worker roles wired; v3 probe proved agent consolidation on t5
- Design reference: `docs/consolidation-adjudication-design.md` §7–9

---

## Execution handoff

Spec is ready. **Do not implement inside deep-interview.** Choose:

1. **`$ralplan`** (recommended) — `.omx/specs/deep-interview-adjudication-build.md` → consensus architecture plan
2. **`$autopilot`** — direct execution against this spec
3. **`$ralph`** — persistent loop until acceptance criteria met
4. **`$team`** — parallel lattice + chorus lanes
5. **Refine further** — more rounds if cross-domain β semantics need detail
