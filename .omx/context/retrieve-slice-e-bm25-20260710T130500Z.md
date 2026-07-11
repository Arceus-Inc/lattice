# Context — Retrieve Slice E: BM25 relevance (rank_bm25)

**Task:** Add BM25 keyword relevance to lattice retrieval using the `rank_bm25` package, replacing naive token overlap in scoring while preserving Slice D domain gate + trust weighting.

**Desired outcome:** `top_k` ranks factual atoms by BM25 relevance + tier/LCB trust; domain gate unchanged; all existing retrieve tests + probe checks still pass; new tests prove BM25 beats overlap on ambiguous multi-atom queries.

**Known facts:**
- Slice D shipped and live-verified (v7 probe: `context_design_excludes_retry: true`, `t7_all_pass: true`).
- `retrieve.py` scoring: `0.35·trust + 0.40·overlap + 0.15·recency + 0.10·activation`.
- `eligible()` uses `_overlap >= 0.15` OR key-segment OR key_files path-component match.
- Atoms are short facts: `key` (dotted) + `value` (2–3 sentences) + optional `key_files`.
- Catalog size today: <20 atoms/employee; PRD Slice D deferred BM25 until catalog grows — user now wants it anyway.
- `rank_bm25` provides `BM25Okapi`; no preprocessing built-in; ~8KB wheel, Apache-2.0, last release 2022.
- No vectors, no LLM at retrieve layer (design invariant).

**Constraints:**
- Lattice-only (no chorus changes unless probe assertion tweak).
- Keep `facade.context()` signature unchanged.
- Domain gate must remain independent of relevance ranking.
- `rank_bm25` as explicit runtime dependency (user request).
- Backward compatible: empty corpus → empty context; single atom → works.

**Unknowns (plan defaults):**
- Eligibility signal: keep `_overlap` for gate vs use BM25 threshold → **keep structural gate unchanged; BM25 only in `score()`**.
- Index scope: per-query rebuild on active atoms (no persistence) → **yes, O(n) per call is fine for n<50**.
- Doc fields: key repeated with dot-split boost → **doc = key + dotted segments + value + key_files tokens**.

**Touchpoints:**
- `pyproject.toml` (add `rank-bm25`)
- `src/lattice/retrieve.py` (BM25 module + score blend)
- `tests/test_retrieve_domain.py`, `tests/components/test_retrieve.py`, new `tests/test_retrieve_bm25.py`
- `docs/consolidation-adjudication-design.md` (gap table, optional)
- No chorus probe change required (Slice D checks still valid)
