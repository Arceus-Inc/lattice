# lattice v1 — patterns only (`feat/patterns-only`)

**Status:** semantic pattern consolidation + retrieval. Habits deferred (live on `main`).

## THE LOOP

| Stage | Owner |
|---|---|
| WRITE / STORE / `recall()` | chorus |
| RANK / gate / packet hints | lattice |
| Author `Proposal.patterns[]` | agent |
| validate / apply | lattice |
| `context(query)` retrieval | lattice |

## Five functions

```text
gate_open(employee_id) → bool
packet(employee_id)      → Packet | ∅
validate(proposal)       → ValidationResult
apply(proposal)          → ApplyResult
context(employee_id, q)  → markdown patterns
```

## Proposal

```json
{
  "employee_id": "e_be_1",
  "patterns": [
    { "key": "api.retry", "claim": "…", "source_run_ids": ["r1"], "supersedes": null }
  ]
}
```

## Validate

1. ≥1 pattern; ≤ L patterns
2. Valid `source_run_ids`
3. Key format `^[a-z][a-z0-9_.]+$`
4. New key or explicit `supersedes`

## Milestones (this branch)

| Milestone | Delivers |
|---|---|
| **P0** | gate, packet, validate, apply, context |
| **P1** | chorus bridge + tool wiring |
| **P2** | activation bump on context hit |

Habits merge from `main` after pattern path is proven.
