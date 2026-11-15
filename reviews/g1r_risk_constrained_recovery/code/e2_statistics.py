"""Frozen E2 count and one-sided Clopper-Pearson gate helpers."""
from __future__ import annotations
from dataclasses import dataclass
from scipy.optimize import brentq
from scipy.stats import beta, binom


def cp_lower(k: int, n: int, alpha: float = 0.05) -> float:
    if not (0 <= k <= n and n > 0 and 0.0 < alpha < 1.0):
        raise ValueError("invalid binomial count or alpha")
    return 0.0 if k == 0 else float(beta.ppf(alpha, k, n-k+1))


def cp_upper(k: int, n: int, alpha: float = 0.05) -> float:
    if not (0 <= k <= n and n > 0 and 0.0 < alpha < 1.0):
        raise ValueError("invalid binomial count or alpha")
    return 1.0 if k == n else float(beta.ppf(1.0-alpha, k+1, n-k))


def cp_lower_binomial_tail(k: int, n: int, alpha: float = 0.05) -> float:
    """Independent tail-equation formulation for cross-checking beta quantiles."""
    if k == 0:
        return 0.0
    return float(brentq(lambda p: binom.sf(k-1, n, p)-alpha,
                        0.0, 1.0, xtol=1e-14, rtol=1e-14))


def cp_upper_binomial_tail(k: int, n: int, alpha: float = 0.05) -> float:
    if k == n:
        return 1.0
    return float(brentq(lambda p: binom.cdf(k, n, p)-alpha,
                        0.0, 1.0, xtol=1e-14, rtol=1e-14))


@dataclass(frozen=True)
class E2Gate:
    n: int
    coverage_count: int
    coverage_lower_95: float
    nonzero_count: int
    nonzero_lower_95: float
    normal_n: int
    normal_nonzero_count: int
    normal_nonzero_upper_95: float
    coverage_pass: bool
    attack_nonzero_pass: bool
    normal_nonzero_pass: bool


def evaluate_e2_counts(attack_rows, normal_rows) -> E2Gate:
    """Use every row; failed construction/rejected actions count as false."""
    attack = [r for r in attack_rows if r["main_case"]]
    normal = [r for r in normal_rows if r["main_case"]]
    expected_attack = set(range(141430000, 141430200))
    expected_normal = set(range(141420000, 141420200))
    attack_seeds = [int(r["seed"]) for r in attack]
    normal_seeds = [int(r["seed"]) for r in normal]
    if len(attack) != 200 or set(attack_seeds) != expected_attack or len(set(attack_seeds)) != 200:
        raise ValueError("attack main-case rows must contain each frozen seed exactly once")
    if len(normal) != 200 or set(normal_seeds) != expected_normal or len(set(normal_seeds)) != 200:
        raise ValueError("normal main-case rows must contain each frozen seed exactly once")
    coverage = sum(bool(r["coverage_confirmed"]) for r in attack)
    nonzero = sum(float(r["set_action_norm"]) > 1e-12 for r in attack)
    normal_nonzero = sum(float(r["set_action_norm"]) > 1e-12 for r in normal)
    lower_cov = cp_lower(coverage, 200)
    lower_nonzero = cp_lower(nonzero, 200)
    upper_normal = cp_upper(normal_nonzero, 200)
    return E2Gate(200, coverage, lower_cov, nonzero, lower_nonzero,
                  200, normal_nonzero, upper_normal,
                  coverage >= 190 and lower_cov >= .90,
                  nonzero >= 100 and lower_nonzero >= .40,
                  normal_nonzero <= 12 and upper_normal <= .10)
