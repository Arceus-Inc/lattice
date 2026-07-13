"""retrieve.py — BM25 relevance scoring."""

from __future__ import annotations

from datetime import UTC, datetime

from lattice.contracts.atom import Atom
from lattice.semantic.retrieve import atom_doc, render_context, score, tokenize, top_k


def _atom(key: str, claim: str, *, key_files: tuple[str, ...] = ()) -> Atom:
    return Atom(
        key=key,
        value=claim,
        employee_id="e1",
        source_run_ids=("r1",),
        created_at=datetime.now(UTC),
        key_files=key_files,
    )


def test_tokenize_strips_punctuation_and_short_tokens() -> None:
    assert tokenize("Retry, HTTP! a") == ["retry", "http"]


def test_atom_doc_repeats_key_segments() -> None:
    doc = atom_doc(_atom("api.retry", "claim text", key_files=("src/api/client.py",)))
    assert doc.count("api retry") >= 2
    assert "claim text" in doc
    assert "src api client.py" in doc


def test_bm25_ranks_retry_above_unrelated_theme() -> None:
    retry = _atom(
        "api.retry",
        "HTTP retries use exponential backoff capped at 30s",
        key_files=("src/api/client.py",),
    )
    theme = _atom("ui.theme", "dark mode uses CSS variables in src/ui/theme.css")
    atoms = (retry, theme)
    selected = top_k("retry exponential backoff", atoms, k=1)
    assert len(selected) == 1
    assert selected[0].key == "api.retry"


def test_bm25_prefers_more_specific_retry_claim() -> None:
    vague = _atom(
        "api.client",
        "HTTP client lives in src/api/client.py",
        key_files=("src/api/client.py",),
    )
    specific = _atom(
        "api.retry",
        "HTTP retries use exponential backoff capped at 30 seconds on 429 and 503",
        key_files=("src/api/client.py",),
    )
    atoms = (vague, specific)
    selected = top_k("exponential backoff 429 503", atoms, k=1)
    assert selected[0].key == "api.retry"


def test_single_eligible_atom_retrieved() -> None:
    retry = _atom("api.retry", "HTTP retries use exponential backoff capped at 30s")
    context = render_context("retry policy", (retry,))
    assert "api.retry" in context


def test_empty_atoms_returns_empty_context() -> None:
    assert render_context("retry", ()) == ""
