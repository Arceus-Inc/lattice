# PRD: Skill Manager + DB Versioning

See full plan: [`docs/skill-manager-harness-plan.md`](../../docs/skill-manager-harness-plan.md)

## One-liner

Hermes `skill_manage` action space + Paperclip append-only `skill_versions` in SQLite + Dream-safe materialize.

## Phases

| # | Slice | Depends |
|---|-------|---------|
| P0 | Schema + VersionedSkillStore | — |
| P1 | SkillManager + Hermes gates | P0 |
| P2 | Chorus `skill_manage` tool | P1 |
| P3 | `lattice_apply` → SkillManager | P1 |
| P4 | Materialize HEAD + pins | P2, P3 |
| P5 | Migrate overlays → DB | P4 |
| P6 | Live e2e backend_engineer | P5 |
| P7 | Curator soft-archive | P6 |

## Harness contract

Every tool obs: `status` · `summary` · `next_actions` · `artifacts` · error → `root_cause`/`retry`/`stop`.
