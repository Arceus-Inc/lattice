---
name: lattice-consolidate
description: Promote recurring beat evidence into lattice patterns (semantic facts). Use ONLY at beat end when the gate is open — never every beat.
when_to_use: Beat end ONLY, when the beat-end notice says "Lattice gate open". Skip when gate is closed.
---

# lattice consolidate — patterns only (gate-gated)

Turn **recurring episodic evidence** into **durable patterns** (key/value facts). Expensive — only when gate opens.

## Gate

1. **≥ N new beats** since last consolidation (default 5)
2. **Cluster** of ≥ K beats share file prefix or intent (default 2)

Silent beat-end notice → gate closed → do nothing.

## Workflow

### 1. Packet

```
lattice_packet()
```

### 2. Re-read evidence

```
recall(query='…')
```

### 3. Proposal JSON

```json
{
  "employee_id": "e_be_1",
  "patterns": [
    {
      "key": "api.retry",
      "claim": "HTTP client retries use exponential backoff capped at 30s; see src/api/client.py",
      "source_run_ids": ["r_done_1", "r_done_2"],
      "supersedes": null
    }
  ]
}
```

| field | use |
|---|---|
| `key` | hierarchical lowercase `api.retry` |
| `claim` | 1–2 sentences: decision + constraint/scope/file path (min ~20 chars) |
| `source_run_ids` | every cited beat — rendered at retrieval for `recall()` drill-down |
| `supersedes` | set when replacing an active pattern key |

### Claim quality

| Too short (rejected) | Good |
|---|---|
| `"exponential backoff"` | `"HTTP retries use exponential backoff capped at 30s; config in src/api/client.py"` |

Patterns stay small; episodic prose stays in chorus. Cite real `source_run_ids` so `lattice_context` can point the agent back to ground truth.

### 4. Apply

```
lattice_apply(proposal=<json>)
```

≤10 patterns per proposal. No verbatim episodic prose.

## After apply

Next beat: `lattice_context(query)` surfaces patterns with `src:` run ids — call `recall(query='…')` when you need beat prose.
