# lattice

**The consolidation layer — episodic traces → durable patterns (facts), with habit *validation* for Chorus skill evolution.**

> `dream` completes one task · `chorus` runs the org · **`lattice` validates and stores what agents propose.**

| Layer | Owner | Output |
|---|---|---|
| **Patterns** | Lattice | `MEMORY.md` + `semantic/*.json` |
| **Procedures** | Chorus `skill_manage` / SkillStore | Versioned skills rematerialized into `.harness/skills/` |
| **Habit gates** | Lattice `validate.py` | EVOLVE-first, diary reject, CREATE rarity |

Agent playbooks (`lattice-context`, `lattice-consolidate`) live in **chorus** at `chorus_employee/_lattice_skills/`. Lattice keeps brief directives only (`lattice.directive`).

Docs index: [`docs/README.md`](docs/README.md) · start with [`docs/plans/v1-plan.md`](docs/plans/v1-plan.md).

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
  facade.py / compose.py / errors.py   public composition root
  contracts/      ports (EpisodicReader, AtomStore, PatchStore, …)
  domain/         PatternDraft, HabitDraft, Proposal, Packet
  stores/         MemoryMdStore, JsonCursorStore, OverlaySkillStore (legacy/tests)
  consolidate/    cluster → compile → validate → apply
  semantic/       retrieve, adjudicate, forget
  harness/        directive briefs + beat notices
  directive.py    compatibility re-export of harness.directive

tests/
  unit/           fast module tests
  components/     store / apply / retrieve components
  integration/    end-to-end seam scenarios

docs/
  plans/          product + integration plans
  research/       background research
  assets/         diagrams
```

## Seam

[`examples/chorus_bridge.py`](examples/chorus_bridge.py) is the **only** place allowed to import chorus.

## License

MIT.
