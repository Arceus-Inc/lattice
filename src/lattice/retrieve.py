"""Retrieval scoring and context rendering."""

from __future__ import annotations

import math
from datetime import UTC, datetime

from lattice.contracts.atom import Atom

DEFAULT_TOP_K = 5
WEIGHT_RECENCY = 0.3
WEIGHT_OVERLAP = 0.5
WEIGHT_ACTIVATION = 0.2
RECENCY_HALF_LIFE_DAYS = 14.0


def score(query: str, atom: Atom, *, now: datetime | None = None) -> float:
    """score(q, a) = w_r·recency + w_b·overlap + w_a·activation."""
    reference = now or datetime.now(UTC)
    return (
        WEIGHT_RECENCY * _recency(atom.created_at, reference)
        + WEIGHT_OVERLAP * _overlap(query, atom)
        + WEIGHT_ACTIVATION * atom.activation
    )


def top_k(query: str, atoms: tuple[Atom, ...], *, k: int = DEFAULT_TOP_K) -> tuple[Atom, ...]:
    """Return the k highest-scoring active atoms."""
    ranked = sorted(atoms, key=lambda atom: score(query, atom), reverse=True)
    return tuple(ranked[:k])


def render_context(query: str, atoms: tuple[Atom, ...], *, k: int = DEFAULT_TOP_K) -> str:
    """Render top-k patterns with provenance cues for recall drill-down."""
    selected = top_k(query, atoms, k=k)
    if not selected:
        return ""
    lines = ["## lattice patterns", ""]
    for atom in selected:
        lines.extend(_format_pattern_lines(atom))
    return "\n".join(lines) + "\n"


def _format_pattern_lines(atom: Atom) -> tuple[str, ...]:
    out: list[str] = [f"- **{atom.key}**: {atom.value}"]
    if atom.source_run_ids:
        src = ", ".join(atom.source_run_ids)
        out.append(f"  src: {src} — recall(query='…') for beat detail")
    return tuple(out)


def _overlap(query: str, atom: Atom) -> float:
    query_tokens = set(query.lower().split())
    if not query_tokens:
        return 0.0
    text_tokens = set(f"{atom.key} {atom.value}".lower().split())
    return len(query_tokens & text_tokens) / len(query_tokens)


def _recency(created_at: datetime, now: datetime) -> float:
    age_days = max(0.0, (now - created_at).total_seconds() / 86_400.0)
    return math.exp(-age_days / RECENCY_HALF_LIFE_DAYS)
