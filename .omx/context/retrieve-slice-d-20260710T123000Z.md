# Context — Retrieve Slice D + domain gate

**Task:** Plan implementation of design-doc Slice D (tier × LCB retrieval) plus a simple structural domain gate to fix wrong-domain pattern surfacing.

**Desired outcome:** `lattice_context("retry")` returns `api.retry`; `lattice_context("design tokens")` does not surface `api.retry` unless explicitly keyed. Rule-tier patterns outrank hint-tier at equal query overlap.

**Known facts:**
- Shipped: adjudicate/forget, MEMORY.md tier+LCB, live probe t6+t7 retrieval loop (chorus `feat/lattice-integration`, lattice `feat/patterns-only`, pushed).
- `retrieve.py` scores: `0.3·recency + 0.5·overlap + 0.2·activation` — no tier/LCB, no domain filter.
- `adjudicate.py` already has `key_files_for_atom()` + `fingerprint_overlap()` — reuse at retrieve time.
- `lattice_context` tool only passes `query` + `limit` — no beat files today.
- Atom has no persisted `key_files`; resolved from episodic at adjudicate time.
- Deep research (Jul 2026): small catalogs need keyword/structure + trust weight, not vectors first.
- Design doc §9 Slice D: "Retrieval weights tier × LCB × overlap"; structural key-match deferred but cross-domain β alone insufficient.

**Constraints:**
- Lattice-first; minimal chorus diff unless probe assertion needs it.
- No vector DB, no LLM at retrieve layer.
- Preserve E2E-14: lattice tools never crash beat.
- Backward compatible when domain signals absent.

**Unknowns (resolved by plan defaults):**
- Domain gate signal: persist `key_files` on atom at apply vs resolve episodic at retrieve vs query-key heuristic only → **persist at apply + optional query-key escape hatch**.
- Chorus `files_hint` auto-injection → defer to follow-up; v1 uses query + stored key_files only.

**Touchpoints:**
- `src/lattice/retrieve.py`, `src/lattice/contracts/atom.py`, `src/lattice/apply.py`, `src/lattice/stores/memory_md.py`
- `src/lattice/facade.py` (if retrieve needs episodes for key_files — prefer persist on atom)
- `tests/components/test_retrieve.py`, `tests/test_retrieve.py`, new `tests/test_retrieve_domain.py`
- `tests/integration/test_context_provenance.py`, `tests/integration/test_employee_isolation.py`
- `chorus/examples/backend_engineer_lattice_5beat_probe.py` (optional t8 wrong-domain assertion)
- `docs/consolidation-adjudication-design.md` (gap table update — optional)
