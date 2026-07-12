# Lattice Integration: Deep Research + Branch Mergeability

*Generated: 2026-07-12 | Sources: local git/PRs/tests + Hermes/Paperclip docs + academic memory literature | Confidence: High (repo facts); Medium (external landscape)*

## Executive Summary

**Lattice integration** is a bicameral memory seam: Chorus owns episodic traces + procedural skill versioning; Lattice owns semantic pattern algebra (gate → packet → validate → apply → retrieve). The correct split today is **patterns via `lattice_apply`**, **procedures via Chorus `skill_manage`** (Hermes-shaped), with Lattice retaining **habit draft validation** only.

**Mergeability verdict (lattice):** both feature branches are **git-mergeable without conflicts**. `feat/patterns-habits` is a **strict superset** of `feat/patterns-only` and is the branch that should land on `main`. Open PR [#3](https://github.com/Arceus-Inc/lattice/pull/3) is `MERGEABLE` / `CLEAN` into `feat/patterns-only`. Direct dry-run merges of either branch into `main` also succeed. Lattice unit/integration tests on `feat/patterns-habits`: **86 passed**.

**Chorus companion:** `feat/lattice-integration` merges **cleanly into `main`**, but GitHub PR [#64](https://github.com/Arceus-Inc/chorus/pull/64) is **CONFLICTING** against its outdated base `feat/episodic-storage-engine` (conflict in `src/chorus_harness/_factory.py`). Retarget the PR to `main` (or rebase) before merge.

---

## 1. What “lattice integration” means

### 1.1 Ownership model (current intended architecture)

| Concern | Owner | Mechanism |
| --- | --- | --- |
| Episodic “what happened” | Chorus | `EpisodicStore` / `recall` / `get_run` |
| Semantic facts | Lattice | `Proposal.patterns[]` → atoms / `MEMORY.md` / `lattice_context` |
| Procedural how-to | **Chorus** | `SkillStore` + `skill_manage` + rematerialize into `.harness/skills` |
| Habit *gates* (diary reject, EVOLVE-first, body floors) | Lattice | `validate.py` / `HabitDraft` used by SkillManager |
| Recurrence gate | Lattice | `gate_open(N, K)` → beat-end teaser |

This matches Hermes’ sticky-note vs reference-manual rule ([Working with Skills](https://hermes-agent.nousresearch.com/docs/guides/work-with-skills)): facts → memory/patterns; procedures → skills. It also matches the Jul 11 correction in `docs/skill-manager-harness-plan.md`: **do not dual-write** `lattice_apply(habits)` + `skill_manage`; do **not** put skill version rows in Lattice SQLite.

### 1.2 Cross-repo seam (from `docs/integration-plan.md`)

Non-negotiable rules still hold:

- `src/lattice/` never imports `chorus`
- One adapter / composition root in Chorus factory
- Shared episodic path under `company_root/memory`
- Consolidation is **offline / gate-gated**, not every beat (CLS-style separation)

Live e2e evidence (Chorus `feat/lattice-integration`):

- 5-beat pattern probe: pass
- Habit/skill live e2e: pass (programmatic evolve + load)
- Agent-driven skill evolve e2e: pass (`skill_manage` → `skills.db` r1→r2 → rematerialize → retrieve)

---

## 2. Lattice branch topology

```text
main (fcacd2a)
  │
  ├─ feat/patterns-only (09ba339)  … +7 commits vs main
  │     │
  │     └─ feat/patterns-habits (090416f)  … +2 commits vs patterns-only
  │           (= +9 vs main; includes ALL of patterns-only)
```

| Branch | Tip | vs `main` | vs other feature |
| --- | --- | --- | --- |
| `feat/patterns-only` | `09ba339` | 0 behind / **7 ahead** | ancestor of habits |
| `feat/patterns-habits` | `090416f` | 0 behind / **9 ahead** | **superset** of patterns-only |

Extra commits on habits only:

1. `f96645e` — Revert patterns-only strip of habits
2. `090416f` — Hermes gates, EVOLVE-first validation, skill-manager plan docs

### 2.1 What each branch adds (theme)

**Shared with both (patterns-only → main):**

- Adjudication / sleep-beat tiers, LCB in MEMORY.md
- Retrieve: domain gate, trust-weighted scoring, BM25
- Integration suite, path safety, chorus bridge helper
- Integration plan + v1/consolidation docs
- Patterns provenance / claim depth

**Habits-only delta (vs patterns-only):**

- Restore habit domain types + `OverlaySkillStore` (validation/tests; Chorus owns writes)
- Hermes-aligned `validate.py` (diary reject, EVOLVE body floors, CREATE rarity)
- Directive/skill docs pointing at `skill_manage`
- Research/plan docs: procedural memory, Hermes granularity, skill-manager harness, chorus skill evolution
- ~+4.7k / −158 lines vs patterns-only tip

---

## 3. Mergeability matrix (verified)

### 3.1 Dry-run merges (local, `--no-commit --no-ff`)

| Merge | Result |
| --- | --- |
| `origin/feat/patterns-habits` → `main` | **CLEAN** (automatic merge) |
| `origin/feat/patterns-only` → `main` | **CLEAN** |
| `origin/feat/patterns-habits` → `feat/patterns-only` | **CLEAN** |

Ancestry checks:

- `main` is ancestor of `feat/patterns-habits` → **YES** (fast-forward possible if desired)
- `feat/patterns-only` is ancestor of `feat/patterns-habits` → **YES**

### 3.2 GitHub PRs

| PR | Repo | Head → Base | `mergeable` | Notes |
| --- | --- | --- | --- | --- |
| [#3](https://github.com/Arceus-Inc/lattice/pull/3) | lattice | `feat/patterns-habits` → `feat/patterns-only` | **MERGEABLE** / **CLEAN** | Open; no status checks reported |
| [#1](https://github.com/Arceus-Inc/lattice/pull/1) | lattice | `feat/patterns-only` → `main` | UNKNOWN | Open; older title (“integration suite…”) understates full branch |
| [#64](https://github.com/Arceus-Inc/chorus/pull/64) | chorus | `feat/lattice-integration` → `feat/episodic-storage-engine` | **CONFLICTING** / **DIRTY** | Conflict: `src/chorus_harness/_factory.py` |

Chorus dry-run vs **`main`**: **CLEAN** (so the conflict is base-branch drift, not unmergeable work).

### 3.3 Test gate

On `feat/patterns-habits`: `uv run pytest -q` → **86 passed** (0.75s).

No GitHub Actions runs were listed for these lattice branches at query time — treat local pytest as the current quality signal.

### 3.4 Recommended merge path

**Preferred (simplest):**

1. Open/retarget a PR: `feat/patterns-habits` → `main` (or merge #3 then fast-forward #1 — redundant).
2. Merge habits to `main` (includes all patterns-only work).
3. Close #1 as superseded (or merge #1 first only if you want a patterns-only intermediate tag).
4. On Chorus: retarget PR #64 to `main` (or rebase onto `main`) to clear the factory conflict vs `feat/episodic-storage-engine`.

**Do not** merge patterns-only *after* habits without resetting — habits already contains it.

**Doc hygiene before merge:** `docs/chorus-skill-evolution-plan.md` still describes older Slice A–D (`habits[]` on `lattice_apply`, overlay materialize). Current code + `skill-manager-harness-plan.md` supersede that. Either update the evolution plan or mark it historical so reviewers are not confused.

---

## 4. External research landscape (procedural / pattern memory)

### 4.1 Hermes (direct design ancestor)

Sources: [Skills System](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills), [Working with Skills](https://hermes-agent.nousresearch.com/docs/guides/work-with-skills), [`skill_manager_tool.py`](https://github.com/NousResearch/hermes-agent/blob/72ff3e90/tools/skill_manager_tool.py), [#12812](https://github.com/NousResearch/hermes-agent/issues/12812).

| Hermes concept | Lattice×Chorus mapping |
| --- | --- |
| Skills = procedural memory | Chorus `SkillStore` / rematerialized `SKILL.md` |
| Sticky-note facts ≠ skills | Lattice `patterns[]` + diary reject in `validate.py` |
| `skill_manage` create/patch/edit | Chorus `skill_manage` (patch/evolve preferred) |
| Progressive disclosure (`skills_list` / `skill_view`) | Dream `skill` tool + harness materialize |
| Write-time prevention + curator archival (#12812 fix) | EVOLVE-first + CREATE rarity + body floors |

**Implication:** Lattice should keep validating *quality* of procedural drafts; Chorus should own *persistence* and versioning. That is already the Jul 11 corrected plan.

### 4.2 Paperclip (versioning ancestor)

Sources: [Skills guide](https://paperclip.inc/docs/paperclip/guides/org/skills/), [Skills reference](https://paperclip.inc/docs/paperclip/reference/skills/).

| Paperclip concept | Chorus mapping |
| --- | --- |
| Company skill library | `{company_root}/skills/skills.db` |
| Append-only / pinned versions | `skill` + `skill_revision` + optional pins |
| Materialize into adapter workspace | `materialize_versioned_skills_into` → `.harness/skills` |
| GitHub pin vs live local | Canonical role pack (immutable) vs evolved HEAD |

Paperclip’s GitHub SHA pins differ from Chorus’s revision rows, but the **DB-as-SoT + filesystem materialization** pattern is the same.

### 4.3 Academic / industry (2025–2026)

| Work | Relevance to lattice integration |
| --- | --- |
| [MemSkill](https://arxiv.org/abs/2602.02474) (2026) | Memory *operations* as evolvable skills; closed-loop designer — analogous to evolving how consolidation works, not only what is stored |
| [ReMe](https://arxiv.org/html/2512.10696v2) | Distill trajectories → reusable experiences + utility pruning — supports gate-gated promotion + forget/adjudicate |
| [AutoRefine](https://arxiv.org/pdf/2601.22758v1) | Subagent patterns + skill patterns + maintenance — dual pattern/skill split mirrors Lattice patterns vs Chorus skills |
| Voyager / Generative Agents (via [memory architecture survey](https://medium.com/ai-simplified-in-plain-english/the-architecture-of-memory-how-ai-agents-remember-forget-and-learn-4cd040420927)) | Procedural skill library is a multiplier; reflection without skills collapses |

**Takeaway:** Industry and research converge on (1) separate declarative vs procedural stores, (2) evolve procedures from experience, (3) prune sticky notes. Lattice×Chorus is aligned; the remaining risk is **doc drift** and **PR base-branch hygiene**, not architectural novelty.

---

## 5. Integration readiness checklist

| Item | Status |
| --- | --- |
| Lattice patterns path (gate/packet/apply/context) | Implemented on both feature branches |
| Hermes habit validation gates | On `feat/patterns-habits` |
| Chorus `skill_manage` + SkillStore | On `feat/lattice-integration` (live e2e pass) |
| Patterns-only apply rejects `habits[]` | Shipped in Chorus tools path |
| Lattice PR mergeable to patterns-only | **Yes** (#3 CLEAN) |
| Lattice habits → main dry-run | **Yes** |
| Chorus PR mergeable to declared base | **No** (#64 CONFLICTING) |
| Chorus → main dry-run | **Yes** |
| Docs fully consistent with ownership split | **Partial** (evolution plan stale) |
| CI checks on lattice PRs | **Absent / empty** in GitHub rollup |

---

## 6. Key takeaways

1. **Both lattice branches are mergeable**; habits is the complete branch — merge it to `main` and treat patterns-only as intermediate history.
2. **Chorus integration is functionally ready** but **PR #64 must be retargeted/rebased onto `main`** to clear the factory conflict with `feat/episodic-storage-engine`.
3. **Architecture matches Hermes + Paperclip + current research**: patterns ≠ skills; evolve umbrellas; version in Chorus DB.
4. **Before shipping:** refresh stale evolution-plan docs; ensure dependency pin (Chorus → Lattice commit on habits tip); add CI to lattice PRs if required by org policy.
5. **Proven live:** agent-driven `skill_manage(evolve)` wrote revisioned skill bodies and rematerialized them for retrieve beats.

---

## Sources

### Local / product

1. Lattice branches `main`, `feat/patterns-only`, `feat/patterns-habits` — ancestry + dry-run merges (2026-07-12)
2. [lattice#3](https://github.com/Arceus-Inc/lattice/pull/3), [lattice#1](https://github.com/Arceus-Inc/lattice/pull/1), [chorus#64](https://github.com/Arceus-Inc/chorus/pull/64)
3. `docs/integration-plan.md`, `docs/skill-manager-harness-plan.md`, `docs/chorus-skill-evolution-plan.md`
4. Chorus reports: `backend-engineer-skill-evolve-e2e.json`, `skill-evolve-proof/`

### External

5. [Hermes — Working with Skills](https://hermes-agent.nousresearch.com/docs/guides/work-with-skills)
6. [Hermes — Skills System / skill_manage](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills)
7. [Hermes #12812](https://github.com/NousResearch/hermes-agent/issues/12812) — sticky-note skills
8. [Paperclip Skills guide](https://paperclip.inc/docs/paperclip/guides/org/skills/)
9. [Paperclip Skills reference (versioning)](https://paperclip.inc/docs/paperclip/reference/skills/)
10. [MemSkill (arXiv:2602.02474)](https://arxiv.org/abs/2602.02474)
11. [ReMe (arXiv HTML 2512.10696)](https://arxiv.org/html/2512.10696v2)
12. [AutoRefine (arXiv:2601.22758)](https://arxiv.org/pdf/2601.22758v1)

## Methodology

- Sub-questions: (1) ownership of lattice integration, (2) branch topology, (3) git/GitHub mergeability, (4) Hermes/Paperclip alignment, (5) external procedural-memory state of art.
- Local: fetch, ancestry, three dry-run merges, PR JSON, pytest.
- Web: Hermes docs + #12812, Paperclip skills reference, MemSkill/ReMe/AutoRefine.
- Note: firecrawl/exa MCP tools were **not available** in this environment; used WebSearch/WebFetch instead.
