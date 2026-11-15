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


FROZEN_ATTACK_SEEDS = frozenset(range(141430000, 141430200))
FROZEN_NORMAL_SEEDS = frozenset(range(141420000, 141420200))


def validate_seed_rows(rows, expected_seeds) -> None:
    """Reject missing, duplicate, or unexpected rows before calculating rates."""
    seeds = [int(row["seed"]) for row in rows]
    if len(seeds) != len(expected_seeds) or set(seeds) != set(expected_seeds) or len(set(seeds)) != len(seeds):
        raise ValueError("main-case rows must contain each expected seed exactly once")


def evaluate_e2_count_gate(coverage_count: int, attack_nonzero_count: int,
                           normal_nonzero_count: int) -> E2Gate:
    """Apply the frozen 200-sample thresholds to aggregate counts only."""
    n = 200
    if any(not isinstance(value, int) or not 0 <= value <= n
           for value in (coverage_count, attack_nonzero_count, normal_nonzero_count)):
        raise ValueError("E2 counts must be integers in [0, 200]")
    lower_cov = cp_lower(coverage_count, n)
    lower_nonzero = cp_lower(attack_nonzero_count, n)
    upper_normal = cp_upper(normal_nonzero_count, n)
    return E2Gate(n, coverage_count, lower_cov, attack_nonzero_count,
                  lower_nonzero, n, normal_nonzero_count, upper_normal,
                  coverage_count >= 190 and lower_cov >= .90,
                  attack_nonzero_count >= 100 and lower_nonzero >= .40,
                  normal_nonzero_count <= 12 and upper_normal <= .10)


def count_e2_outcomes(attack_rows, normal_rows) -> tuple[int, int, int]:
    """Count every row; rejected or failed actions remain zero outcomes."""
    coverage = sum(bool(row["coverage_confirmed"]) for row in attack_rows)
    attack_nonzero = sum(float(row["set_action_norm"]) > 1e-12 for row in attack_rows)
    normal_nonzero = sum(float(row["set_action_norm"]) > 1e-12 for row in normal_rows)
    return coverage, attack_nonzero, normal_nonzero


def evaluate_e2_counts(attack_rows, normal_rows) -> E2Gate:
    """Evaluate only the frozen E2 seed sets; failed rows remain in denominators."""
    attack = [row for row in attack_rows if row["main_case"]]
    normal = [row for row in normal_rows if row["main_case"]]
    validate_seed_rows(attack, FROZEN_ATTACK_SEEDS)
    validate_seed_rows(normal, FROZEN_NORMAL_SEEDS)
    coverage, attack_nonzero, normal_nonzero = count_e2_outcomes(attack, normal)
    return evaluate_e2_count_gate(coverage, attack_nonzero, normal_nonzero)
