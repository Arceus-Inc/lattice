# lattice skills

Canonical skill bundles for chorus employees. Materialize this directory into the worktree the same way role skills are copied to `.harness/skills/` (see `chorus_harness._skills.materialize_skills`).

## Skills

| Skill | Tool(s) | When |
|---|---|---|
| `lattice-context` | `lattice_context` | Beat-start — patterns (facts) when durable context matters |
| `lattice-consolidate` | `lattice_packet`, `lattice_apply` | Beat-end — patterns + habits when gate is open |

## Beat policy

- **Every beat:** chorus captures episodic engrams automatically (cheap append).
- **Most beats:** gate closed → no consolidation, no `lattice_apply`.
- **Every ~N beats** (default 5) with a recurring cluster: gate opens → beat-end notice → agent loads `lattice-consolidate` once.

Brief directives for composition roots live in `src/lattice/directive.py` (`LATTICE_CONTEXT_DIRECTIVE`, `LATTICE_CONSOLIDATE_DIRECTIVE`).

## Wiring (chorus composition root)

```python
from pathlib import Path
from lattice.directive import (
    LATTICE_CONSOLIDATE_DIRECTIVE,
    LATTICE_CONTEXT_DIRECTIVE,
    beat_end_notice,
)

SKILLS_ROOT = Path(lattice.__file__).resolve().parents[2] / "skills"  # repo root skills/

# Append to employee brief when lattice tools are registered.
# At beat end: inject beat_end_notice(gate_open=lattice.gate_open(employee_id))
```

Copy `skills/` alongside employee role skills or merge into one `materialize_skills` source tree.
