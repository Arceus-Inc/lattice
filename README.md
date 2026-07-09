# lattice

**Pattern consolidation — episodic traces → durable semantic facts.**

> `dream` completes one task · `chorus` runs the org · **`lattice` validates and stores patterns agents propose.**

**Branch `feat/patterns-only`:** habits (procedural skills) removed — sync from `main` later. See [`docs/patterns-only.md`](docs/patterns-only.md).

| Construct | Output |
|---|---|
| **Pattern** | `semantic/*.json` atoms + `MEMORY.md` view |

chorus owns WRITE / STORE / `recall()`. lattice owns gate → validate → apply → `context()`.

## Quickstart

```bash
uv sync --extra dev
uv run pytest -q
```

```python
from lattice.compose import build_default
from lattice.domain import PatternDraft, Proposal

lattice = build_default(consolidated_root=".lattice", episodes=episodic_reader)
if lattice.gate_open("e_be_1"):
    packet = lattice.packet("e_be_1")
    result = lattice.apply(
        Proposal(
            employee_id="e_be_1",
            patterns=(
                PatternDraft(
                    key="api.retry",
                    claim="HTTP client retries use exponential backoff capped at 30s",
                    source_run_ids=("r1",),
                ),
            ),
        )
    )
context = lattice.context("e_be_1", "retry policy")
```

## Package map

```
src/lattice/
  cluster.py      gate, rank, cluster, pattern hints
  compile.py      PatternDraft → ops
  validate.py     pattern rules
  apply.py        atom writes
  retrieve.py     context scoring
  stores/         MemoryMdStore, JsonCursorStore
  facade.py       Lattice
```

## License

MIT.
