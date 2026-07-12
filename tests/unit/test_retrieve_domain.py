"""retrieve.py — domain gate and trust-weighted scoring."""

from __future__ import annotations

from datetime import UTC, datetime

from lattice.contracts.atom import Atom
from lattice.domain.stats import PatternStats, Tier
from lattice.retrieve import eligible, render_context, score, top_k


def _atom(
    key: str,
    claim: str,
    *,
    key_files: tuple[str, ...] = (),
    tier: Tier = Tier.HINT,
    alpha: float = 2.0,
    beta: float = 0.5,
) -> Atom:
    now = datetime.now(UTC)
    return Atom(
        key=key,
        value=claim,
        employee_id="e1",
        source_run_ids=("r1",),
        created_at=now,
        key_files=key_files,
        stats=PatternStats(alpha_own=alpha, beta_own=beta, tier=tier),
    )


def test_rule_outranks_hint_at_equal_overlap() -> None:
    query = "retry HTTP backoff"
    hint = _atom(
        "api.retry",
        "HTTP retries use exponential backoff capped at 30s",
        tier=Tier.HINT,
        alpha=2.0,
        beta=0.5,
        key_files=("src/api/client.py",),
    )
    rule = _atom(
        "api.retry",
        "HTTP retries use exponential backoff capped at 30s",
        tier=Tier.RULE,
        alpha=6.0,
        beta=0.5,
        key_files=("src/api/client.py",),
    )
    atoms = (hint, rule)
    assert score(query, rule, atoms=atoms) > score(query, hint, atoms=atoms)


def test_design_query_excludes_api_retry() -> None:
    retry = _atom(
        "api.retry",
        "HTTP retries use exponential backoff capped at 30s",
        key_files=("src/api/client.py",),
    )
    selected = top_k("design tokens typography", (retry,))
    assert selected == ()


def test_retry_query_includes_api_retry() -> None:
    retry = _atom(
        "api.retry",
        "HTTP retries use exponential backoff capped at 30s",
        key_files=("src/api/client.py",),
    )
    selected = top_k("retry policy api", (retry,))
    assert len(selected) == 1
    assert selected[0].key == "api.retry"


def test_legacy_atom_without_key_files_retrieved_by_overlap() -> None:
    retry = _atom(
        "api.retry",
        "HTTP retries use exponential backoff capped at 30s",
        key_files=(),
    )
    assert eligible("retry HTTP backoff", retry)
    context = render_context("retry HTTP backoff", (retry,))
    assert "api.retry" in context


def test_key_segment_match_makes_eligible() -> None:
    retry = _atom(
        "api.retry",
        "unrelated claim text without shared overlap words",
        key_files=("src/api/client.py",),
    )
    assert eligible("api migration", retry)


def test_path_component_match_makes_eligible() -> None:
    retry = _atom(
        "api.retry",
        "unrelated claim text without shared overlap words",
        key_files=("src/api/client.py",),
    )
    assert eligible("client module", retry)
