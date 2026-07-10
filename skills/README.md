# lattice skills (deprecated here)

Agent skill playbooks now live in **chorus** at `chorus_employee/_lattice_skills/`.

This directory is kept for reference during the patterns-only integration milestone. Do not add new materialization logic in chorus that reads from this path.

| Skill | Tool(s) | When |
|---|---|---|
| `lattice-context` | `lattice_context`, `get_run` | Beat-start — patterns; full prose via `get_run` on `src:` ids |
| `lattice-consolidate` | `lattice_packet`, `recall`, `get_run`, `lattice_apply` | Beat-end when gate open — slim search then full prose per cite |

See [`docs/patterns-only.md`](../docs/patterns-only.md) for branch scope (habits deferred).
