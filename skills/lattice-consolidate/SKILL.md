---
name: lattice-consolidate
description: Promote recurring beat evidence into lattice patterns (facts) and habits (skill overlays). Use ONLY at beat end when the gate is open — never every beat.
when_to_use: Beat end ONLY, when the harness beat-end notice says "Lattice gate open". Do not run on every beat — consolidation is expensive. Skip entirely when the gate is closed.
---

# lattice consolidate — patterns + habits (gate-gated)

Consolidation turns **recurring episodic evidence** into:

- **Patterns** — declarative facts (`api.retry`, `deploy.order`)
- **Habits** — procedural playbooks (evolve an existing skill or create a new overlay)

It is expensive. The gate ensures it runs only after enough new beats accumulate.

## Gate

1. **≥ N new beats** since last consolidation (default N = 5)
2. **A cluster** of ≥ K beats share the same file prefix or intent (default K = 2)

Silent beat-end notice → gate **closed** → do nothing.

## Workflow (gate open only)

### 1. Fetch the packet

```
lattice_packet()
```

Returns engrams plus hints tagged `pattern` or `habit`.

### 2. Re-read evidence

```
recall(query='…')
```

### 3. Author Proposal JSON

```json
{
  "employee_id": "e_be_1",
  "patterns": [
    {
      "key": "api.retry",
      "claim": "exponential backoff with 30s cap",
      "source_run_ids": ["r_done_1", "r_done_2"],
      "supersedes": null
    }
  ],
  "habits": [
    {
      "action": "evolve",
      "skill": "structuring-any-service",
      "section": "Scale the layering",
      "body": "Split when a module exceeds ~200 lines…",
      "source_run_ids": ["r_done_1", "r_done_2"]
    },
    {
      "action": "create",
      "slug": "retry-discipline",
      "title": "Retry discipline for HTTP clients",
      "body": "# Retry discipline\n\nAlways recall the failure shape before patching.",
      "source_run_ids": ["r_done_2"]
    }
  ]
}
```

| Construct | use when |
|---|---|
| `patterns[]` | durable **what is true** — cite recurring cluster |
| `habits evolve` | patch a section of an existing skill overlay |
| `habits create` | new overlay skill (slug must not collide with canonical role skills) |

Habits require ≥1 cited engram with `outcome=done`.

### 4. Apply

```
lattice_apply(proposal=<json above>)
```

Prefer ≤10 total patterns + habits combined.

## When NOT to consolidate

- Gate closed (most beats)
- Mid-beat
- Verbatim episodic prose — patterns must be shorter; habits must be actionable

## After apply

- Patterns surface via `lattice_context`
- Habits surface via `skill` tool on next beat (evolved-skills overlay)
