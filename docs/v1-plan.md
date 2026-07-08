# lattice v1 — scaffold

**Status:** L0 scaffold · semantic P0 + procedural P1 packages present, noop extractors.

lattice turns chorus episodic traces into:

- **Semantic (P0):** `MEMORY.md` + atom dir under `consolidated/<employee_id>/`
- **Procedural (P1):** `evolved-skills/<slug>/SKILL.md` overlays

## THE LOOP

| Stage | Owner |
|---|---|
| WRITE / STORE / RETRIEVE (pull) | chorus |
| RANK / RECONCILE / FORGET | lattice |
| Push catalogue | lattice → beat-start injection (composition root) |

## Package map

```
contracts/     ports
domain/        pure types
episodic/      trigger + selector
semantic/      P0 vertical slice
procedural/    P1 vertical slice
consolidate/   ConsolidationPass
stores/        default file adapters
facade.py      Lattice
compose.py     build_default()
```

## Milestones

- **L0** — this scaffold
- **L1** — real `ChorusEpisodicReader` seam tests
- **L2** — LLM semantic extractor + skill evolver
- **L3** — reconcile UPDATE/DELETE + two-arm promotion gate
- **L4** — pruner + optional embeddings
