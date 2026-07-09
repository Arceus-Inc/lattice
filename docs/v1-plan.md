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

**Proposal:** agent supplies `patterns[]` (semantic) and `habits[]` (procedural). lattice compiles to internal ops and applies.

```json
{
  "patterns": [{ "key", "claim", "source_run_ids", "supersedes?" }],
  "habits": [{ "action": "evolve|create", "skill|slug", "section?", "body", "source_run_ids" }]
}
```

**Validate** (v1 rules):

1. ≥1 pattern or habit; total ≤ L
2. Every item cites ≥1 valid `run_id` for this employee
3. Pattern keys match `^[a-z][a-z0-9_.]+$`
4. `assert` pattern on active key → error (set `supersedes`)
5. Habit requires ≥1 cited engram with `outcome=done`
6. Habit `create` slug must not collide with canonical role skills

**Apply:** patterns → atoms; habits `evolve` → patch overlay; habits `create` → draft overlay.

**Retrieve:**

```text
score(q, a) = w_r·recency(a) + w_b·overlap(q, a.key + a.value) + w_a·activation(a)
```

Return top‑k active atoms rendered as Markdown.

## Types (5 primitives)

| Type | Role | Storage |
|---|---|---|
| `RawEpisode` | engram vertex (read-only from chorus) | chorus |
| `PatternDraft` → `Atom` | declarative fact | `semantic/*.json` + `MEMORY.md` view |
| `HabitDraft` → `SkillPatch` / `SkillDraft` | procedural playbook | `evolved-skills/<slug>/SKILL.md` |
| `Proposal` | agent-authored patterns + habits | transient |
| `PacketHint` | `pattern` or `habit` cluster hint | transient |

No Bond, Schema, Script, Prior, Cue, PromotionCandidate, or lattice-owned LLM extractors.

## Package map

```text
src/lattice/
  contracts/     episodic, atom, patch, cursor ports
  domain/        Proposal, Op, Packet, ValidationResult, ApplyResult
  compile.py     patterns/habits → internal ops
  cluster.py     gate, rank, cluster, packet hints (pattern + habit)
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
