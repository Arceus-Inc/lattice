---
name: lattice-consolidate
description: Promote recurring beat evidence into durable lattice atoms. Use ONLY at beat end when the gate is open (≥N new beats + recurring cluster) — never every beat.
when_to_use: Beat end ONLY, when the harness beat-end notice says "Lattice gate open". Do not run on every beat — consolidation is expensive. Skip entirely when the gate is closed.
---

# lattice consolidate — beat-end promotion (gate-gated)

Consolidation turns **recurring episodic evidence** into **durable atoms**. It is expensive (agent-authored proposal + validate + disk write). The gate ensures it runs only after enough new beats accumulate.

## Gate (when consolidation is allowed)

Consolidation is due when **both** are true:

1. **≥ N new beats** since the last successful consolidation (default N = 5)
2. **A cluster** of ≥ K beats share the same file prefix or intent token (default K = 2)

If the beat-end notice is **silent**, the gate is **closed** — do nothing. Your beat is already in episodic memory.

## Beat-end workflow (gate open only)

Run this **once** before ending the beat:

### 1. Fetch the packet

```
lattice_packet()
```

Returns ranked engrams since the cursor plus deterministic hints `(key_template, run_ids)`.

### 2. Re-read evidence

For each cited `run_id` in hints (or your chosen cluster), call:

```
recall(query='…')   # or recall() for recency
```

Read outcome + prose. **You** extract the durable claim — lattice does not LLM-extract.

### 3. Author Proposal JSON

Prefer **few, high-signal ops** (≤ 10). Every op must cite real `source_run_ids`.

```json
{
  "employee_id": "e_be_1",
  "ops": [
    {
      "kind": "assert",
      "key": "api.retry",
      "value": "exponential backoff with 30s cap; cite r123",
      "source_run_ids": ["r_done_1", "r_done_2"]
    }
  ]
}
```

| kind | use when |
|---|---|
| `assert` | new fact at unused key |
| `supersede` | replace an active fact (`supersedes` names the old key) |
| `patch` | skill overlay (P1; requires a `done` engram) |

Keys: lowercase hierarchical `api.retry`, `deploy.migration_order`.

### 4. Apply

```
lattice_apply(proposal=<json above>)
```

If errors return, fix citations/keys and retry once. Do not spam apply.

## When NOT to consolidate

- Gate closed (most beats)
- Single-beat spike with no recurrence — wait for cluster
- Mid-beat — never consolidate while implementation is in flight
- Duplicating episodic prose verbatim — atoms must be shorter and durable

## After apply

Next beat may show distilled lines via `lattice_context`. Episodic history remains in `recall()`.
