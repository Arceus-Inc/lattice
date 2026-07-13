"""Retrieval rendering with provenance."""

from __future__ import annotations

from datetime import UTC, datetime

from lattice.contracts.atom import Atom
from lattice.semantic.retrieve import render_context


def test_render_context_includes_source_run_ids() -> None:
    now = datetime.now(UTC)
    atoms = (
        Atom(
            key="api.retry",
            value="HTTP retries use exponential backoff capped at 30s",
            employee_id="e1",
            source_run_ids=("r_done_1", "r_done_2"),
            created_at=now,
        ),
    )
    context = render_context("retry", atoms)
    assert "api.retry" in context
    assert "r_done_1" in context
    assert "get_run(run_id)" in context
