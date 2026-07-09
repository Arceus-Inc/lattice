# feat/patterns-only

This branch strips **habits** (procedural skill evolution) to focus on mastering:

1. **Consolidation** — gate → packet → agent proposal
2. **Creation** — pattern assert / supersede → atom store
3. **Retrieval** — `lattice_context(query)` over active patterns

Habits are additive on `main` and will merge back when pattern semantics are solid.

## Scope

| In | Out (deferred to main) |
|---|---|
| `PatternDraft`, `Proposal.patterns[]` | `HabitDraft`, habits in proposals |
| `AtomStore` / `MEMORY.md` view | `PatchStore`, evolved skills |
| Pattern packet hints | Habit packet hints |
| `lattice-context`, `lattice-consolidate` (patterns) | Skill overlay creation/evolve |

## Test focus

```bash
uv run pytest tests/test_proposal_flow.py tests/test_cluster.py tests/test_directive.py -q
```
