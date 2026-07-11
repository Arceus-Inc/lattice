# Adjudication build — context snapshot

**Task:** Deep-interview the consolidation-adjudication spec before building Slice A (or broader).

**Desired outcome (hypothesis):** Ship outcome-grounded pattern tiers (`hint` → `rule`) so lattice promotes/demotes atoms from honest beat outcomes, not agent assertion alone.

**Stated solution:** Implement `lattice/adjudicate.py` per `docs/consolidation-adjudication-design.md` — starting with Slice A-core discussed in chat.

**Probable intent:** Close the gap between shipped patterns-only loop (agent apply = durable forever) and draft v1 epistemics ("prose proposes, outcomes dispose") before merging chorus/lattice PRs or scaling to other employee roles.

## Known facts (brownfield evidence)

- **Shipped:** gate → packet → validate → apply → context on `feat/patterns-only` (53 tests)
- **Chorus wired:** 7 worker roles have lattice tools/skills; reviewer reads `lattice_context`; manager has no lattice
- **Live probe:** backend engineer v3 — agent consolidated on t5 (`lattice_packet`, `get_run`×2, `lattice_apply`); semantic atom `api__retry.json` + MEMORY.md
- **Atom today:** flat `key`, `value`, `source_run_ids`, `activation` — no `tier`, no `(α, β)` stats
- **Cursor:** per-employee watermark in `lattice/.cursor.json`
- **Clustering:** file prefix or intent token; gate N=5, K=2
- **Greplica comparison:** same agent-author / validate-apply boundary; Greplica has graph retrieval, no outcome adjudication
- **Proposed smallest build:** `adjudicate.py` + stats sidecar; single-arm first; defer lift gate, forget, BMM, auto-supersede

## Constraints

- Lattice must not import chorus
- No lattice-owned LLM extractors
- `c_p = 0` in agent-authored mode (no prose pseudo-votes)
- Patterns-only branch scope (habits deferred)
- PRs open, not merged (chorus #64, lattice #1)

## Unknowns / open questions

- Which slice is in scope for *this* build (A-core only vs A-wire vs C/D)?
- Must adjudication be visible to agent (`MEMORY.md` tier/LCB) or internal-only first?
- Per-role gate tuning required before adjudication?
- Chorus facade ordering: adjudicate before packet on sleep beat — required for v1 or defer?
- Parameter defaults (`N_rule`, `θ*`, `d`) — accept doc guesses or tune on probe first?

## Decision-boundary unknowns

- What may be decided without user confirmation (params, schema, chorus wire)?
- Is cross-repo change (chorus) in scope or lattice-only first?
- Commit/push/merge policy for this build?

## Likely touchpoints

- `lattice/src/lattice/adjudicate.py` (new)
- `lattice/src/lattice/contracts/atom.py`, `stores/memory_md.py`
- `lattice/src/lattice/facade.py`
- `lattice/tests/test_adjudicate.py`, integration tests
- Optional: `chorus/src/chorus_harness/_factory.py` (sleep ordering)
- `docs/consolidation-adjudication-design.md`
