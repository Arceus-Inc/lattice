# Procedural Memory & Skill Evolution: Research Report

*Generated: July 11, 2026 | Sources: 28 | Confidence: High*

## Executive Summary

Procedural memory in agent systems has converged on a small set of patterns: **skills as portable `SKILL.md` files**, **progressive disclosure at load time**, and **evolution loops that distill successful trajectories into reusable playbooks**. Hermes, Letta, SkillOS, and the agentskills.io standard all treat procedural knowledge as narrow, actionable markdown — distinct from declarative memory (facts, preferences, episodic traces).

The evolution mechanisms split into three families: **(1) agent-authored runtime tools** (Hermes `skill_manage`, Letta `/skill`), **(2) offline optimizers** (Hermes Self-Evolution with DSPy+GEPA, SkillOS auto-improve), and **(3) learned meta-operators** (MemSkill controller/designer, Memp lifecycle). Academic work (Voyager, Reflexion, ExpeL, Memp) established that procedural memory must support **add / modify / delete / retrieve** — not just append — and that **success-gated distillation** (outcome=done, verifier feedback) dramatically improves quality.

The dominant production gap is **routing policy**: knowing when to write a fact vs. a procedure vs. a session note. Hermes issue #3506 frames this explicitly. Lattice's `HabitDraft` + `OverlaySkillStore` aligns well with the emerging standard but should add agentskills.io frontmatter, section-level patching, and explicit routing from semantic patterns.

---

## 1. The Converging Skill Format (agentskills.io)

The [Agent Skills open standard](https://agentskills.io/specification) (Anthropic-origin, Dec 2025) defines procedural memory as:

```
skill-name/
├── SKILL.md          # YAML frontmatter + markdown body (required)
├── scripts/          # Optional executables
├── references/       # Optional deep docs
└── assets/           # Optional templates
```

**Progressive disclosure** is the load model ([agentskills.io](https://agentskills.io/home)):
1. **Discovery** — `name` + `description` only (~30–100 tokens/skill)
2. **Activation** — full `SKILL.md` body when task matches
3. **Execution** — bundled scripts/assets on demand

Hermes, Cursor, Letta Code, and Codex CLI all follow this layout. Hermes stores user-evolved skills at `~/.hermes/skills/<slug>/SKILL.md` with `references/`, `templates/`, `scripts/`, `assets/` subdirs ([`skill_manager_tool.py`](https://github.com/NousResearch/hermes-agent/blob/main/tools/skill_manager_tool.py)).

**Implication for Lattice:** `OverlaySkillStore` writes bare markdown without YAML frontmatter. Adding `name`/`description` frontmatter would make evolved skills portable to Chorus harness and any agentskills.io runtime.

---

## 2. Hermes: Runtime Authoring + Offline GEPA Evolution

### 2a. Runtime: `skill_manage` tool

Hermes exposes procedural memory as a first-class tool ([`skill_manager_tool.py`](https://github.com/NousResearch/hermes-agent/blob/main/tools/skill_manager_tool.py)):

| Action | Purpose |
|--------|---------|
| `create` | New skill directory + `SKILL.md` |
| `edit` | Full rewrite of `SKILL.md` |
| `patch` | Targeted find-and-replace in skill files |
| `delete` | Remove user skill |
| `write_file` / `remove_file` | Manage supporting assets |

Key design choices:
- **Declarative vs procedural split:** "General memory (MEMORY.md, USER.md) is broad and declarative. Skills are narrow and actionable."
- **Security opt-in:** `skills.guard_agent_created` scans agent-created skills (off by default — agent can run same code via `terminal()`)
- **Collision with bundled skills:** edits apply wherever skills live; creates only in `~/.hermes/skills/`

### 2b. Background review routing

Hermes runs background self-improvement reviews ([issue #30227](https://github.com/NousResearch/hermes-agent/issues/30227)) with explicit store priority:

1. **SKILL** → reusable workflows
2. **USER.md** → user-specific preferences
3. **MEMORY.md** → stable facts

Rule: **one fact, one store** — never duplicate across stores.

### 2c. Routing gap (issue #3506)

[Issue #3506](https://github.com/NousResearch/hermes-agent/issues/3506) states the gap is **not storage** but **routing policy**:

- `memory` → stable facts/preferences
- `skill_manage` → reusable procedures
- `session_search` → cross-session recall
- Issue/plan follow-up → recurring product failures (not memory spam)

Proposed fix: tighten prompt assembly + focused routing tests — no new persistence subsystem.

### 2d. Offline evolution: hermes-agent-self-evolution

[NousResearch/hermes-agent-self-evolution](https://github.com/NousResearch/hermes-agent-self-evolution) optimizes skills via **DSPy + GEPA** (Genetic-Pareto Prompt Evolution):

```
Read skill → Generate eval dataset → GEPA mutates → Evaluate traces → Constraint gates → PR
```

- **Phase 1 (implemented):** evolve `SKILL.md` files
- **Phases 2–5 (planned):** tool descriptions, system prompts, tool code, continuous loop
- **Guardrails:** full pytest pass, size limits (≤15KB), semantic preservation, human PR review
- **Eval sources:** synthetic datasets or real session history (`sessiondb`)
- **Cost:** ~$2–10 per optimization run, no GPU

**Key insight:** Hermes separates **runtime authoring** (agent decides what to save mid-session) from **offline refinement** (GEPA improves wording/structure from traces). Lattice currently only has the runtime path via `lattice_propose` → `lattice_apply`.

### 2e. Tiered memory architecture (issue #32726)

Hermes roadmap proposes 4 layers ([issue #32726](https://github.com/NousResearch/hermes-agent/issues/32726)):

| Layer | Store | Content |
|-------|-------|---------|
| Index | `~/.hermes/index.json` | Project pointers |
| Logic | Skills (`skill_manage`) | Workflows, configs |
| Rules | MEMORY.md | Behavior rules + index pointer |
| Fallback | `session_search` | Full session history |

Procedural memory sits in the **Logic layer** — not mixed with facts.

---

## 3. Letta: Sleep-Time Compute + Skill Learning

### 3a. Architecture

[Letta Code](https://github.com/letta-ai/letta-code) treats memory as a **git-backed MemFS** context repository ([docs](https://docs.letta.com/letta-code/memory/)). Skills live at multiple scopes:

- Global: `~/.letta`
- Project: `.agents/skills`
- Agent-scoped: `$MEMORY_DIR/skills` (versioned with agent memory)

### 3b. Sleep-time agents

[Sleep-time compute](https://www.letta.com/blog/sleep-time-compute/) offloads memory management to background subagents:

- Primary agent: conversation + tools, **cannot** edit core memory
- Sleep-time agent: async memory consolidation, triggered every N steps (default 5)
- Solves MemGPT's problem of messy incremental memory by continuous cleanup

Triggers in Letta Code: `/sleeptime` — off, step count, or compaction event.

### 3c. Skill Learning (two-stage)

[Skill Learning blog](https://www.letta.com/blog/skill-learning) (Terminal Bench 2.0 eval):

1. **Reflection** — evaluate trajectory: success?, reasoning sound?, abstractable patterns?
2. **Creation** — learning agent uses skill-creator to generate `.md` skill with approaches, pitfalls, verification strategies

Results:
- Trajectory-only skills: **+21.1% relative** performance, **-15.7% cost**, **-10.4% tool calls**
- With verifier feedback: **+36.8% relative** (15.7% absolute)

**Hierarchy:**
- **Core memory / system prompt** — agent-specific, cross-task
- **Skills / filesystem** — task-specific, shareable across agents

User invokes via `/skill` command after a session.

**Key insight for Lattice:** Letta's biggest gain came from **verifier feedback** in reflection, not just successful trajectories. Lattice's `outcome=done` gate is the right primitive; adding structured verifier logs (test output, CI failure) would strengthen habit quality.

---

## 4. SkillOS: Markdown-as-OS + Human-in-the-Loop Auto-Improve

[SkillOS](https://github.com/EvolvingAgentsLabs/skillos) is a PoC where **everything is markdown** — agents, tools, memory, orchestration. No compilation.

### Skill hierarchy
```
Domain → Family → Skill
orchestration/core/system-agent
memory/consolidation/memory-consolidation-agent
auto-improve/meta-agent/auto-improve-meta-agent
```

**4-step lazy loading** reduces routing tokens ~61% vs flat registry.

### Evolution: auto-improve loop
- `usage-tracker` tool records skill usage
- `auto-improve-meta-agent` detects stale skills, analyzes failure traces
- Proposes targeted spec improvements
- **Human-in-the-loop** approval before merge

### Dialects for efficient patching
`strict-patch` dialect: `[DEL:42]`/`[ADD:42]` instead of full file rewrites — 97.5% token reduction on code-editing benchmarks.

**Key insight:** SkillOS separates **frozen executor** (runtime interprets markdown) from **trainable curator** (auto-improve proposes changes). This mirrors MemSkill's controller/designer split. Lattice's gate-validated `lattice_apply` is the human-in-the-loop curator equivalent.

---

## 5. MemSkill: Learned Meta-Memory Operators (Not Content)

[MemSkill](https://github.com/ViktorAxelsen/MemSkill) (arXiv:2602.02474) is critical to understand because it evolves **how to remember**, not **what was remembered**:

> "Skills evolved by MemSkill are NOT experiential/procedural memory/insights themselves. Rather, they are meta-memory — what kinds of memory to extract, how to remember, where to focus, what to preserve or forget."

### Architecture: Controller → Executor → Designer

| Component | Role |
|-----------|------|
| **Controller** | RL-trained (PPO); selects Top-K memory skills per span |
| **Executor** | Applies selected skills to construct memory from interaction |
| **Designer** | Mines hard cases; refines existing skills; proposes new ones |

### Training loop (ALFWorld example)
- **Batch A:** offline expert trajectories → teach controller skill composition
- **Batch B:** environment rollouts → task success as reward signal
- Designer evolves skill bank from Batch B failures

### Transfer
Skills trained on LoCoMo transfer to LongMemEval-S without retraining.

**Distinction from Lattice habits:** MemSkill skills are **memory-operation templates** (extract, consolidate, forget). Lattice `HabitDraft` skills are **task playbooks** (how to run probes, how to wire Chorus). Different layer — but the designer's hard-case mining is analogous to Lattice adjudication promoting patterns from `outcome=done` episodes.

---

## 6. Memp: Procedural Memory Lifecycle (Build / Retrieve / Update)

[Memp](https://arxiv.org/abs/2508.06433) (ACL 2026 Findings) formalizes procedural memory as a **repository with lifecycle operations**:

### Build
Distill completed trajectories into:
- Fine-grained step-by-step instructions
- Higher-level script-like abstractions

### Retrieve
Query-based or keyword-vector matching to find relevant procedures.

### Update
```
U = Add(M_new) ⊖ Del(M_obsolete) ⊕ Update(M_existing)
```

Strategies studied:
- **Validation filtering** — retain only successful task memories
- **Adjustment** — revise erroneous trajectories in place
- **Deprecation** — remove obsolete procedures

Evaluated on TravelPlanner + ALFWorld. Key finding: procedural memory from stronger models **transfers to weaker models**.

**Key insight for Lattice:** Memp's update formula maps directly to habit operations:
- `Add` → `HabitAction.CREATE`
- `Update` → `HabitAction.EVOLVE` (section patch)
- `Del` → **not yet in Lattice** (habit deprecation/delete is a gap)

---

## 7. Voyager: Executable Code Skills

[Voyager](https://github.com/MineDojo/Voyager) (NeurIPS 2023) stores skills as **executable JavaScript** in a vector DB skill library:

1. **Automatic curriculum** — maximizes exploration
2. **Skill library** — code stored + retrieved by embedding similarity
3. **Iterative prompting** — environment feedback + execution errors + self-verification improve programs

Skills are compositional and temporally extended — rapid ability compounding, no catastrophic forgetting.

**Contrast:** Voyager skills are **code**, not markdown playbooks. Better for embodied/tool-heavy domains; less portable across harnesses. The iterative refinement loop (try → error → fix → verify) is the precursor to Reflexion and modern skill learning.

---

## 8. Reflexion & ExpeL: Verbal RL → Insight Extraction

### Reflexion ([arXiv:2303.11366](https://arxiv.org/abs/2303.11366))
Agent generates **verbal self-reflection** after failure, stores in persisting memory, retries with reflection in context. No weight updates. Works on HotPotQA, AlfWorld, programming.

### ExpeL ([arXiv:2308.10144](https://arxiv.org/html/2308.10144v2))
Three-stage experiential learning:

1. **Collection** — trial-and-error trajectories into experience pool (via Reflexion)
2. **Extraction** — cross-task insights via ADD/UPVOTE/DOWNVOTE/EDIT operations on insight list
3. **Application** — recall insights + similar successful trajectories at inference

Insights are **natural language rules**, not full skill files. ExpeL's insight pool is closer to Lattice **semantic patterns** (MEMORY.md atoms) than **habits** (SKILL.md overlays).

**Mapping:**
| System | Lattice equivalent |
|--------|-------------------|
| ExpeL insights | `PatternDraft` → MEMORY.md atoms |
| Hermes/Letta skills | `HabitDraft` → evolved-skills/ |
| Reflexion verbal memory | Episodic engrams (raw traces) |

---

## 9. Architecture Comparison Matrix

| System | Storage | Evolution trigger | Success gate | Update ops | Human gate |
|--------|---------|-------------------|--------------|------------|------------|
| **Hermes** | `~/.hermes/skills/SKILL.md` | Agent `skill_manage` + background review | Implicit (agent judgment) | create/edit/patch/delete | Optional guard scan |
| **Hermes GEPA** | Same | Offline trace eval | Test suite pass | GEPA mutation | PR review |
| **Letta** | MemFS `$MEMORY_DIR/skills/` | `/skill` + sleep-time | Reflection + verifier | skill-creator | User invokes |
| **SkillOS** | Markdown skill tree | auto-improve meta-agent | Usage + failure traces | strict-patch dialect | Human approval |
| **MemSkill** | Skill bank (meta-ops) | Designer on hard cases | Task reward (PPO) | refine + propose new | RL training |
| **Memp** | Procedural repository | Post-task feedback | Validation filter | add/modify/delete | Automated |
| **Voyager** | Vector DB of JS code | Iterative prompting | Self-verification | add + refine code | Automated |
| **ExpeL** | Insight list + traj pool | Insight extraction stage | Success/failure pairs | ADD/EDIT/UPVOTE/DOWNVOTE | Automated |
| **Lattice** | `evolved-skills/<slug>/SKILL.md` | `lattice_propose` habits | `outcome=done` required | create/evolve | `validate` + `apply` gate |

---

## 10. Common Evolution Patterns (Synthesis)

### Pattern A: Success-gated distillation
Every effective system filters on task success before promoting to procedural memory:
- Lattice: `outcome=done` on cited `source_run_id`
- Memp: validation filtering
- Letta: reflection assesses "did agent solve the task?"
- ExpeL: separates success/failure pairs for insight extraction

### Pattern B: Separate declarative from procedural
Universal rule (Hermes, Letta, tiered memory roadmap):
- **Facts/preferences** → declarative memory (MEMORY.md, user blocks)
- **How-to workflows** → skills (SKILL.md)
- **Raw traces** → episodic/session search

Lattice `directive.py` already encodes this: "For 'how should I act?' use evolved skills, not lattice_context."

### Pattern C: Progressive disclosure at runtime
Load skill metadata always; full body on activation. Keeps 50–100 skills viable (~3–5K tokens overhead).

### Pattern D: Section-level patching > full rewrites
- Hermes: `patch` action (find-and-replace)
- SkillOS: `strict-patch` dialect
- Lattice `EVOLVE`: `skill` + `section` + `new_content` — aligned

### Pattern E: Offline optimizer on top of runtime authoring
Hermes GEPA and SkillOS auto-improve both assume runtime-created skills are **drafts** refined by a second pass. Lattice has no offline refinement loop yet.

### Pattern F: Lifecycle includes deletion
Memp explicitly models `Del(M_obsolete)`. Most skill systems under-invest in deprecation. Lattice habits lack delete/deprecate — only create/evolve.

### Pattern G: Routing is the hard problem
Multiple Hermes issues (#3506, #30227, #24770) confirm: storage primitives exist; **classification policy** is the bottleneck. Lattice's typed `Proposal` (patterns vs habits) is an architectural advantage over prompt-only routing.

---

## 11. Recommendations for Lattice `feat/patterns-habits`

### Already aligned
1. **Typed routing** — `PatternDraft` (semantic) vs `HabitDraft` (procedural) in one `Proposal` avoids Hermes-style memory spam
2. **Success gate** — `outcome=done` matches Memp/Letta validation filtering
3. **Overlay model** — `evolved-skills/` separate from canonical role skills; collision check on `canonical_slugs`
4. **Section evolve** — `HabitAction.EVOLVE` with `skill` + `section` matches Hermes `patch` semantics
5. **Source citation** — `source_run_ids` provides provenance (ExpeL/Memp trajectory linking)

### Gaps to close (priority order)

**H1 — agentskills.io frontmatter on write**
`OverlaySkillStore.apply_draft` should emit:
```yaml
---
name: probe-retrieval-checks
description: Run lattice retrieval domain checks after materialize beat
---
```
Enables Chorus harness progressive disclosure without custom parsing.

**H2 — Chorus materialization wiring**
Per conversation state: `_lattice_bridge.py` needs `enable_patches=True` and copy `evolved-skills/` → worktree `.harness/skills/` on materialize. Without this, habits are stored but never loaded.

**H3 — Habit delete/deprecate**
Add `HabitAction.DEPRECATE` or `delete` op per Memp lifecycle. Pair with adjudication `forget` for semantic patterns.

**H4 — Verifier-enriched proposals**
Letta's +6.7% gain from feedback suggests extending `HabitDraft` metadata with `verifier_summary` or linking to episodic `test_output` fields when present.

**H5 — Sleep-time / background evolution (later)**
Letta sleep-time and Hermes background review suggest a **non-blocking second pass** after `lattice_apply`:
- Review new habits for redundancy
- Merge overlapping sections
- Route misfired patterns (procedural content in MEMORY.md) to habit proposals

This could run as Chorus "adjudication beat" extension without blocking the agent loop.

**H6 — Offline GEPA pass (optional)**
For high-traffic evolved skills, run hermes-agent-self-evolution-style optimization on accumulated traces. Not required for v1 but matches production Hermes architecture.

---

## Key Takeaways

1. **Procedural memory = SKILL.md playbooks**, not facts. The industry has standardized on agentskills.io format with progressive disclosure. Lattice should emit compliant frontmatter.

2. **Evolution = distillation loop**, not weight updates. Every major system converts trajectories → structured artifacts via success gates, reflection, or RL. Lattice's `outcome=done` + `lattice_propose`/`apply` is the right minimal loop.

3. **Routing beats storage.** Hermes's biggest open issue is classifying feedback into memory vs skill vs session. Lattice's typed `Proposal` fields are architecturally ahead — protect this distinction in prompts and validation.

4. **Lifecycle needs delete.** Memp and SkillOS auto-improve both model deprecation. Lattice habits are create/evolve only — add delete before skill library rots.

5. **Runtime + offline is the production pattern.** Hermes agent creates skills live; GEPA refines offline. Lattice has runtime; consider background review or GEPA for high-value skills later.

6. **MemSkill is a different layer.** MemSkill evolves memory-*operations* (meta-memory), not task playbooks. Don't conflate with `HabitDraft` — but borrow the designer's hard-case mining for adjudication.

---

## Sources

1. [Agent Skills Specification](https://agentskills.io/specification) — open SKILL.md format
2. [Agent Skills Overview](https://agentskills.io/home) — progressive disclosure model
3. [Hermes skill_manager_tool.py](https://github.com/NousResearch/hermes-agent/blob/main/tools/skill_manager_tool.py) — runtime skill CRUD
4. [Hermes issue #3506](https://github.com/NousResearch/hermes-agent/issues/3506) — routing policy gap
5. [Hermes issue #30227](https://github.com/NousResearch/hermes-agent/issues/30227) — background review store routing
6. [Hermes issue #32726](https://github.com/NousResearch/hermes-agent/issues/32726) — tiered memory architecture
7. [hermes-agent-self-evolution README](https://github.com/NousResearch/hermes-agent-self-evolution) — DSPy+GEPA offline evolution
8. [Letta Code](https://github.com/letta-ai/letta-code) — MemFS + skill learning harness
9. [Letta Skill Learning blog](https://www.letta.com/blog/skill-learning) — reflection + creation, Terminal Bench results
10. [Letta Sleep-time Compute](https://www.letta.com/blog/sleep-time-compute/) — async memory consolidation
11. [Letta Memory docs](https://docs.letta.com/letta-code/memory/) — MemFS, dreaming, skill storage
12. [SkillOS README](https://github.com/EvolvingAgentsLabs/skillos) — markdown-as-OS, auto-improve, lazy loading
13. [MemSkill README](https://github.com/ViktorAxelsen/MemSkill) — controller/executor/designer, meta-memory skills
14. [MemSkill paper](https://arxiv.org/abs/2602.02474) — arXiv:2602.02474
15. [Memp paper](https://arxiv.org/abs/2508.06433) — Build/Retrieve/Update lifecycle
16. [Memp ACL 2026](https://aclanthology.org/2026.findings-acl.866/) — empirical results
17. [Voyager README](https://github.com/MineDojo/Voyager) — code skill library + iterative prompting
18. [Reflexion README](https://github.com/noahshinn/reflexion) — verbal RL, persisting reflections
19. [ExpeL paper](https://arxiv.org/html/2308.10144v2) — experience pool + insight extraction
20. [ExpeL repo](https://github.com/LeapLabTHU/ExpeL) — insight_extraction.py implementation
21. [Firecrawl Agent Skills blog](https://www.firecrawl.dev/blog/agent-skills) — ecosystem adoption, token costs
22. [Lattice OverlaySkillStore](src/lattice/stores/overlay_skills.py) — current procedural store
23. [Lattice validate.py habits](src/lattice/validate.py) — outcome=done gate, create/evolve validation

## Methodology

Searched 12 query variations across GitHub repos, arXiv, ACL Anthology, and official docs. Deep-read 8 primary sources (README files, skill tool source, Letta/Hermes blogs, Memp/ExpeL papers). Cross-referenced against Lattice `feat/patterns-habits` implementation.

Sub-questions investigated:
1. What is the standard format for procedural memory (skills) in 2026?
2. How does Hermes evolve skills at runtime and offline?
3. What evolution loops do Letta, SkillOS, and MemSkill use?
4. What lifecycle operations (add/modify/delete) does research recommend?
5. How does Lattice's HabitDraft design compare, and what's missing?

*Note: firecrawl/exa MCP tools were unavailable; research used WebSearch + WebFetch against primary sources.*
