"""Independent exhaustive finite-tree checks of online detector recurrences."""
from __future__ import annotations

import itertools
import json
import math
from pathlib import Path

import numpy as np

from core import Detectors

HERE = Path(__file__).resolve().parent


def main() -> None:
    depth, alpha = 8, 0.4
    strengths, weights = (0.05, 0.1, 0.25), (0.2, 0.3, 0.5)
    expectations = np.zeros((depth, 3))
    rejection_probabilities = np.zeros(5)
    probability_sum = 0.0
    max_recurrence_error = 0.0
    for bits in itertools.product((0, 1), repeat=depth):
        d = Detectors(1, strengths, weights, alpha, depth)
        prefix_probability = 1.0
        lrs = np.ones((depth, 3))
        reference_prefix_stats = []
        for index, bit in enumerate(bits):
            n = index + 1
            # Predictable history dependence deliberately exercises the
            # non-iid case. This is a synthetic binary tree, not a trajectory.
            nu = 0.65 + 0.1 * (bits[index - 1] if index else 0)
            q = np.array([nu - 0.02, nu - 0.06, nu - 0.15])
            factor = q / nu if bit else (1 - q) / (1 - nu)
            lrs[:n] *= factor
            explicit_fixed = lrs[0, 1]
            explicit_strength = float(lrs[0] @ weights)
            start_weights = np.array([1 / (k * (k + 1)) for k in range(1, n + 1)])
            explicit_start = float(start_weights @ (lrs[:n] @ weights)) + 1 / (n + 1)
            explicit_cusum = float(np.max(lrs[:n], axis=0) @ weights) / depth
            d.step(n, np.array([bool(bit)]), np.array([nu]), q[:, None])
            actual = np.exp(d.last_statistics[1:, 0] * math.log(1 / alpha))
            expected = np.array([explicit_fixed, explicit_strength, explicit_start, explicit_cusum])
            max_recurrence_error = max(max_recurrence_error, float(np.max(np.abs(actual - expected))))
            prefix_probability *= nu if bit else (1 - nu)
            reference_prefix_stats.append((prefix_probability, expected[:3].copy()))
        probability_sum += prefix_probability
        rejection_probabilities += prefix_probability * (d.tau[:, 0] >= 0)
        # Each n-prefix occurs 2^(depth-n) times in the complete enumeration.
        for index, (prefix_probability_n, values) in enumerate(reference_prefix_stats):
            expectations[index] += prefix_probability_n * values / (2 ** (depth - index - 1))
    if abs(probability_sum - 1) > 1e-12:
        raise AssertionError("Health binary tree is not normalized")
    if not np.allclose(expectations, 1, rtol=0, atol=3e-14):
        raise AssertionError("Fixed/strength/start mixture has nonunit null expectation")
    if max_recurrence_error > 3e-13:
        raise AssertionError("Online recurrence disagrees with explicit component calculation")
    if np.max(rejection_probabilities) > alpha + 1e-14:
        raise AssertionError("Finite tree false-alarm probability exceeds declared budget")
    result = {"status": "PASS", "performance_random_samples_generated": False,
              "tree_depth": depth, "enumerated_leaves": 2 ** depth,
              "synthetic_health_alpha": alpha, "tree_total_probability": probability_sum,
              "null_expectations_D1_D2_D3_by_time": expectations.tolist(),
              "false_alarm_probabilities_D0_through_D4": rejection_probabilities.tolist(),
              "maximum_recurrence_error": max_recurrence_error,
              "scope": "Exhaustive predictable Bernoulli fixtures; not Monte Carlo performance data."}
    (HERE / "detector_enumeration_checks.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf8")
    print(json.dumps({"status": "PASS", "enumerated_leaves": 2 ** depth,
                      "maximum_recurrence_error": max_recurrence_error}))


if __name__ == "__main__":
    main()
