# lattice

**The consolidation layer — episodic traces → validated semantic atoms.**

> `dream` completes one task · `chorus` runs the org · **`lattice` validates and stores what agents propose.**

lattice is an SDK sibling to horizon. It reads chorus's append-only episodic stream, ranks evidence, and applies agent-authored proposals:

| Layer | Priority | Output |
|---|---|---|
| **Semantic** | P0 | `MEMORY.md` view + `semantic/*.json` atoms |
| **Procedural** | P1 | `evolved-skills/<slug>/SKILL.md` overlays (deferred) |

chorus owns WRITE / STORE / `recall()` pull. The agent authors proposals. lattice owns RANK / validate / apply / context.

See [`docs/v1-plan.md`](docs/v1-plan.md). Employee skills live in [`skills/`](skills/) — materialize alongside role skills so agents know **when** to call lattice tools (consolidation only after N beats when the gate opens, not every beat end).

## Employee skills

| Skill | When |
|---|---|
| `lattice-context` | Beat-start — `lattice_context` vs `recall` |
| `lattice-consolidate` | Beat-end — **only** when gate is open (default: ≥5 new beats + cluster) |

Brief directives for chorus wiring: `lattice.directive.LATTICE_CONTEXT_DIRECTIVE`, `LATTICE_CONSOLIDATE_DIRECTIVE`.

## Quickstart

```bash
uv sync --extra dev
uv run pytest -q
```

```python
from lattice.compose import build_default
from lattice.domain import Op, OpKind, Proposal

lattice = build_default(consolidated_root=".lattice", episodes=episodic_reader)
if lattice.gate_open("e_be_1"):
    packet = lattice.packet("e_be_1")
    result = lattice.apply(
        Proposal(
            employee_id="e_be_1",
            ops=(Op(kind=OpKind.ASSERT, key="api.retry", value="...", source_run_ids=("r1",)),),
        )
    )
context = lattice.context("e_be_1", "retry policy")
```

## Package map

```
src/lattice/
  contracts/      ports (EpisodicReader, AtomStore, PatchStore, …)
  domain/         Proposal, Op, Packet, ValidationResult, ApplyResult
  cluster.py      gate, rank, cluster, packet hints
  validate.py     deterministic proposal rules
  apply.py        transactional writes
  retrieve.py     score + context markdown
  stores/         MemoryMdStore, OverlaySkillStore, JsonCursorStore
  facade.py       Lattice (5 functions)
  compose.py      build_default()
```

## Seam

[`examples/chorus_bridge.py`](examples/chorus_bridge.py) is the **only** place allowed to import chorus.

## License

MIT.
