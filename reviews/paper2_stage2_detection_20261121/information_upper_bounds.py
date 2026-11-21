"""Analytic event-record information bounds and offline confidence helpers.

No random numbers are generated. This does not edit frozen simulation inputs.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent


def riccati_root(A: float, Q: float, observation_variance: float) -> float:
    c = observation_variance - Q - A * A * observation_variance
    return (-c + math.sqrt(c * c + 4 * Q * observation_variance)) / 2


def analytic_bounds(model: dict, b: float) -> dict:
    A, Q, R, P0, Z, delta = (model[k] for k in ("A", "Q", "R", "P0", "Z", "delta"))
    r0 = R + 1 / Z
    p_lo = riccati_root(A, Q, R)
    p_hi = max(P0, riccati_root(A, Q, r0))
    if not P0 >= p_lo:
        raise ValueError("The stated Riccati invariant interval does not cover P0")
    k_lo, k_hi = p_lo / (p_lo + R), p_hi / (p_hi + R)
    silent_contraction = A * r0 / (p_lo + r0)
    if not (A > 0 and silent_contraction < 1 and 1 - A * (1 - k_lo) > 0):
        raise ValueError("The stated sharp bias invariant does not apply")
    extremal_k = k_hi if A <= 1 else k_lo
    bias_multiplier = extremal_k / (1 - A * (1 - extremal_k))
    B = b * bias_multiplier
    Ppost_lo = R * k_lo
    Ppost_hi = p_hi * r0 / (p_hi + r0)
    V_lo = 1 / Z + A * A * Ppost_lo + Q + R
    V_hi = 1 / Z + A * A * Ppost_hi + Q + R
    nu_hi = 1 / math.sqrt(Z * V_lo)
    nu_lo = math.exp(-delta * delta / (2 * V_lo)) / math.sqrt(Z * V_hi)
    eta = (A * B) ** 2 / (2 * V_lo)
    fractional_gap = -math.expm1(-eta)
    chi_square_upper = nu_hi / (1 - nu_hi) * fractional_gap ** 2
    extremal_p = nu_hi * math.exp(-eta)
    info_upper = (extremal_p * math.log1p((extremal_p - nu_hi) / nu_hi) +
                  (1 - extremal_p) * math.log1p((nu_hi - extremal_p) / (1 - nu_hi)))
    coefficient_b4 = nu_hi / (1 - nu_hi) * (A * bias_multiplier) ** 4 / (4 * V_lo * V_lo)
    # Check the invariant at both endpoints; r(K) is monotone.
    for gain in (k_lo, k_hi):
        if A * (1 - gain) * B + gain * b > B * (1 + 2e-14):
            raise AssertionError("Send invariant failed")
    if not (0 < nu_lo <= nu_hi < 1):
        raise AssertionError("Invalid null probability bounds")
    return {
        "model": model["id"], "attack_strength": b,
        "prior_variance_lower": p_lo, "prior_variance_upper": p_hi,
        "send_gain_lower": k_lo, "send_gain_upper": k_hi,
        "silent_contraction_upper": silent_contraction,
        "extremal_gain_for_bias_invariant": extremal_k,
        "sharp_bias_multiplier": bias_multiplier,
        "analysis_bias_absolute_upper": B,
        "kernel_V_lower_all_events": V_lo, "kernel_V_upper_all_events": V_hi,
        "nu_lower_all_events": nu_lo, "nu_upper_all_events": nu_hi,
        "eta_upper": eta, "relative_silence_gap_upper": fractional_gap,
        "absolute_silence_gap_upper": nu_hi * fractional_gap,
        "conditional_Bernoulli_KL_upper_per_step": info_upper,
        "conditional_Bernoulli_chi_square_upper_per_step": chi_square_upper,
        "conditional_KL_b4_upper_coefficient": coefficient_b4,
    }


def empirical_bernstein_upper(moment: dict, range_upper: float, failure_probability: float) -> dict:
    """One-sided empirical Bernstein for iid X in [0, range_upper].

    Uses the unbiased sample variance and the standard 7/3 finite-sample term.
    The caller must explicitly budget multiplicity across any family of cells.
    """
    n = int(moment["n"])
    if n < 2 or not 0 < failure_probability < 1 or range_upper < 0:
        raise ValueError("Invalid empirical Bernstein inputs")
    mean = float(moment["sum"]) / n
    sample_variance = max(0.0, (float(moment["sum_squares"]) - n * mean * mean) / (n - 1))
    if not -1e-12 <= mean <= range_upper + 1e-12:
        raise AssertionError("Observed mean violates the proved bounded range")
    if n > 1 and sample_variance > n / (n - 1) * range_upper * range_upper / 4 * (1 + 1e-10):
        raise AssertionError("Observed variance violates the proved bounded range")
    z = math.log(2 / failure_probability)
    radius = math.sqrt(2 * sample_variance * z / n) + 7 * range_upper * z / (3 * (n - 1))
    upper = min(range_upper, max(0.0, mean + radius))
    return {
        "n": n, "sample_mean_conditional_KL_sum": mean,
        "sample_variance_conditional_KL_sum": sample_variance,
        "proved_sample_range_upper": range_upper,
        "failure_probability": failure_probability,
        "empirical_Bernstein_radius": radius,
        "population_event_record_KL_upper": upper,
    }


def binary_power_upper(record_KL_upper: float, false_alarm_budget: float) -> float:
    """Invert binary data processing: kl(power || alpha) <= record KL."""
    alpha = false_alarm_budget
    if not 0 < alpha < 1 or record_KL_upper < 0:
        raise ValueError("Invalid information/testing parameters")
    if record_KL_upper >= math.log(1 / alpha):
        return 1.0
    lo, hi = alpha, 1.0
    for _ in range(80):
        p = (lo + hi) / 2
        divergence = p * math.log(p / alpha) + (1 - p) * math.log((1 - p) / (1 - alpha))
        if divergence > record_KL_upper:
            hi = p
        else:
            lo = p
    return hi


def infer_event_power_upper(moment: dict, model: dict, b: float, horizon: int,
                           false_alarm_budget: float = 0.01,
                           confidence_failure: float = 0.05 / 72) -> dict:
    bounds = analytic_bounds(model, b)
    result = empirical_bernstein_upper(
        moment, horizon * bounds["conditional_Bernoulli_KL_upper_per_step"], confidence_failure)
    result.update({
        "false_alarm_budget": false_alarm_budget,
        "horizon": horizon, "model": model["id"], "attack_strength": b,
        "event_only_detection_probability_upper": min(
            1.0, false_alarm_budget + math.sqrt(result["population_event_record_KL_upper"] / 2)),
        "binary_data_processing_detection_probability_upper": binary_power_upper(
            result["population_event_record_KL_upper"], false_alarm_budget),
        "scope": "Any detector measurable from event history and deterministic covariance labels; not payload/phase logs.",
    })
    return result


def main() -> None:
    protocol = json.loads((HERE / "protocol.json").read_text(encoding="utf8"))
    rows = []
    for model in protocol["models"]:
        for b in protocol["attack_strengths"]:
            row = analytic_bounds(model, b)
            per_step = row["conditional_Bernoulli_KL_upper_per_step"]
            row["horizon_bounds"] = {
                str(H): {
                    "event_record_KL_upper": H * per_step,
                    "event_only_detection_probability_upper": min(
                        1.0, protocol["alpha"] + math.sqrt(H * per_step / 2)),
                    "binary_data_processing_detection_probability_upper": binary_power_upper(
                        H * per_step, protocol["alpha"]),
                }
                for H in protocol["horizons_after_onset"]
            }
            target_power = 0.8
            Cb4 = row["conditional_KL_b4_upper_coefficient"] * b ** 4
            required_kl = target_power * math.log(target_power / protocol["alpha"]) + (
                1 - target_power) * math.log((1 - target_power) / (1 - protocol["alpha"]))
            row["target_power"] = target_power
            row["necessary_horizon_b4_Pinsker"] = 2 * (target_power - protocol["alpha"]) ** 2 / Cb4
            row["necessary_horizon_b4_binary_data_processing"] = required_kl / Cb4
            row["necessary_horizon_exact_kernel_bound_binary_data_processing"] = required_kl / per_step
            rows.append(row)
    # Check a rectangle containing all admissible posterior variances/biases.
    # The proof, not these mesh extrema, certifies the continuous domain.
    grid_checks = []
    for row in rows:
        model = next(m for m in protocol["models"] if m["id"] == row["model"])
        delta, A, Z = model["delta"], model["A"], model["Z"]
        numeric_max_KL = 0.0
        for iv in range(81):
            V = row["kernel_V_lower_all_events"] + iv / 80 * (
                row["kernel_V_upper_all_events"] - row["kernel_V_lower_all_events"])
            root = math.sqrt(2 * V)
            coeff = math.sqrt(2 * math.pi / Z) / (4 * delta)
            nu = coeff * (math.erf(delta / root) - math.erf(-delta / root))
            for ib in range(51):
                displacement = A * row["analysis_bias_absolute_upper"] * ib / 50
                p = coeff * (math.erf((delta - displacement) / root) -
                             math.erf((-delta - displacement) / root))
                KL = p * math.log1p((p - nu) / nu) + (1 - p) * math.log1p((nu - p) / (1 - nu))
                numeric_max_KL = max(numeric_max_KL, KL)
                if KL > row["conditional_Bernoulli_KL_upper_per_step"] + 1e-13:
                    raise AssertionError("Phase-integrated grid value exceeds analytical KL envelope")
        grid_checks.append({"model": row["model"], "attack_strength": row["attack_strength"],
                            "max_numeric_grid_KL": numeric_max_KL,
                            "proved_KL_upper": row["conditional_Bernoulli_KL_upper_per_step"],
                            "status": "PASS"})
    # Purely synthetic bounded moments exercise the confidence helper.
    values = (0.0, 0.25, 0.5, 0.75, 1.0)
    synthetic = {"n": len(values), "sum": sum(values), "sum_squares": sum(x * x for x in values)}
    check = empirical_bernstein_upper(synthetic, 1.0, 0.05)
    if not check["population_event_record_KL_upper"] == 1.0:
        raise AssertionError("Small-sample range clipping check failed")
    output = {
        "base_commit": "8cf49e73", "performance_random_samples_generated": False,
        "input_protocol_sha256": hashlib.sha256((HERE / "protocol.json").read_bytes()).hexdigest(),
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "purpose": "Analytic upper bounds for event-only detection, plus offline confidence helpers.",
        "rows": rows,
        "confidence_method": "One-sided empirical Bernstein, family failure 0.05 split across 24 cases x 3 horizons.",
        "upper_bound_is_not_for_richer_logs": True,
        "numerical_checks_not_global_optimization": grid_checks,
        "deterministic_check": {"status": "PASS", "synthetic_bounded_moments": check},
    }
    (HERE / "information_upper_constants.json").write_text(
        json.dumps(output, indent=2, allow_nan=False) + "\n", encoding="utf8")
    for row in rows:
        print(row["model"], row["attack_strength"], "B/b", row["sharp_bias_multiplier"],
              "I_upper", row["conditional_Bernoulli_KL_upper_per_step"],
              "power_upper_2048", row["horizon_bounds"]["2048"]["event_only_detection_probability_upper"])


if __name__ == "__main__":
    main()
