"""Brief directives for chorus composition roots — patterns only."""

from __future__ import annotations

DEFAULT_MIN_NEW_EPISODES = 5
DEFAULT_MIN_CLUSTER_SIZE = 2

LATTICE_CONTEXT_DIRECTIVE = (
    "Distilled **patterns** live in lattice; raw beats live in episodic memory. "
    "At beat-start, call `lattice_context(query='…')` only when you need durable patterns "
    "for THIS intent — not every beat. "
    "For beat orientation use `recall()` or `recall(query='…')` (slim hits). "
    "For full beat prose use `get_run(run_id)` — especially on `src:` ids from lattice_context."
)

LATTICE_CONSOLIDATE_DIRECTIVE = (
    "Consolidation is EXPENSIVE — never at every beat end. "
    f"Pattern updates run only after ≥{DEFAULT_MIN_NEW_EPISODES} new beats AND a recurring cluster. "
    "When the beat-end notice says the gate is OPEN: load `lattice-consolidate` once, "
    "call `lattice_packet()`, `recall(query)` + `get_run(run_id)` per cited beat, "
    "author a Proposal with `patterns[]` (claims in clear plain English), "
    "then `lattice_apply(proposal)`. "
    "When the gate is closed: do nothing — episodic capture already happened."
)

BEAT_END_GATE_OPEN = (
    "**Lattice gate open** — pattern consolidation is due this beat. "
    "Load `lattice-consolidate` → `lattice_packet` → patterns Proposal → `lattice_apply`. "
    "Once per open gate; do not consolidate on every beat."
)


def beat_end_notice(*, gate_open: bool) -> str:
    if not gate_open:
        return ""
    return BEAT_END_GATE_OPEN


def beat_start_notice(*, context: str, max_chars: int = 400) -> str:
    trimmed = context.strip()
    if not trimmed:
        return ""
    if len(trimmed) > max_chars:
        trimmed = trimmed[: max_chars - 3].rstrip() + "..."
    return f"**Distilled patterns:**\n{trimmed}"
