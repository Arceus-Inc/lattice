"""Retrieval scoring and context rendering."""

from __future__ import annotations

import math
from datetime import UTC, datetime

from rank_bm25 import BM25Okapi

from lattice.contracts.atom import Atom
from lattice.domain.stats import PatternStats, Tier

DEFAULT_TOP_K = 5
WEIGHT_TRUST = 0.35
WEIGHT_BM25 = 0.40
WEIGHT_RECENCY = 0.15
WEIGHT_ACTIVATION = 0.10
RULE_TIER_BONUS = 0.15
MIN_OVERLAP = 0.15
RECENCY_HALF_LIFE_DAYS = 14.0
_PUNCTUATION = ".,;:!?()[]{}"


def atom_doc(atom: Atom) -> str:
    """BM25 document text — key segments repeated for mild field boost."""
    segments = atom.key.replace(".", " ")
    paths = " ".join(atom.key_files).replace("/", " ").replace("\\", " ")
    return f"{atom.key} {segments} {segments} {atom.value} {paths}"


def tokenize(text: str) -> list[str]:
    """Lowercase whitespace tokens with punctuation stripped (min length 2)."""
    cleaned = text.lower()
    for ch in _PUNCTUATION:
        cleaned = cleaned.replace(ch, " ")
    return [token for token in cleaned.split() if len(token) >= 2]


def eligible(query: str, atom: Atom) -> bool:
    """Domain gate — exclude clearly off-domain patterns for the query."""
    if _overlap(query, atom) >= MIN_OVERLAP:
        return True

    lower_query = query.lower()
    for segment in atom.key.split("."):
        if segment and segment.lower() in lower_query:
            return True

    query_tokens = set(lower_query.split())
    for path in atom.key_files:
        for component in _path_components(path):
            if component in query_tokens:
                return True

    return False


def score(
    query: str,
    atom: Atom,
    *,
    atoms: tuple[Atom, ...] | None = None,
    bm25_norm: float | None = None,
    now: datetime | None = None,
) -> float:
    """score(q, a) = w_b·bm25 + w_t·trust + w_r·recency + w_a·activation."""
    reference = now or datetime.now(UTC)
    if bm25_norm is None:
        corpus = atoms if atoms is not None else (atom,)
        norms = _bm25_normalized_scores(query, corpus)
        try:
            index = corpus.index(atom)
        except ValueError:
            index = 0
        bm25_norm = norms[index] if norms else 0.0

    return (
        WEIGHT_TRUST * _trust(atom)
        + WEIGHT_BM25 * bm25_norm
        + WEIGHT_RECENCY * _recency(atom.created_at, reference)
        + WEIGHT_ACTIVATION * atom.activation
    )


def top_k(query: str, atoms: tuple[Atom, ...], *, k: int = DEFAULT_TOP_K) -> tuple[Atom, ...]:
    """Return the k highest-scoring active atoms that pass the domain gate."""
    if not atoms:
        return ()

    reference = datetime.now(UTC)
    bm25_norms = _bm25_normalized_scores(query, atoms)
    ranked: list[tuple[float, Atom]] = []
    for atom, bm25_norm in zip(atoms, bm25_norms, strict=True):
        if not eligible(query, atom):
            continue
        total = score(query, atom, bm25_norm=bm25_norm, now=reference)
        ranked.append((total, atom))

    ranked.sort(key=lambda item: item[0], reverse=True)
    return tuple(atom for _, atom in ranked[:k])


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
    out: list[str] = [f"- **{atom.key}**", "", atom.value.strip(), ""]
    if atom.source_run_ids:
        src = ", ".join(atom.source_run_ids)
        out.append(f"  src: {src} — get_run(run_id) for full beat prose")
    return tuple(out)


def _bm25_normalized_scores(query: str, atoms: tuple[Atom, ...]) -> tuple[float, ...]:
    if not atoms:
        return ()

    corpus = [tokenize(atom_doc(atom)) for atom in atoms]
    if not any(corpus):
        return tuple(0.0 for _ in atoms)

    bm25 = BM25Okapi(corpus)
    raw = tuple(float(value) for value in bm25.get_scores(tokenize(query)))
    return _normalize_scores(raw)


def _normalize_scores(scores: tuple[float, ...]) -> tuple[float, ...]:
    if not scores:
        return ()
    lo = min(scores)
    hi = max(scores)
    if hi <= lo:
        return tuple(0.0 for _ in scores)
    span = hi - lo
    return tuple((value - lo) / span for value in scores)


def _trust(atom: Atom) -> float:
    stats = atom.stats or PatternStats.jeffreys_prior()
    tier_bonus = RULE_TIER_BONUS if stats.tier is Tier.RULE else 0.0
    return tier_bonus + stats.lcb05


def _overlap(query: str, atom: Atom) -> float:
    query_tokens = set(query.lower().split())
    if not query_tokens:
        return 0.0
    text_tokens = set(f"{atom.key} {atom.value}".lower().split())
    return len(query_tokens & text_tokens) / len(query_tokens)


def _path_components(path: str) -> tuple[str, ...]:
    raw = path.replace("/", " ").replace("\\", " ").replace(".", " ").split()
    return tuple(token.lower() for token in raw if len(token) >= 2)


def _recency(created_at: datetime, now: datetime) -> float:
    age_days = max(0.0, (now - created_at).total_seconds() / 86_400.0)
    return math.exp(-age_days / RECENCY_HALF_LIFE_DAYS)
