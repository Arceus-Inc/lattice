# Hermes Skill Granularity: When Short Things Must NOT Be Skills

*Generated: July 11, 2026 | Sources: 18 | Confidence: High*

## Executive Summary

Hermes explicitly rejects **short, sticky-note, and diary-entry content as skills**. Skills are **class-level reference manuals** loaded on demand; memory is **compact facts** injected every session. The agent should **patch existing umbrella skills** before creating new ones, and only create skills after **non-trivial multi-step work** (typically 5+ tool calls). One-off narratives, transient errors, and environment-specific observations belong in **memory** or **`references/`** files under an existing skill — not new micro-skills.

**Implication for Lattice/Chorus:** The `retry-discipline` CREATE example in our integration plan is **anti-pattern**. `"The HTTP client retries 429/503"` is a **pattern** (`lattice_context`). `"Recall failure shape before patching"` is either a **section patch** into an existing role skill (EVOLVE) or stays out of procedural memory entirely — not a 2-line standalone skill.

---

## 1. The Sticky Note vs Reference Manual Rule

Official Hermes guidance ([Working with Skills](https://hermes-agent.nousresearch.com/docs/guides/work-with-skills)):

| | Skills | Memory |
|---|--------|--------|
| **What** | Procedural — how to do things | Factual — what things are |
| **When** | On demand, only when relevant | Every session automatically |
| **Size** | Can be large (hundreds of lines) | Compact (key facts only) |
| **Cost** | Zero tokens until loaded | Small but constant |
| **Examples** | "How to deploy to Kubernetes" | "User prefers dark mode" |

> **Rule of thumb:** If you'd put it in a **reference document**, it's a skill. If you'd put it on a **sticky note**, it's memory.

The [optimization guide](https://github.com/OnlyTerp/hermes-optimization-guide/blob/main/part5-creating-skills.md) repeats this and adds:

> **Anti-pattern:** Create a skill for a one-off task — just do it, skip the skill.

---

## 2. Minimum Bar: When Hermes Creates Skills

From [Skills System docs](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills):

Skills are created only when:

1. **Complex task completed** — typically **5+ tool calls** successfully
2. **Errors/dead ends** — agent found the working path after iteration
3. **User corrected approach** — workflow preference, not a one-time fact
4. **Non-trivial workflow discovered** — repeatable class of work

Skills are **not** created for:

- Simple Q&A
- One-time setup narratives
- Session diary entries ("we found 86 calls to Gemini on April 18")
- Facts that should live in memory

---

## 3. The Diary-Entry Bug (Issue #12812)

Real production failure documented in [hermes-agent#12812](https://github.com/NousResearch/hermes-agent/issues/12812):

**Bad skill created:** `openrouter-billing-investigate`

```markdown
## What we found
- There were 86 calls to Gemini-Flash for auxiliary tasks.
- Total estimated cost was 5 cents.
```

**Why broken** ([issue reporter](https://github.com/NousResearch/hermes-agent/issues/12812)):

1. **Diary entry, not a tool** — records what we found *today*, not how to investigate billing generally
2. **Misleads later** — agent treats one-time observations as hard-coded facts
3. **Static narrative** — real logic belongs in a script, not a skill that says "we looked at logs"

Hermes fixed this with two systems ([teknium1 comment](https://github.com/NousResearch/hermes-agent/issues/12812#issuecomment)):

1. **Write-time prevention** — PR [#23004](https://github.com/NousResearch/hermes-agent/pull/23004): `Do NOT capture` in background review prompts
2. **Post-hoc archival** — `hermes curator` auto-archives stale unused skills

---

## 4. Do NOT Capture List (Background Review)

From [`agent/background_review.py`](https://github.com/NousResearch/hermes-agent/blob/main/agent/background_review.py) (`_SKILL_REVIEW_PROMPT`, PR #23004):

**Never save as skills:**

| Category | Example | Why |
|----------|---------|-----|
| Environment-dependent failures | missing binary, `command not found` | User can fix; not durable |
| Negative tool claims | "browser tools do not work" | Hardens into months-long self-refusal |
| Transient session errors | failed once, retry worked | Lesson is retry pattern, not failure |
| **One-off task narratives** | "summarize today's market", "analyze this PR" | Not a **class of work** |

**Positive reframing:** If setup caused failure, capture the **FIX** (install command, env var) under an **existing setup/troubleshooting skill** — never "this tool doesn't work" as standalone.

`'Nothing to save.'` is a valid outcome when no durable technique emerged.

---

## 5. Preference Order: Patch Before Create

Hermes background review enforces a **4-step preference ladder** ([background_review.py](https://github.com/NousResearch/hermes-agent/blob/main/agent/background_review.py)):

```
1. UPDATE currently-loaded skill     → patch the skill in play
2. UPDATE existing umbrella skill    → patch class-level skill via skills_list
3. ADD support file under umbrella   → references/, templates/, scripts/
4. CREATE new class-level umbrella   → ONLY when no existing skill covers the class
```

**Target library shape:**

> CLASS-LEVEL skills, each with a rich SKILL.md and `references/` for session-specific detail. **Not** a long flat list of narrow one-session-one-skill entries.

**CREATE naming rules:**

- Name MUST be **class-level** (`deploy-k8s`, `github-pr-workflow`)
- Name MUST NOT be: PR number, error string, feature codename, `fix-X-today`, `debug-Y-audit`

If the proposed name only makes sense for today's task → **wrong** → fall back to patch or reference file.

---

## 6. Required Skill Structure (Not Optional for Real Skills)

Hermes peer skills ([hermes-agent-skill-authoring/SKILL.md](https://github.com/NousResearch/hermes-agent/blob/main/skills/software-development/hermes-agent-skill-authoring/SKILL.md)) require:

```
# Title
## Overview
## When to Use          ← trigger class + "Don't use for:"
## <Procedure sections> ← numbered steps with completion criteria
## Common Pitfalls
## Verification Checklist
```

**Minimum for a skill to "feel like a peer":** Overview + When to Use + actionable body + pitfalls.

**Description** must start with `"Use when ..."` — trigger **class**, not one task.

**Size guidance:**

| Tier | Chars | Notes |
|------|-------|-------|
| Operational workflow | 8k–15k | Peer norm |
| Complex high-risk | ≤15k–25k | |
| Hot-path wrapper | 1k–4k | Routing only; body in references |
| Hard limit (agent writes) | 100k | Enforced in `skill_manager_tool.py` |
| Warning threshold | >20k | Split to `references/` |

From [issue #30754](https://github.com/NousResearch/hermes-agent/issues/30754) progressive disclosure refactor:

> Hot-path `SKILL.md` = trigger contract, routing, safety boundaries, execution skeleton, critical pitfalls, verification. Long examples/incidents → lazy-loaded `references/`.

---

## 7. Three-Tier Loading (Why Micro-Skills Waste Tokens)

Hermes progressive disclosure ([docs](https://hermes-agent.nousresearch.com/docs/guides/work-with-skills)):

```
Level 0: skills_list()           → name + description only (~3k tokens all skills)
Level 1: skill_view(name)        → full SKILL.md (loads on activation)
Level 2: skill_view(name, path)  → references/ on demand
```

A micro-skill still pays **description tokens at session start** (~30–50 tokens/skill in agentskills.io; ~3k for full list). Creating many narrow skills:

- Pollutes the skill registry
- Increases false-positive activations
- Produces diary entries that mislead on load

**Preferred:** One umbrella skill + `references/session-specific.md` pointer.

---

## 8. Curator: Lifecycle Cleanup

[Curator docs](https://hermes-agent.nousresearch.com/docs/user-guide/features/curator):

- Tracks `use_count` + `last_used_at` on agent-created skills
- Auto-archives skills unused past configured window
- Consolidates overlapping skills at scale
- `hermes curator pin` protects from deletion (not from patch)

Foreground `skill_manage(create)` at user request is **not** curator-managed — considered user-directed.

Lattice has **no curator equivalent** yet. `forget` applies to semantic patterns only, not evolved skills.

---

## 9. Patch > Create > Edit (Token Economics)

| Action | When | Cost |
|--------|------|------|
| `patch` | Small fixes, new pitfall, tightened trigger | **Preferred** — only changed text |
| `create` | New class-level umbrella only | Full SKILL.md write |
| `edit` | Major structural rewrite | Full replacement |

Hermes docs: *"patch is preferred for updates — more token-efficient than edit."*

Lattice `HabitAction.EVOLVE` maps to patch semantics; `CREATE` should be rare.

---

## 10. Mapping to Lattice/Chorus (Corrected)

### Retry probe example — what goes where

| Content | Hermes bucket | Lattice store | Action |
|---------|---------------|---------------|--------|
| "HTTP client retries 429/503, 3×, exp backoff 0.2s–30s" | Sticky note / fact | **Pattern** `api.retry` | `patterns[]` → `lattice_context` |
| "Before patching client.py, get_run to recall failure shape" | Section in existing playbook | **Habit EVOLVE** | Patch `test-evidence` or `structuring-any-service` section |
| "On April 18 we saw 86 Gemini calls" | Diary — never skill | **Episodic only** | `recall` / `get_run` — do not promote |
| Full "how to implement HTTP retry policy" workflow | Class-level skill | **Rare CREATE** | Only if no role skill covers HTTP client work |

### What our plan got wrong

The integration plan's `retry-discipline` CREATE:

```json
{
  "action": "create",
  "slug": "retry-discipline",
  "body": "## Before patching\n\nRecall failure shape from get_run."
}
```

This is exactly [issue #12812](https://github.com/NousResearch/hermes-agent/issues/12812) territory:
- Too short for a skill (no When to Use, Procedure, Pitfalls, Verification)
- Sticky-note content masquerading as procedural memory
- Creates a narrow sibling instead of patching an umbrella

### What Lattice should do instead

| Hermes rule | Lattice implementation |
|-------------|------------------------|
| Sticky note → memory | Short facts → `patterns[]` only |
| Patch loaded skill first | Default `HabitAction.EVOLVE` into canonical role skill |
| Class-level CREATE only | Gate CREATE: min body length, required sections, no file-prefix slugs |
| Do NOT capture narratives | Reject habit bodies that look like diary ("we found", "today", run-specific counts) |
| references/ for session detail | Future: `HabitDraft` support files or episodic pointer only |
| Curator archival | Future: deprecate unused `evolved-skills/` by `last_used` |
| 5+ tool calls bar | Gate habit hints on episodic complexity signal (tool call count if available) |

---

## 11. Recommended Lattice Validation Changes

Add to `validate.py` for `HabitDraft`:

**CREATE gates (strict):**
- `MIN_HABIT_BODY_CHARS` ≥ 500 (or ~150 tokens) — peers start much larger
- Required sections: `## When to Use` (or equivalent), procedure steps, pitfalls OR verification
- Reject diary patterns: regex for "we found", "today", "on \<date\>", session-specific counts
- Slug must not derive from single file prefix alone (discourage `src-api` skills)

**EVOLVE gates (default path):**
- `skill` must exist in canonical **or** prior evolved-skills
- `section` + `new_content` must add procedure/pitfall, not restate a pattern fact
- Prefer EVOLVE: validation nudge if CREATE slug overlaps canonical domain

**Packet hints:**
- Stop auto-emitting `HintKind.HABIT` for every done cluster
- Emit habit hint only when cluster shows multi-step complexity (or agent explicitly requests)
- Habit hint should suggest **EVOLVE target** (nearest canonical skill slug), not new CREATE slug

**Directive update (`lattice-consolidate` skill):**

```
Preference order (Hermes-aligned):
1. patterns[] for facts (sticky notes)
2. habits evolve into EXISTING role skill (patch section)
3. habits create ONLY for new class-level playbook (Overview, When to Use, Procedure, Pitfalls, Verification)
4. Never create skills for one-off narratives or <500 char bodies
```

---

## 12. Revised Probe t8 (Hermes-aligned)

Instead of CREATE `retry-discipline`:

**t6 programmatic apply:**
- `patterns[]`: `api.retry` claim (fact)
- `habits[]`: **EVOLVE** `test-evidence` section `"Before patching HTTP clients"` with procedure distilled from 5 retry beats

**t8 check:**
- Evolved section exists in `.harness/skills/test-evidence/SKILL.md` (merged overlay)
- Agent loads `test-evidence` via `skill` tool on t8 — not a novel micro-skill slug

---

## Key Takeaways

1. **Short skills are bad** — Hermes treats them as diary entries that mislead future sessions ([#12812](https://github.com/NousResearch/hermes-agent/issues/12812)).

2. **Facts are memory, not skills** — retry policy numbers belong in `patterns[]` / `lattice_context`, not `habits[]`.

3. **Default to EVOLVE, not CREATE** — patch existing role skill sections; CREATE only for class-level umbrellas ([background_review.py](https://github.com/NousResearch/hermes-agent/blob/main/agent/background_review.py)).

4. **Real skills have structure** — When to Use, Procedure, Pitfalls, Verification; 8k–15k chars for operational workflows ([skill-authoring](https://github.com/NousResearch/hermes-agent/blob/main/skills/software-development/hermes-agent-skill-authoring/SKILL.md)).

5. **Lattice habit hints are too permissive** — auto-suggesting CREATE slugs from file prefixes will spam micro-skills; align with Hermes preference ladder.

6. **Our integration plan example was wrong** — replace `retry-discipline` CREATE with `api.retry` pattern + EVOLVE into existing role skill.

---

## Sources

1. [Working with Skills | Hermes](https://hermes-agent.nousresearch.com/docs/guides/work-with-skills) — sticky note vs reference manual
2. [Skills System | Hermes](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills) — 5+ tool calls, patch preferred
3. [hermes-agent#12812](https://github.com/NousResearch/hermes-agent/issues/12812) — diary-entry skills bug
4. [hermes-agent#23004](https://github.com/NousResearch/hermes-agent/pull/23004) — Do NOT capture prompts
5. [background_review.py](https://github.com/NousResearch/hermes-agent/blob/main/agent/background_review.py) — preference ladder, Do NOT list
6. [hermes-agent-skill-authoring/SKILL.md](https://github.com/NousResearch/hermes-agent/blob/main/skills/software-development/hermes-agent-skill-authoring/SKILL.md) — structure, 8–15k peers
7. [hermes-agent#30754](https://github.com/NousResearch/hermes-agent/issues/30754) — progressive disclosure, wrapper 1k–4k
8. [Curator | Hermes](https://hermes-agent.nousresearch.com/docs/user-guide/features/curator) — stale skill archival
9. [part5-creating-skills.md](https://github.com/OnlyTerp/hermes-optimization-guide/blob/main/part5-creating-skills.md) — anti-pattern one-off skills
10. [skill_manager_tool.py](https://github.com/NousResearch/hermes-agent/blob/main/tools/skill_manager_tool.py) — 100k limit, procedural vs declarative comment
11. [How To Write Hermes Skills That Compound](https://medium.com/ai-systems-lab/how-to-write-hermes-agent-skills-that-actually-compound-c7ceb7f2ad0a) — single job scope, <5k tokens body
12. [agentskills.io](https://agentskills.io/specification) — progressive disclosure model
