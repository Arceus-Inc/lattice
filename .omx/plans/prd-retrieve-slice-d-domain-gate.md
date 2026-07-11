# PRD — Retrieve Slice D: tier×LCB scoring + structural domain gate

**Source:** `.omx/context/retrieve-slice-d-20260710T123000Z.md`, `docs/consolidation-adjudication-design.md` §9 Slice D, deep-research Jul 2026  
**Branches:** lattice `feat/patterns-only`, chorus `feat/lattice-integration` (probe only)  
**Status:** Consensus APPROVED (Planner + inline Architect/Critic)  
**Plan path:** `.omx/plans/prd-retrieve-slice-d-domain-gate.md`

---

## RALPLAN-DR Summary

### Principles

1. **Trust surface must affect retrieval** — tier/LCB in MEMORY.md is meaningless if `lattice_context` ignores it.
2. **Structure before semantics** — file-prefix fingerprint overlap beats token overlap for wrong-domain rejection (design doc §8.2).
3. **Small-catalog simplicity** — no vectors; deterministic scoring on <30 atoms per employee.
4. **Backward compatible** — empty domain signal → current behavior + trust weight (no breaking API).
5. **Reuse adjudicate primitives** — `key_files_for_atom` / `fingerprint_overlap` are the single source of truth.

### Decision Drivers

1. Wrong-domain surfacing (`api.retry` on non-API beats) is the original failure mode adjudication alone did not fix in t7.
2. Research consensus: for small pattern catalogs, keyword/structure + trust weight outperforms adding embeddings first.
3. `lattice_context` has no beat-file input today — solution must work with query-only v1, improve with persisted `key_files`.

### Options Considered

| Option | Verdict |
|--------|---------|
| **A — Persist `key_files` on atom + tier×LCB score + query-domain gate** | **CHOSEN** |
| B — Query-key heuristic only (split `api.retry` tokens) | Rejected — brittle; `retry` matches too broadly |
| C — Chorus auto-inject `files_hint` from task episodic | Deferred follow-up — higher wiring cost |
| D — Vector/hybrid retrieval (BM25+embeddings) | Rejected for v1 — catalog size <20; ops overhead |

**Invalidation rationale:**
- **B** fails on shared tokens (`retry`, `api`) and cannot use file overlap.
- **C** is correct long-term but blocked on harness passing beat fingerprint into tool; not required for first e2e proof.
- **D** violates "simple first" and does not fix domain without structure anyway.

---

## Architect Review (inline)

### Steelman antithesis

> "Don't persist `key_files` or add domain gates — only multiply score by LCB and let cross-domain β eventually demote wrong patterns. Retrieval stays query-only forever."

**Counter:** β demotion is slow and invisible at retrieve time; users still see bad patterns until many unrelated failures accumulate. Slice D without domain gate does not address the stated failure mode. Persisting `key_files` at apply is cheap (already computed) and makes retrieve independent of episodic reader.

### Tradeoff tension

**Strict domain gate vs recall:** filtering atoms with zero query relevance AND zero key-prefix match may hide useful patterns when the agent asks a vague query (`"what do we know?"`). Mitigation: **gate is soft-exclude** — if query tokens overlap `atom.key` (dot-split) or overlap score > ε, bypass gate; only hard-exclude when query is clearly different domain (e.g. `design tokens` vs `api.retry`).

### Synthesis

- Persist `key_files: tuple[str, ...]` on `Atom` at `apply()` time (from cited `source_run_ids`).
- `retrieve.py`: new `score_trust(atom) = tier_bonus + lcb05` blended into total score.
- `filter_eligible(query, atom)`: include if explicit key mention OR query overlap ≥ ε OR key-prefix token in query; else require `domain_overlap(query, atom.key_files)` via query token matching path segments in key_files (e.g. query contains `api` and key_files under `src/api/`).
- v1 simpler gate: **exclude atom when** `overlap(query, atom) < MIN_OVERLAP` **and** no dot-segment of `atom.key` appears in query **and** no path-prefix token from `key_files` appears in query.

---

## Critic Review (inline)

**Verdict: APPROVE**

| Criterion | Status |
|-----------|--------|
| Principle-option consistency | ✅ |
| Testable acceptance criteria | ✅ unit + integration |
| Verification steps | ✅ pytest + optional probe assertion |
| Risk mitigation | ✅ backward compat + soft gate |
| Alternatives explored | ✅ B, C, D invalidated |

**Required test additions:**
1. `rule` outranks `hint` at equal overlap and recency
2. `api.retry` not returned for query `"design tokens typography"`
3. `api.retry` returned for query `"retry policy api"`
4. Atoms without `key_files` (legacy) still retrievable by overlap
5. Integration: `test_employee_isolation` FE pattern not returned for BE query

---

## Scope

### In scope (lattice)

| # | Deliverable |
|---|-------------|
| 1 | Extend `Atom` with optional `key_files: tuple[str, ...]` |
| 2 | Seed `key_files` in `apply.py` from episodic `source_run_ids` |
| 3 | Serialize `key_files` in `memory_md.py` JSON + preserve on invalidate |
| 4 | Rewrite `retrieve.score()` → trust + overlap + recency + activation |
| 5 | Add `eligible(query, atom)` domain gate before scoring |
| 6 | Unit tests + extend integration tests |
| 7 | Optional: integration test for cross-domain demotion → lower rank (not hide) |

### In scope (chorus, minimal)

| # | Deliverable |
|---|-------------|
| 8 | Probe post-check: programmatic `lattice.context("design")` must not include `api.retry` after retry cluster consolidate |

### Out of scope

- `files_hint` on `lattice_context` tool (follow-up)
- Vector / BM25 index
- Two-arm lift gate
- Auto-supersede (Slice C)
- MEMORY.md format changes

---

## Technical Design

### Atom extension

```python
@dataclass(frozen=True)
class Atom:
    ...
    key_files: tuple[str, ...] = ()  # union files_touched from source_run_ids at apply
```

Populate in `apply_proposal` via episodic lookup (same as `key_files_for_atom`).

### Scoring (Slice D)

```text
trust = (1.0 if tier == rule else 0.0) * W_TIER + lcb05(atom.stats) * W_LCB
score = W_TRUST·trust + W_OVERLAP·overlap + W_RECENCY·recency + W_ACT·activation
```

Starting weights (tune in tests):
- `W_TRUST=0.35`, `W_OVERLAP=0.40`, `W_RECENCY=0.15`, `W_ACT=0.10`
- `W_TIER` inside trust: rule gets +0.15 boost on top of LCB

### Domain gate (v1)

```text
eligible(query, atom) :=
  overlap(query, atom) >= MIN_OVERLAP (0.15)
  OR any segment of atom.key (split ".") is substring of query
  OR any path component from atom.key_files appears as token in query
     (e.g. key_files contains "src/api/client.py" → tokens {src, api, client, py})
```

If not eligible → atom excluded from `top_k` (not merely deprioritized).

**Legacy atoms** with empty `key_files`: eligible if `overlap >= MIN_OVERLAP` OR key segment match (same as today, slightly stricter).

### API surface

- `facade.context()` — unchanged signature
- `render_context()` / `top_k()` — accept optional `min_overlap` param internally; no public facade break

---

## Acceptance Criteria

- [ ] `Atom.key_files` persisted in `semantic/*.json` after apply
- [ ] `score(rule_atom) > score(hint_atom)` for same query/overlap/recency in unit test
- [ ] `top_k("design tokens", atoms)` does not include `api.retry` when only retry atom exists
- [ ] `top_k("retry api", atoms)` includes `api.retry`
- [ ] `test_context_provenance` and `test_employee_isolation` still pass
- [ ] Full lattice pytest green (62+ tests)
- [ ] Probe JSON records `context_design_excludes_retry: true` (programmatic check at end)

---

## Implementation Steps

### Phase 1 — Atom + apply (lattice)

1. Add `key_files` to `Atom`, JSON serde in `memory_md.py`
2. In `apply.py`, resolve `key_files` from episodic records for `source_run_ids`
3. Test: apply proposal → JSON contains `key_files`

### Phase 2 — Retrieve (lattice)

4. Add `eligible()` + updated `score()` in `retrieve.py`
5. Wire `top_k` to filter then rank
6. Tests in `tests/test_retrieve_domain.py` + update `tests/components/test_retrieve.py`

### Phase 3 — Integration + probe

7. Extend `test_employee_isolation` / `test_context_provenance` if needed
8. Add programmatic check to `backend_engineer_lattice_5beat_probe.py`
9. Run `uv run pytest -q` (lattice) + lattice harness tests (chorus)

---

## Verification

```bash
# Lattice
cd lattice && uv run pytest tests/components/test_retrieve.py tests/test_retrieve.py tests/test_retrieve_domain.py tests/integration/ -q
cd lattice && uv run pytest -q

# Chorus (wiring unchanged; probe assertion only)
cd chorus && uv run pytest tests/harness/test_lattice_*.py tests/tools/test_lattice_tool.py -q
```

**E2e proof:** existing 5+2 probe still passes; new assertion `lattice.context(employee, "design")` lacks `api.retry`.

---

## ADR

**Decision:** Persist `key_files` on atoms at apply; filter retrieval with a lightweight domain gate; weight scores by tier×LCB.

**Drivers:** Wrong-domain surfacing; small-catalog simplicity; trust metadata must affect read path.

**Alternatives considered:** Query-only gate, chorus `files_hint`, vector hybrid — rejected (see Options table).

**Why chosen:** Reuses adjudicate fingerprint logic; no chorus API change; deterministic; testable in unit tests without LLM.

**Consequences:**
- Slightly stricter retrieval may hide patterns on vague queries — mitigated by key-segment escape hatch
- Old atoms without `key_files` need overlap-only path until re-applied
- Future `files_hint` param composes cleanly with persisted `key_files`

**Follow-ups:**
- Chorus `lattice_context(files_hint=...)` from task episodic
- Cross-domain demotion integration test (failing unrelated beat → LCB drop)
- BM25 hybrid if catalog >30 patterns
- Slice C auto-supersede

---

## Execution Handoff

### `$ralph` (recommended — sequential, lattice-heavy)

```text
$ralph .omx/plans/prd-retrieve-slice-d-domain-gate.md
```

| Step | Lane | Suggested agent |
|------|------|-----------------|
| 1 | Atom + apply + serde | coder |
| 2 | retrieve.py + tests | coder + python-reviewer |
| 3 | integration + probe assertion | coder + tester |

**Reasoning:** medium for retrieve scoring tuning; low elsewhere.

### `$team` (parallel)

| Lane | Scope |
|------|-------|
| A | Atom + apply + memory_md serde |
| B | retrieve.py + unit tests |
| C | integration tests + probe check |

**Team verification:** all lattice pytest green + probe programmatic domain check.  
**Ralph follow-up:** run probe only if user requests live confirmation.

### Available agent types (follow-up roster)

`coder`, `python-reviewer`, `tester`, `architect` (optional sanity), `build-error-resolver` (if types break)

---

## Changelog (consensus)

- Chose persist `key_files` over episodic resolve-at-retrieve (no reader dependency in retrieve layer)
- Soft domain gate with key-segment escape hatch per Architect tradeoff
- Deferred chorus `files_hint` to follow-up
- Probe gets programmatic check only (no new LLM beat)
