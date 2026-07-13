"""Pattern outcome statistics — Beta–Bernoulli adjudication (patterns-only)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum


class Tier(str, Enum):
    """Epistemic tier for a semantic pattern."""

    HINT = "hint"
    RULE = "rule"


@dataclass(frozen=True)
class PatternStats:
    """Own-evidence Beta posterior state for one pattern atom."""

    alpha_own: float
    beta_own: float
    tier: Tier = Tier.HINT

    @staticmethod
    def jeffreys_prior() -> PatternStats:
        """Uninformative prior for legacy atoms without stats."""
        return PatternStats(alpha_own=0.5, beta_own=0.5, tier=Tier.HINT)

    @property
    def mean(self) -> float:
        total = self.alpha_own + self.beta_own
        if total <= 0:
            return 0.0
        return self.alpha_own / total

    @property
    def lcb05(self) -> float:
        return beta_lcb05(self.alpha_own, self.beta_own)

    @property
    def trial_count(self) -> float:
        return self.alpha_own + self.beta_own


def beta_lcb05(alpha: float, beta: float) -> float:
    """5th percentile of Beta(α, β) — normal approximation, scipy-free."""
    a = max(alpha, 1e-9)
    b = max(beta, 1e-9)
    total = a + b
    mean = a / total
    variance = (a * b) / (total * total * (total + 1.0))
    if variance <= 0:
        return mean
    z = 1.645
    approx = mean - z * math.sqrt(variance)
    return max(0.0, min(mean, approx))


@dataclass(frozen=True)
class AdjudicationParams:
    """Tunable thresholds from consolidation-adjudication-design.md §10."""

    n_rule: float = 3.0
    theta_star: float = 0.6
    theta_floor: float = 0.3
    w_cross: float = 0.5
    decay: float = 0.95


DEFAULT_ADJUDICATION_PARAMS = AdjudicationParams()


def tier_from_stats(stats: PatternStats, *, params: AdjudicationParams = DEFAULT_ADJUDICATION_PARAMS) -> Tier:
    """Promote to rule when own evidence clears LCB bar."""
    if stats.trial_count < params.n_rule:
        return Tier.HINT
    if stats.lcb05 > params.theta_star:
        return Tier.RULE
    return Tier.HINT


def is_success_outcome(outcome: str) -> bool:
    return outcome == "done"
