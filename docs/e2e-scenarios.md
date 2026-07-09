# Lattice E2E Testing Scenarios

**Branch:** `feat/patterns-only` · **Companion:** [integration-plan.md](integration-plan.md), [v1-plan.md](v1-plan.md)

Lattice is a Python SDK — there is no browser UI. **E2E** here means end-to-end **memory lifecycle** tests: episodic append → gate → packet → proposal → apply → context → recall drill-down. Tests are layered by seam depth.

---

## 1. Testing layers

| Layer | Scope | Repo | Runner | Status |
|---|---|---|---|---|
| **L0 — Unit** | Algorithms in isolation (gate, rank, validate) | lattice | `tests/test_*.py` | ✅ 12 tests |
| **L1 — SDK E2E** | Full consolidation loop with in-memory episodic reader | lattice | `tests/integration/` | ⬜ this doc |
| **L2 — Seam E2E** | `ChorusEpisodicReader` + real `EpisodicStore` | lattice + chorus | `tests/integration/test_chorus_seam.py` | ⬜ P1 |
| **L3 — Harness E2E** | Tools, hooks, scheduler teaser file, skills | chorus | `tests/integration/` (chorus repo) | ⬜ P1 |
| **L4 — Live agent** | 5 real beats on recurring task cluster | chorus + harness | manual / eval harness | ⬜ P1 done criteria |

**This document covers L1–L2.** L3–L4 are specified for chorus integration work (integration-plan §10, C9–C10).

---

## 2. System under test

### Memory tiers

```
WORKING (dream)     in-beat scratchpad — out of scope
EPISODIC (chorus)   every beat append — simulated via EpisodicReader
SEMANTIC (lattice)  gate-gated pattern promotion — SUT
```

### Public API (five functions)

```text
gate_open(employee_id)  → bool
packet(employee_id)     → Packet | None
validate(proposal)      → ValidationResult
apply(proposal)         → ApplyResult
context(employee_id, q) → markdown
```

### Gate invariant

```text
G(c) ⇔ |E_new| ≥ N  ∧  max_cluster_size(E_new) ≥ K
```

Defaults: **N = 5**, **K = 2**. Clustering buckets by first file prefix, intent token, or `run_id`.

### Cost policy (must hold in every scenario)

| Beat phase | Gate closed | Gate open |
|---|---|---|
| Encode (chorus append) | always | always |
| `beat_end_teaser` | silent (`""`) | gate-open notice |
| `lattice_packet` | `None` | `Packet` with engrams + hints |
| `lattice_apply` | must not run | agent/test submits Proposal |

---

## 3. Shared fixtures

### Employee

```text
employee_id: "e_be_1"
role:        backend_engineer
```

### Recurring task cluster (gate opens on beat 5)

Five beats touching `src/api/client.py` with intent `"add retry"`:

| Beat | run_id | outcome | body (abbrev) |
|---|---|---|---|
| 1 | `r_b1` | done | added retry wrapper |
| 2 | `r_b2` | done | tuned backoff base |
| 3 | `r_b3` | done | capped delay at 30s |
| 4 | `r_b4` | done | added jitter |
| 5 | `r_b5` | done | documented retry policy |

All five share `files_touched=("src/api/client.py",)` → single cluster size 5 ≥ K.

### Valid proposal (post-gate)

```json
{
  "employee_id": "e_be_1",
  "patterns": [{
    "key": "api.retry",
    "claim": "HTTP client retries use exponential backoff capped at 30s; config in src/api/client.py",
    "source_run_ids": ["r_b1", "r_b2", "r_b3", "r_b4", "r_b5"],
    "supersedes": null
  }]
}
```

### `BeatSimulator` (L1 helper)

Incrementally appends `RawEpisode` records to a growing `EpisodicReader`, rebuilds or re-reads lattice state per beat. Used by all beat-sequencing scenarios.

---

## 4. Scenario catalog

### Priority map

| ID | Scenario | Layer | Maps to |
|---|---|---|---|
| **E2E-01** | Five-beat golden path | L1 | integration-plan C10, §13 |
| **E2E-02** | Gate closed beats 1–4 (cost policy) | L1 | integration-plan §11 |
| **E2E-03** | Gate closed — scattered episodes (no cluster) | L1 | v1-plan §6.1 |
| **E2E-04** | Supersede active pattern | L1 | v1-plan §9.3 |
| **E2E-05** | Persistence across lattice restart | L1 | integration-plan §8 |
| **E2E-06** | Cross-employee isolation | L1 | integration-plan §11 |
| **E2E-07** | Validation rejection matrix | L1 | v1-plan §9.2 |
| **E2E-08** | Context retrieval + provenance | L1 | v1-plan §7.4 |
| **E2E-09** | Beat-start teaser injection | L1 | integration-plan §4.1 |
| **E2E-10** | Cursor advancement after apply | L1 | v1-plan §9.3 |
| **E2E-11** | ChorusEpisodicReader seam | L2 | integration-plan L1 |
| **E2E-12** | Tool identity binding (chorus) | L3 | integration-plan §6 |
| **E2E-13** | Scheduler teaser file (chorus) | L3 | integration-plan §4.4 |
| **E2E-14** | Beat never fails on lattice error | L3 | integration-plan §13.7 |

---

## 5. Scenario details

### E2E-01 — Five-beat golden path ⭐

**Goal:** Prove the full episodic → semantic consolidation loop.

**Given:** Empty lattice store, empty episodic history, defaults N=5 K=2.

**When:** Simulator appends beats 1–5 (recurring cluster table above).

**Then per beat:**

| Beat | `gate_open` | `beat_end_teaser` | `packet()` |
|---|---|---|---|
| 1 | `false` | `""` | `None` |
| 2 | `false` | `""` | `None` |
| 3 | `false` | `""` | `None` |
| 4 | `false` | `""` | `None` |
| 5 | `true` | contains `"gate open"` | non-empty engrams + hints |

**And after apply:**

1. `lattice.apply(proposal)` → `ok=True`, `patterns_written=1`
2. `semantic/api.retry.json` exists under employee dir
3. `MEMORY.md` regenerated with claim text
4. Beat 6: `lattice.context("e_be_1", "retry")` contains `api.retry` and `src: r_b1`
5. Cited `run_id` values exist in episodic reader

**Success criteria:** integration-plan §13 items 1–5.

---

### E2E-02 — Gate closed cost policy (beats 1–4)

**Goal:** Consolidation must not run before gate opens.

**Given:** Same fixture as E2E-01.

**When:** After beats 1–4 only.

**Then:**

- `gate_open("e_be_1")` is `false`
- `beat_end_teaser()` returns `""`
- `packet()` returns `None`
- No files under `semantic/`
- `.cursor.json` watermark unchanged (episodes_seen = 0)

**And:** Mock/spy on `apply` — must not be called by harness logic (test asserts no apply attempted).

---

### E2E-03 — Scattered episodes — gate stays closed

**Goal:** N new episodes without a cluster of size K must not open gate.

**Given:** 5 beats with **distinct** intent tokens and no shared `files_touched` (each buckets by unique `run_id`).

**When:** All 5 appended.

**Then:**

- `gate_open` is `false` (|E_new| ≥ 5 but max_cluster < 2)
- `packet()` is `None`
- No consolidation possible

---

### E2E-04 — Supersede active pattern

**Goal:** Reconsolidation replaces an active atom without DELETE.

**Given:** E2E-01 completed — `api.retry` is active.

**When:** Agent submits Proposal with:

```json
{
  "key": "api.retry",
  "claim": "HTTP retries use exponential backoff capped at 60s; config in src/api/client.py",
  "source_run_ids": ["r_b5"],
  "supersedes": "api.retry"
}
```

**Then:**

1. `validate` → `ok=True`
2. `apply` → `ok=True`
3. Old atom has `invalid_at` set
4. New atom is active with updated claim
5. `context("retry")` shows 60s cap, not 30s
6. Only one active key `api.retry`

---

### E2E-05 — Persistence across restart

**Goal:** Atoms and cursor survive process restart.

**Given:** E2E-01 completed on disk at `tmp_path`.

**When:** New `build_default(consolidated_root=tmp_path, episodes=reader)` constructed.

**Then:**

- `context("retry")` still returns `api.retry`
- `gate_open` is `false` (cursor advanced — no new episodes since consolidate)
- `.cursor.json` shows `episodes_seen=5`

**When:** 5 more beats appended (new cluster).

**Then:** Gate opens again on beat 10.

---

### E2E-06 — Cross-employee isolation

**Goal:** Patterns and provenance are per-employee.

**Given:** Employee `e_be_1` has pattern citing `r_b1`. Employee `e_fe_1` has episode `r_other` only.

**When:** `e_fe_1` submits proposal citing `r_b1` (belongs to `e_be_1`).

**Then:** `validate` rejects with `unknown source_run_id`.

**When:** `e_be_1` calls `context()`.

**Then:** `e_fe_1` patterns not visible.

---

### E2E-07 — Validation rejection matrix

**Goal:** Deterministic rules reject bad proposals before any write.

| Case | Input violation | Expected error substring |
|---|---|---|
| V1 | empty `patterns[]` | `at least one pattern` |
| V2 | 21 patterns | `exceeds max patterns` |
| V3 | `source_run_ids: []` | `at least one source_run_id` |
| V4 | `source_run_ids: ["ghost"]` | `unknown source_run_id` |
| V5 | `key: "API.Retry"` | `must match` |
| V6 | `claim: "short"` (< 20 chars) | `claim too short` |
| V7 | duplicate active key, no `supersedes` | `already active` |
| V8 | `supersedes: "missing.key"` | `is not active` |
| V9 | wrong `employee_id` in tool binding | `cross-employee` (L3 only) |

**Then for all:** `apply` leaves atom store unchanged.

---

### E2E-08 — Context retrieval + provenance

**Goal:** Two-channel read model works after consolidation.

**Given:** Pattern `api.retry` applied with `source_run_ids=(r_b1, r_b2)`.

**When:** `context("e_be_1", "retry api client")`.

**Then:**

- Markdown contains `**api.retry**:`
- Contains `src: r_b1, r_b2`
- Contains `recall(query=`
- Targeted query `"exponential backoff HTTP"` returns `api.retry` (token overlap path)
- Note: with a single active pattern, any query may still surface it via recency/activation weights

---

### E2E-09 — Beat-start teaser injection

**Goal:** Cheap push channel surfaces patterns before encoding.

**Given:** Active pattern from E2E-01.

**When:** `beat_start_teaser("e_be_1", "retry policy")`.

**Then:**

- Non-empty string
- Contains `**Distilled patterns:**`
- Contains `api.retry`
- Length ≤ 400 chars (truncation if needed)

**When:** No active patterns.

**Then:** `beat_start_teaser` returns `""`.

---

### E2E-10 — Cursor advancement

**Goal:** Successful apply advances watermark so gate closes until new episodes arrive.

**Given:** Gate open with 5 episodes.

**When:** `apply` succeeds.

**Then:**

- `.cursor.json` → `episodes_seen=5`, `last_run_id=r_b5`
- Immediate `gate_open` → `false`
- `new_episodes` count → 0

**When:** `apply` fails validation.

**Then:** Cursor **not** advanced; gate still open.

---

### E2E-11 — ChorusEpisodicReader seam (L2)

**Goal:** Adapter satisfies `EpisodicReader` against real chorus store.

**Given:** `EpisodicStore` at `tmp_path/memory` with 5 `SprintDelta` records.

**When:** `ChorusEpisodicReader(store)` wired into `build_default`.

**Then:**

- `records_for` returns `RawEpisode` tuples with correct fields
- `count_for` matches store length
- E2E-01 passes unchanged through the adapter
- `isinstance(adapter, EpisodicReader)` (structural)

**Requires:** `uv sync --extra dev` (chorus optional dep).

---

### E2E-12 — Tool identity binding (L3, chorus repo)

**Goal:** `employee_id` comes from `BeatContext`, not model args.

**When:** Agent calls `lattice_apply` with `employee_id: "e_other"` while beat context is `e_be_1`.

**Then:** Tool rejects or overwrites with beat context id; cross-employee write impossible.

---

### E2E-13 — Scheduler teaser file (L3, chorus repo)

**Goal:** Post-beat encode writes `.harness/lattice-beat-end.json` when gate open.

**When:** Beat 5 completes, gate open.

**Then:** File contains `{ "gate_open": true, "teaser": "...", "employee_id": "...", "run_id": "..." }`.

**When:** Beat 3 completes, gate closed.

**Then:** File absent or `{ "gate_open": false }`.

---

### E2E-14 — Resilience (L3, chorus repo)

**Goal:** Lattice errors never fail the beat.

**When:** `lattice_apply` throws / returns validation errors.

**Then:** Beat status remains `done`; episodic capture succeeded; error surfaced in tool result only.

---

## 6. Test file map (L1 implementation)

| File | Scenarios |
|---|---|
| `tests/integration/conftest.py` | `BeatSimulator`, episode builders |
| `tests/integration/test_five_beat_consolidation.py` | E2E-01, E2E-02 |
| `tests/integration/test_gate_scattered.py` | E2E-03 |
| `tests/integration/test_supersede_flow.py` | E2E-04 |
| `tests/integration/test_persistence.py` | E2E-05, E2E-10 |
| `tests/integration/test_employee_isolation.py` | E2E-06 |
| `tests/integration/test_validation_matrix.py` | E2E-07 |
| `tests/integration/test_context_provenance.py` | E2E-08, E2E-09 |
| `tests/integration/test_chorus_seam.py` | E2E-11 (skip if chorus unavailable) |

Run:

```bash
uv sync --extra dev
uv run pytest tests/integration -v
```

---

## 7. P1 done checklist (from integration-plan §13)

- [ ] **E2E-01** passes — 5 beats → gate → apply → context
- [ ] **E2E-02** passes — no consolidation beats 1–4
- [ ] **E2E-08** passes — context shows `src:` ids
- [ ] **E2E-11** passes — cited `run_id` readable via chorus store
- [ ] **E2E-12–14** pass in chorus repo
- [ ] Import graph clean (`test_import_graph.py`)
- [ ] Beat never fails because lattice threw

---

## 8. Out of scope (deferred)

| Item | Why |
|---|---|
| Playwright / browser tests | No UI |
| Habit / procedural memory | `feat/patterns-only` branch |
| Background consolidate worker | Manual/agent path first |
| `lattice_validate` separate tool | validate inside apply |
| Embeddings / FTS retrieval | BM25/overlap suffices P1 |
| LLM-authored proposals in CI | Agent authors; tests use fixtures |

---

*The agent remembers what happened (`recall`). The org remembers what mattered (patterns). E2E tests prove lattice knows when to sleep.*
