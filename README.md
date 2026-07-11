# lattice

**The consolidation layer — episodic traces → patterns (facts) + habits (skills).**

> `dream` completes one task · `chorus` runs the org · **`lattice` validates and stores what agents propose.**

lattice is an SDK sibling to horizon. It reads chorus's append-only episodic stream, ranks evidence, and applies agent-authored proposals:

| Layer | Priority | Output |
|---|---|---|
| **Patterns (P0)** | semantic facts | `MEMORY.md` view + `semantic/*.json` |
| **Habits (P1)** | procedural playbooks | `evolved-skills/<slug>/SKILL.md` overlays |

chorus owns WRITE / STORE / `recall()` pull. The agent authors proposals. lattice owns RANK / validate / apply / context.

See [`docs/v1-plan.md`](docs/v1-plan.md). Employee skills live in [`skills/`](skills/) — materialize alongside role skills so agents know **when** to call lattice tools (consolidation only after N beats when the gate opens, not every beat end).

## Employee skills

| Skill | When |
|---|---|
| `lattice-context` | Beat-start — patterns via `lattice_context` vs `recall` vs habits via `skill` |
| `lattice-consolidate` | Beat-end — **only** when gate is open (default: ≥5 new beats + cluster) |

Brief directives for chorus wiring: `lattice.directive.LATTICE_CONTEXT_DIRECTIVE`, `LATTICE_CONSOLIDATE_DIRECTIVE`.

## Quickstart

```bash
uv sync --extra dev
uv run pytest -q
```

```python
from lattice.compose import build_default
from lattice.domain import HabitAction, HabitDraft, PatternDraft, Proposal

lattice = build_default(consolidated_root=".lattice", episodes=episodic_reader, enable_patches=True)
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
            habits=(
                HabitDraft(
                    action=HabitAction.CREATE,
                    slug="retry-discipline",
                    title="Retry discipline",
                    body="# Retry discipline\n\n…",
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
  contracts/      ports (EpisodicReader, AtomStore, PatchStore, …)
  domain/         PatternDraft, HabitDraft, Proposal, Packet
  compile.py      patterns/habits → internal ops
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
