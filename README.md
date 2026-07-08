# lattice

**The consolidation layer — episodic traces → semantic facts + evolved skills.**

> `dream` completes one task · `chorus` runs the org · **`lattice` decides what's worth remembering.**

lattice is an SDK sibling to horizon. It reads chorus's append-only episodic stream and promotes:

| Layer | Priority | Output |
|---|---|---|
| **Semantic** | P0 | `MEMORY.md` + atom dir |
| **Procedural** | P1 | `evolved-skills/<slug>/SKILL.md` overlays |

chorus owns WRITE / STORE / `recall()` pull. lattice owns RANK / RECONCILE / FORGET.

See [`docs/v1-plan.md`](docs/v1-plan.md).

## Quickstart

```bash
uv sync --extra dev
uv run pytest -q
```

```python
from lattice.compose import build_default

lattice = build_default(consolidated_root=".lattice", episodes=episodic_reader)
result = lattice.consolidate("e_be_1")
```

## Package map

```
src/lattice/
  contracts/      ports (EpisodicReader, SemanticStore, ProceduralStore, …)
  domain/         pure types (EpisodeBatch, ConsolidationResult, …)
  episodic/       trigger + selector (RANK)
  semantic/       P0 extract → reconcile → promote
  procedural/     P1 evolve → gate → promote
  consolidate/    ConsolidationPass (THE LOOP)
  stores/         MemoryMdStore, OverlaySkillStore, JsonCursorStore
  facade.py       Lattice
  compose.py      build_default()
```

## Seam

[`examples/chorus_bridge.py`](examples/chorus_bridge.py) is the **only** place allowed to import chorus.

## License

MIT.
