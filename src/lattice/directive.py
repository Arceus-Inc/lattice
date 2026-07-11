"""Brief directives for chorus composition roots — when to use lattice tools."""

from __future__ import annotations

# Default gate: consolidation is expensive; run only after N new beats AND a cluster of K.
DEFAULT_MIN_NEW_EPISODES = 5
DEFAULT_MIN_CLUSTER_SIZE = 2

LATTICE_CONTEXT_DIRECTIVE = (
    "Distilled **patterns** live in lattice; raw beats live in episodic memory. "
    "Habits (procedural playbooks) live in evolved skills — load via the `skill` tool. "
    "At beat-start, call `lattice_context(query='…')` only when you need durable patterns "
    "for THIS intent — not every beat. "
    "For beat orientation use `recall()` or `recall(query='…')` (slim hits). "
    "For full beat prose use `get_run(run_id)` — especially on `src:` ids from lattice_context. "
    "For 'how should I act?' use evolved skills, not lattice_context."
)

LATTICE_CONSOLIDATE_DIRECTIVE = (
    "Consolidation is EXPENSIVE — never at every beat end. "
    f"Durable updates run only after ≥{DEFAULT_MIN_NEW_EPISODES} new beats AND a recurring cluster. "
    "When the beat-end notice says the gate is OPEN: load `lattice-consolidate` once, "
    "call `lattice_packet()`, `recall(query)` + `get_run(run_id)` per cited beat, "
    "author a Proposal with `patterns[]` (claims in clear plain English) and/or `habits[]` "
    "(evolve/create skill overlays), then `lattice_apply(proposal)`. "
    "When the gate is closed: do nothing — episodic capture already happened."
)

BEAT_END_GATE_OPEN = (
    "**Lattice gate open** — durable memory update is due this beat. "
    "Load `lattice-consolidate` (skill tool) → `lattice_packet` → Proposal → `lattice_apply`. "
    "Once per open gate; do not consolidate on every beat."
)


def beat_end_notice(*, gate_open: bool) -> str:
    """Teaser injected at beat end — silent when gate closed (no expensive nudge)."""
    if not gate_open:
        return ""
    return BEAT_END_GATE_OPEN


def beat_start_notice(*, context: str, max_chars: int = 400) -> str:
    """Optional beat-start teaser from lattice context — empty when nothing scored."""
    trimmed = context.strip()
    if not trimmed:
        return ""
    if len(trimmed) > max_chars:
        trimmed = trimmed[: max_chars - 3].rstrip() + "..."
    return f"**Distilled memory:**\n{trimmed}"
