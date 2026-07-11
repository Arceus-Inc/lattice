# PRD — Retrieve Slice E: BM25 relevance via `rank_bm25`

**Source:** `.omx/context/retrieve-slice-e-bm25-20260710T130500Z.md`, design doc §9 Slice D follow-up  
**Branches:** lattice `feat/patterns-only` (chorus unchanged)  
**Status:** Consensus APPROVED (Planner + inline Architect/Critic)  
**Plan path:** `.omx/plans/prd-retrieve-slice-e-bm25.md`

---

## RALPLAN-DR Summary

### Principles

1. **Gate ≠ rank** — domain exclusion (`eligible`) stays structural; BM25 only improves relevance among in-domain atoms.
2. **Facts are short docs** — atoms (`key` + claim + `key_files`) are ideal BM25 corpus entries; no chunking or embeddings.
3. **Trust stays separate** — tier/LCB weights belief; BM25 weights lexical match. Don't conflate them.
4. **Rebuild-per-query is fine** — catalog <50 atoms/employee; no persisted index until proven necessary.
5. **Minimal dependency** — use battle-tested `rank_bm25` (user choice) with explicit tokenization we control.

### Decision Drivers

1. Naive `_overlap` (query-token recall) can't rank well when multiple atoms partially match the same query.
2. v7 probe proved domain gate works; next quality lever is relevance ranking within the eligible set.
3. User explicitly requested `rank_bm25` — not hand-rolled BM25.

### Options Considered

| Option | Verdict |
|--------|---------|
| **A — `rank_bm25.BM25Okapi` replaces overlap in `score()`, gate unchanged** | **CHOSEN** |
| B — Hand-rolled BM25 (~50 lines, zero deps) | Rejected — user asked for `rank_bm25`; maintenance cost |
| C — BM25 for gate + score (replace `eligible` overlap check) | Rejected — BM25 threshold is corpus-relative; breaks Slice D domain semantics |
| D — Defer until catalog >30 | Rejected — user wants it now; cost is low |

**Invalidation rationale:**
- **B** ignores explicit user preference for `rank_bm25`.
- **C** couples wrong-domain rejection to IDF statistics that shift as catalog grows.
- **D** no longer applies given user directive.

---

## Architect Review (inline)

### Steelman antithesis

> "Don't add `rank_bm25` — naive overlap is enough for <20 atoms, and BM25 IDF on tiny corpora is noisy. A generic word like `retry` gets low IDF when every doc mentions it, so BM25 adds complexity without better ranking. Keep overlap and tune weights."

**Counter:** Overlap already fails when two atoms share vocabulary density differently (e.g. `api.retry` vs `api.timeout` both mention "HTTP client"). BM25's TF component still differentiates term frequency within docs; IDF noise on tiny corpora is mitigated by min-max normalization and trust weight. Dependency cost is one small Apache-2.0 package.

### Tradeoff tension

**Corpus-wide IDF vs eligible-only index:** Building BM25 only on eligible atoms changes IDF per query (unstable). Building on all active atoms then masking ineligible is correct but means an ineligible atom still affects IDF for others. **Mitigation:** acceptable at n<50; document assumption; revisit if catalog grows.

### Synthesis

- Keep `eligible()` exactly as Slice D — no BM25 in gate.
- Add `_atom_doc(atom) -> str` and `_tokenize(text) -> list[str]` helpers in `retrieve.py` (or `retrieve_bm25.py` if file grows).
- `top_k()`: build BM25 on all atoms → score all → zero/mask ineligible → blend with trust/recency/activation → sort.
- Replace `WEIGHT_OVERLAP` with `WEIGHT_BM25` (start 0.40, same slot).
- Key boost: repeat dot-segments in doc string (`api.retry` → `"api retry api retry …"`) — cheap field weighting without custom BM25 params.
- **Do not** use `bm25.get_top_n` directly — we need trust/recency blend, so use `get_scores` only.

**Verdict: APPROVE** with corpus-wide index + ineligible masking.

---

## Critic Review (inline)

**Verdict: APPROVE**

| Criterion | Status |
|-----------|--------|
| Principle-option consistency | ✅ gate/rank separation preserved |
| Testable acceptance criteria | ✅ unit tests for ranking + gate regression |
| Verification steps | ✅ pytest + existing integration suite |
| Risk mitigation | ✅ normalization, empty corpus, single-atom edge cases |
| Alternatives explored | ✅ B, C, D invalidated |

**Required test additions:**
1. BM25 ranks `api.retry` above `ui.theme` for query `"retry exponential backoff"`
2. Two retry-related atoms — more specific claim wins
3. `eligible` / domain gate tests unchanged and still pass
4. Empty atoms → empty context
5. Single atom → retrievable
6. `test_rule_outranks_hint` still passes (trust dominates when BM25 tied)

---

## Scope

### In scope (lattice)

| # | Deliverable |
|---|-------------|
| 1 | Add `rank-bm25` to `pyproject.toml` dependencies |
| 2 | `atom_doc()` + `tokenize()` helpers |
| 3 | `bm25_scores(query, atoms) -> dict[key, float]` with corpus-wide BM25Okapi |
| 4 | Replace `_overlap` in `score()` with normalized BM25; keep `_overlap` for `eligible()` only |
| 5 | `top_k()` masks ineligible atoms after scoring |
| 6 | Unit tests in `tests/test_retrieve_bm25.py` |
| 7 | Update `tests/components/test_retrieve.py` if score assertions need tuning |

### Out of scope

- Chorus probe changes (Slice D checks remain sufficient)
- Persisted BM25 index across calls
- Stopword removal / stemming (v1: whitespace + lowercase + punct strip)
- Vector embeddings
- `files_hint` on `lattice_context`
- Changing `eligible()` semantics

---

## Technical Design

### Dependency

```toml
dependencies = [
  "dream",
  "rank-bm25>=0.2.2",
]
```

Import: `from rank_bm25 import BM25Okapi`

### Document construction

```python
def atom_doc(atom: Atom) -> str:
    segments = atom.key.replace(".", " ")
    paths = " ".join(atom.key_files).replace("/", " ").replace("\\", " ")
    # Repeat key segments for mild field boost (key matches weigh more)
    return f"{atom.key} {segments} {segments} {atom.value} {paths}"
```

### Tokenization (v1)

```python
def tokenize(text: str) -> list[str]:
    cleaned = text.lower()
    for ch in ".,;:!?()[]{}":
        cleaned = cleaned.replace(ch, " ")
    return [t for t in cleaned.split() if len(t) >= 2]
```

### Scoring (Slice E)

```text
bm25_raw  = BM25Okapi(corpus).get_scores(tokenize(query))  # per atom index
bm25_norm = min_max_normalize(bm25_raw)                     # 0..1 across corpus
trust     = tier_bonus + lcb05
score     = W_BM25·bm25_norm + W_TRUST·trust + W_RECENCY·recency + W_ACT·activation
```

Starting weights (same slots as Slice D):
- `W_BM25=0.40`, `W_TRUST=0.35`, `W_RECENCY=0.15`, `W_ACT=0.10`

### `top_k` flow

```text
1. atoms = active atoms for employee
2. corpus = [tokenize(atom_doc(a)) for a in atoms]
3. bm25 = BM25Okapi(corpus)
4. raw_scores = bm25.get_scores(tokenize(query))
5. For each atom: if not eligible(query, atom): skip
6. else: final_score = blend(bm25_norm[i], trust, recency, activation)
7. Return top k by final_score
```

### Edge cases

| Case | Behavior |
|------|----------|
| Empty atoms | `top_k` → `()` |
| Single atom, eligible | return it |
| All ineligible | `top_k` → `()` |
| All BM25 scores 0 | `bm25_norm` → 0 for all; trust/recency breaks ties |
| Tied BM25 + trust | recency then activation (existing sort stability) |

---

## Acceptance Criteria

- [ ] `rank-bm25` in `pyproject.toml`; `uv sync` resolves
- [ ] `score()` uses BM25, not overlap
- [ ] `eligible()` still uses overlap/key_segment/key_files (unchanged)
- [ ] `test_design_query_excludes_api_retry` passes
- [ ] `test_rule_outranks_hint_at_equal_overlap` passes (rename if needed)
- [ ] New: BM25 ranks more specific atom above weaker partial match
- [ ] Full lattice pytest green (69+ tests)
- [ ] Optional: re-run v7 probe — `context_design_excludes_retry` still true

---

## Implementation Steps

### Phase 1 — Dependency + helpers

1. Add `rank-bm25>=0.2.2` to `pyproject.toml`
2. Add `atom_doc()`, `tokenize()`, `_normalize_scores()` to `retrieve.py`
3. Test tokenize/doc helpers in isolation

### Phase 2 — BM25 scoring

4. Add `_bm25_relevance(query, atoms) -> tuple[float, ...]` aligned to atom order
5. Update `score()` to accept precomputed `bm25_norm` or compute internally
6. Update `top_k()` to filter eligible after corpus-wide score

### Phase 3 — Tests + regression

7. Add `tests/test_retrieve_bm25.py`
8. Run `uv run pytest -q` — all green
9. Spot-check: `context("design tokens typography")` still empty with only `api.retry`

---

## Verification

```bash
cd lattice && uv sync
cd lattice && uv run pytest tests/test_retrieve_bm25.py tests/test_retrieve_domain.py tests/components/test_retrieve.py -q
cd lattice && uv run pytest -q
```

---

## ADR

**Decision:** Replace naive token overlap in retrieval scoring with `rank_bm25.BM25Okapi`; keep Slice D domain gate unchanged.

**Drivers:** Better ranking among partial matches; atoms are short factual docs; user requested `rank_bm25`.

**Alternatives considered:** Hand-rolled BM25, BM25-for-gate, defer — rejected (see Options table).

**Why chosen:** Clean separation of gate vs rank; battle-tested dep; minimal code; fits existing blend architecture.

**Consequences:**
- New runtime dependency (`rank-bm25`, unmaintained since 2022 but stable)
- Per-query O(n) index build — fine until catalog ~50+
- IDF on tiny corpora can be noisy — trust weight provides stabilizer

**Follow-ups:**
- Stopword list for English function words if generic queries pollute ranking
- Persisted inverted index if catalog >50
- Cross-encoder rerank if synonyms become a problem
- Chorus `files_hint` composes with BM25 doc fields

---

## Execution Handoff

### `$ralph` (recommended — small, sequential)

```text
$ralph .omx/plans/prd-retrieve-slice-e-bm25.md
```

| Step | Lane | Agent | Reasoning |
|------|------|-------|-----------|
| 1 | dep + helpers | coder | low |
| 2 | score/top_k wiring | coder | medium |
| 3 | tests + regression | coder + python-reviewer | low |

### `$team` (optional parallel)

| Lane | Scope |
|------|-------|
| A | pyproject + helpers |
| B | retrieve.py scoring |
| C | tests |

**Team verification:** full lattice pytest green; domain gate tests unchanged.

### Available agent types

`coder`, `python-reviewer`, `tester`, `architect` (sanity), `build-error-resolver`

---

## Changelog (consensus)

- Chose corpus-wide BM25 + ineligible mask over eligible-only index
- Kept `eligible()` overlap logic; BM25 scoring only
- Key segment repetition in `atom_doc` for mild boost
- No chorus/probe changes in v1
