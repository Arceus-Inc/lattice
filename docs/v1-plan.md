# lattice v1 — lean plan

**Status:** L0 scaffold aligned to proposal validate/apply model.

lattice is a **deterministic memory algebra** over chorus engrams. The employee agent is the only author of durable memory; lattice ranks evidence, validates proposals, stores atoms, and retrieves by score.

## THE LOOP

| Stage | Owner |
|---|---|
| WRITE / STORE / `recall()` pull | chorus |
| RANK / gate / packet hints | lattice |
| Author `Proposal` from prose + traces | agent |
| validate / apply | lattice |
| context(query) for next beat | lattice |

## Five functions

```text
1. gate_open(employee_id) → bool
2. packet(employee_id)      → Packet | ∅        # if gate open
3. validate(proposal)       → ValidationResult
4. apply(proposal)          → ApplyResult        # validate internal
5. context(employee_id, q)  → markdown facts
```

Everything else is implementation detail.

## Math spec

**Inputs:** engrams `E`, cursor `c`, active atoms `A`, query `q`.

**Gate** (single function, no OR-chain):

```text
G(c) ⇔ |E_new| ≥ N  ∧  max_cluster_size(E_new) ≥ K
```

`E_new` = episodes since cursor watermark (`total − episodes_seen`).

**Cluster:** greedy bucket on primary file prefix (or intent token if no files).

**Packet hints** (deterministic, optional):

```text
hints = { (key_template, run_ids) : |cluster| ≥ K }
```

**Proposal:** agent supplies ops `O = { assert | supersede | patch }`.

**Validate** (v1 rules):

1. Every op cites ≥1 `run_id` that exists for this employee
2. `patch` ops require ≥1 cited engram with `outcome=done`
3. Keys match `^[a-z][a-z0-9_.]+$`
4. `assert` on key that is already active → error (use `supersede`)
5. `supersede` must name an active key
6. `|ops| ≤ L`

**Apply:** ADD via `assert`; replace via `supersede` (set `invalid_at`, write new); `patch` → overlay store. Advance cursor on success.

**Retrieve:**

```text
score(q, a) = w_r·recency(a) + w_b·overlap(q, a.key + a.value) + w_a·activation(a)
```

Return top‑k active atoms rendered as Markdown.

## Types (4 primitives)

| Type | Role | Storage |
|---|---|---|
| `RawEpisode` | engram vertex (read-only from chorus) | chorus |
| `Atom` | `(key, value, src, t_valid, t_invalid, activation)` | `semantic/*.json` + `MEMORY.md` view |
| `Op` / `Proposal` | agent-authored write intent | transient |
| `SkillPatch` | procedural overlay | `evolved-skills/<slug>/SKILL.md` |

No Bond, Schema, Script, Prior, Cue, PromotionCandidate, or lattice-owned LLM extractors.

## Package map

```text
src/lattice/
  contracts/     episodic, atom, patch, cursor ports
  domain/        Proposal, Op, Packet, ValidationResult, ApplyResult
  cluster.py     gate, rank, cluster, packet hints
  validate.py    pure validation rules
  apply.py       transactional writes
  retrieve.py    score + context markdown
  stores/        MemoryMdStore, OverlaySkillStore, JsonCursorStore
  facade.py      Lattice (5 functions)
  compose.py     build_default()
```

## Milestones

| Milestone | Delivers |
|---|---|
| **L0** | This scaffold — gate, packet, validate, apply, context stubs |
| **L1** | `ChorusEpisodicReader` seam test against real chorus |
| **L2** | End-to-end agent proposal round-trip in tests |
| **L3** | Activation bump on context hit; tune retrieval weights |
| **L4** | `patch` ops + overlay store (procedural P1) |
| **L5** | Optional hook enqueue + embeddings |

## Deferred (not v1)

- Background dream `STOP` worker — manual `packet()` first
- `lattice_validate` tool (validate is internal to `apply`)
- Two-arm critic / SSGM middleware
- DELETE ops — supersede only
- Greplica component/flow/claim ontology
- Separate neuroscience module names in code

## Integration (v1)

### Beat policy — episodic cheap, consolidation expensive

| When | What | Cost |
|---|---|---|
| Every beat (automatic) | chorus appends episodic engram | cheap |
| Beat start (optional) | `lattice_context(query)` + `lattice-context` skill | cheap read |
| Mid-beat | `recall()` / `recall(query)` | cheap read |
| Beat end (gate closed) | **nothing** — default for most beats | free |
| Beat end (gate open) | `lattice-consolidate` skill → packet → Proposal → apply | expensive |

Gate defaults: **N = 5** new beats, **K = 2** cluster size. Tune via `build_default(min_new_episodes=…)`.

### Employee skills

Shipped under `skills/` (materialize into `.harness/skills/` like role skills):

| Skill | Teaches |
|---|---|
| `lattice-context` | When `lattice_context` vs `recall` at beat-start |
| `lattice-consolidate` | Beat-end workflow when gate is open only |

Brief directives for composition roots: `lattice.directive.LATTICE_CONTEXT_DIRECTIVE`, `LATTICE_CONSOLIDATE_DIRECTIVE`, `beat_end_notice()`.

### Tools (L5 wiring in chorus)

`lattice_context(query)`, `lattice_packet()`, `lattice_apply(proposal_json)`. `recall()` stays chorus.

Beat-end injection: `lattice.beat_end_teaser(employee_id)` — silent when gate closed.
