"""retrieve.py — scoring and context rendering."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from lattice.contracts.atom import Atom
from lattice.retrieve import render_context, score, top_k


def _atom(key: str, claim: str, *, days_ago: int = 0) -> Atom:
    now = datetime.now(UTC)
    return Atom(
        key=key,
        value=claim,
        employee_id="e1",
        source_run_ids=("r1",),
        created_at=now - timedelta(days=days_ago),
    )


def test_score_prefers_token_overlap() -> None:
    retry = _atom("api.retry", "HTTP retries use exponential backoff capped at 30s")
    unrelated = _atom("ui.theme", "dark mode uses CSS variables in src/ui/theme.css")
    assert score("retry HTTP backoff", retry) > score("retry HTTP backoff", unrelated)


def test_top_k_limits_results() -> None:
    atoms = (
        _atom("a.one", "first pattern with enough claim text here"),
        _atom("a.two", "second pattern with enough claim text here"),
        _atom("a.three", "third pattern with enough claim text here"),
    )
    result = top_k("pattern", atoms, k=2)
    assert len(result) == 2


def test_render_context_empty_for_no_atoms() -> None:
    assert render_context("retry", ()) == ""
