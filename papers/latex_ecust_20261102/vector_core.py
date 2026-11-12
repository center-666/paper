"""Exploratory floating-point, coupled vector event-tree calculation.

This file is self-contained (Python + numpy). No parameter search, optimization,
Monte Carlo, matrix-label merging, or continuous-payload TV is performed.
The parameters below are fixed before execution. All data stay in this branch.
"""
from __future__ import annotations

import csv
import hashlib
import itertools
import json
from pathlib import Path
import sys

import numpy as np
from numpy.polynomial.hermite import hermgauss

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
PARAMETERS = {
    "protocol": "C=I; trusted actual-prediction feedback and event bit; after-send payload attack",
    "target_time_k": 4,
    "peak_norm": "Euclidean",
    "amplitudes": [0.025, 0.05, 0.1, 0.2],
    "policies": ["persistent_fixed_direction", "target_rademacher"],
    "quadrature_orders": [24, 40],
    "cases": {
        "coupled_2d_stable": {
            "A": [[0.82, 0.18], [-0.10, 0.72]],
            "P0": [[0.8, 0.12], [0.12, 0.6]],
            "Q": [[0.05, 0.01], [0.01, 0.04]],
            "R": [[0.2, 0.03], [0.03, 0.3]],
            "Z": [[2.0, 0.25], [0.25, 1.5]],
            "direction": [1.0, -1.0],
            "quadrature_bias": [0.13, -0.17],
        },
        "coupled_3d_unstable": {
            "A": [[1.04, 0.12, 0.0], [0.0, 0.91, 0.08], [0.03, 0.0, 0.86]],
            "P0": [[0.8, 0.12, 0.04], [0.12, 0.6, 0.07], [0.04, 0.07, 0.7]],
            "Q": [[0.05, 0.01, 0.0], [0.01, 0.04, 0.005], [0.0, 0.005, 0.06]],
            "R": [[0.2, 0.03, 0.01], [0.03, 0.3, 0.02], [0.01, 0.02, 0.25]],
            "Z": [[2.0, 0.25, 0.10], [0.25, 1.5, 0.15], [0.10, 0.15, 1.8]],
            "direction": [1.0, -1.0, 1.0],
            "quadrature_bias": [0.13, -0.17, 0.09],
        },
    },
}


def sym(x):
    return (x + x.T) / 2


def arr(model):
    return {key: np.asarray(value, dtype=float) for key, value in model.items()}


def covariance_update(P, noise):
    K = np.linalg.solve((P + noise).T, P.T).T  # P(P+noise)^-1; preserve order.
    post = sym(P - K @ P)
    alternative = np.linalg.inv(np.linalg.inv(P) + np.linalg.inv(noise))
    return K, post, float(np.linalg.norm(post - alternative, ord="fro"))


def silence(P, d, R, Z):
    S = P + R
    L = S + np.linalg.inv(Z)
    sign1, logdet1 = np.linalg.slogdet(Z)
    sign2, logdet2 = np.linalg.slogdet(L)
    assert sign1 == sign2 == 1
    base = float(np.exp(-0.5 * (logdet1 + logdet2)))
    exponent = float(0.5 * d @ np.linalg.solve(L, d))
    return base * float(np.exp(-exponent)), base, exponent


def run_tree(model, k, b, policy):
    A, P0, Q, R, Z = (model[key] for key in ["A", "P0", "Q", "R", "Z"])
    n = len(P0)
    direction = model["direction"] / np.linalg.norm(model["direction"])
    Rs = R + np.linalg.inv(Z)
    signs = [-1.0, 1.0] if policy in ("target_rademacher", "compensated_rademacher") else [1.0]
    # Node = (probability, P_t^-, d_t, event tuple, private sign).
    nodes = [(1 / len(signs), P0.copy(), np.zeros(n), (), s) for s in signs]
    target_nodes = []
    masses = []
    max_peak = 0.0
    max_cov_identity_residual = 0.0
    min_cov_eigenvalue = float("inf")
    max_gain_asymmetry = 0.0
    max_silent_shrink_spectral_norm = 0.0
    for t in range(k + 2):
        next_nodes = []
        for mass, P, d, history, s in nodes:
            qs, _, _ = silence(P, d, R, Z)
            for gamma, p in [(0, qs), (1, 1 - qs)]:
                K, Pplus, resid = covariance_update(P, R if gamma else Rs)
                attack = np.zeros(n)
                if gamma and ((policy == "persistent_fixed_direction" and t <= k)
                              or (policy in ("target_rademacher", "compensated_rademacher") and t == k)):
                    attack = s * b * direction
                if gamma and policy == "compensated_rademacher" and t == k + 1:
                    attack = -d
                D = (np.eye(n) - K) @ d - K @ attack if gamma else (np.eye(n) - K) @ d
                next_history = history + (gamma,)
                new_mass = mass * p
                max_peak = max(max_peak, float(np.linalg.norm(attack)))
                max_cov_identity_residual = max(max_cov_identity_residual, resid)
                min_cov_eigenvalue = min(min_cov_eigenvalue, float(np.linalg.eigvalsh(Pplus).min()))
                max_gain_asymmetry = max(max_gain_asymmetry, float(np.linalg.norm(K - K.T, ord="fro")))
                if not gamma:
                    max_silent_shrink_spectral_norm = max(max_silent_shrink_spectral_norm,
                                                         float(np.linalg.norm(np.eye(n) - K, ord=2)))
                if t == k:
                    target_nodes.append((new_mass, Pplus, D, next_history))
                next_nodes.append((new_mass, sym(A @ Pplus @ A.T + Q), A @ D, next_history, s))
        nodes = next_nodes
        masses.append(float(sum(row[0] for row in nodes)))
    bits = {}
    for mass, _, _, history, _ in nodes:
        bits[history] = bits.get(history, 0.0) + mass  # marginalize private seed.
    e_bias2 = sum(p * float(D @ D) for p, P, D, h in target_nodes)
    e_trace = sum(p * float(np.trace(P)) for p, P, D, h in target_nodes)
    ew_record = 0.0
    e_exp = 0.0
    covariance_by_history = {}
    for mass, P, D, history in target_nodes:
        _, base, exponent = silence(A @ P @ A.T + Q, A @ D, R, Z)
        e_exp += mass * np.exp(-exponent)
        covariance_by_history[history] = P
    # Independent aggregation route over the full event-word distribution.
    for history, mass in bits.items():
        if history[-1] == 0:
            P = covariance_by_history[history[:-1]]
            _, base, _ = silence(A @ P @ A.T + Q, np.zeros(n), R, Z)
            ew_record += mass / base
    diagnostics = {
        "probability_mass_error": max(abs(p - 1) for p in masses),
        "peak_attack_norm": max_peak,
        "covariance_identity_max_residual_fro": max_cov_identity_residual,
        "minimum_posterior_covariance_eigenvalue": min_cov_eigenvalue,
        "gain_asymmetry_max_fro": max_gain_asymmetry,
        "silent_I_minus_K_max_spectral_norm": max_silent_shrink_spectral_norm,
        "witness_residual": float(abs(ew_record - e_exp)),
    }
    return {
        "bits": bits, "target_nodes": target_nodes,
        "e_bias2": float(e_bias2), "e_trace": float(e_trace),
        "ew_record": float(ew_record), "e_exp": float(e_exp),
        "diagnostics": diagnostics,
    }


def quadrature_check(model, order):
    """Independent integration over x; sensor noise is integrated analytically."""
    P, R, Z, d = (model[key] for key in ["P0", "R", "Z", "quadrature_bias"])
    n = len(d)
    nodes, weights = hermgauss(order)
    grid = np.asarray(list(itertools.product(range(order), repeat=n)), dtype=int)
    x = d + np.sqrt(2.0) * nodes[grid] @ np.linalg.cholesky(P).T
    wx = np.prod(weights[grid] / np.sqrt(np.pi), axis=1)
    Rs = R + np.linalg.inv(Z)
    sign, logdet = np.linalg.slogdet(np.eye(n) + R @ Z)
    assert sign == 1
    likelihood = np.exp(-0.5 * logdet - 0.5 * np.einsum("ni,ij,nj->n", x, np.linalg.inv(Rs), x))
    joint_weight = wx * likelihood
    qs = float(joint_weight.sum())
    mean = np.einsum("n,ni->i", joint_weight, x) / qs
    centered = x - mean
    cov = np.einsum("n,ni,nj->ij", joint_weight, centered, centered) / qs
    K, Pplus, _ = covariance_update(P, Rs)
    target_mean = (np.eye(n) - K) @ d
    target_qs = silence(P, d, R, Z)[0]
    return {
        "order_per_dimension": order, "quadrature_points": int(order ** n),
        "silence_probability_quadrature": qs, "silence_probability_formula": target_qs,
        "silence_probability_abs_error": abs(qs - target_qs),
        "silent_mean_error_2norm": float(np.linalg.norm(mean - target_mean)),
        "silent_covariance_error_fro": float(np.linalg.norm(cov - Pplus, ord="fro")),
    }


def main():
    DATA.mkdir(exist_ok=True)
    parameters_text = json.dumps(PARAMETERS, ensure_ascii=False, indent=2) + "\n"
    (DATA / "parameters.json").write_text(parameters_text, encoding="utf-8")
    rows, cases = [], {}
    k = PARAMETERS["target_time_k"]
    for name, raw in PARAMETERS["cases"].items():
        model = arr(raw)
        n = len(model["P0"])
        for key in ["P0", "Q", "R", "Z"]:
            assert np.linalg.eigvalsh(model[key]).min() > 0
        assert abs(np.linalg.det(model["A"])) > 1e-10
        assert np.linalg.norm(model["A"] - np.diag(np.diag(model["A"]))) > 0.1
        healthy = run_tree(model, k, 0.0, "healthy")
        target = healthy["target_nodes"]
        Ps = [row[1] for row in target]
        minimum_pair_distance = min(np.linalg.norm(P1 - P2, ord="fro")
                                    for i, P1 in enumerate(Ps) for P2 in Ps[i + 1:])
        eigenvalues = np.linalg.eigvals(model["A"])
        case = {
            "dimension": n,
            "A_eigenvalues_real_imag": [[float(v.real), float(v.imag)] for v in eigenvalues],
            "spectral_radius_A": float(max(abs(eigenvalues))),
            "minimum_singular_value_A": float(np.linalg.svd(model["A"], compute_uv=False).min()),
            "commutator_P0_R_fro": float(np.linalg.norm(model["P0"] @ model["R"] - model["R"] @ model["P0"], ord="fro")),
            "commutator_P0_Z_fro": float(np.linalg.norm(model["P0"] @ model["Z"] - model["Z"] @ model["P0"], ord="fro")),
            "event_histories_to_k": len(Ps),
            "covariance_pair_min_distance_fro_diagnostic_only": float(minimum_pair_distance),
            "covariance_label_injectivity_proved": False,
            "healthy_witness_expectation": healthy["ew_record"],
            "healthy_mse": healthy["e_trace"],
            "quadrature_checks": [quadrature_check(model, order) for order in PARAMETERS["quadrature_orders"]],
            "policies": [],
        }
        for policy in PARAMETERS["policies"]:
            for b in PARAMETERS["amplitudes"]:
                attack = run_tree(model, k, b, policy)
                tv = 0.5 * sum(abs(attack["bits"][h] - healthy["bits"][h]) for h in healthy["bits"])
                covariance_change = attack["e_trace"] - healthy["e_trace"]
                J = attack["e_bias2"] + covariance_change
                row = {
                    "case": name, "dimension": n, "policy": policy, "k": k, "b": b,
                    "bias_squared_expectation": attack["e_bias2"],
                    "covariance_trace_change": covariance_change,
                    "true_mse_damage_J": J,
                    "event_word_tv_0_to_k_plus_1": float(tv),
                    "J_over_b_squared": J / b ** 2,
                    "event_tv_over_b_squared": float(tv) / b ** 2,
                    "witness_gap": healthy["ew_record"] - attack["ew_record"],
                    "witness_exp_gap": 1 - attack["e_exp"],
                    **attack["diagnostics"],
                }
                assert row["probability_mass_error"] < 1e-12
                assert row["peak_attack_norm"] <= b * (1 + 1e-12)
                assert row["covariance_identity_max_residual_fro"] < 1e-12
                assert row["witness_residual"] < 1e-12
                if policy == "target_rademacher":
                    assert abs(covariance_change) < 1e-12
                rows.append(row)
                case["policies"].append(row)
        assert case["quadrature_checks"][-1]["silent_covariance_error_fro"] < 1e-9
        cases[name] = case
    results = {
        "status": "exploratory_floating_point_checks_passed",
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "parameters_sha256": hashlib.sha256((DATA / "parameters.json").read_bytes()).hexdigest(),
        "python": sys.version, "numpy": np.__version__,
        "limitations": [
            "Finite event trees for two fixed, coupled full-state observation models only.",
            "Floating-point checks, not a rigorous interval certificate or proof of vector theorems.",
            "Only full event-word TV is computed; continuous-payload joint-log TV is not computed.",
            "No claim that covariance labels are injective; floating-point distances are diagnostic.",
            "No optimization over attacks; no transfer of scalar optimal binary certificates.",
            "Target policy uses one fair private sign at k; no k+1 compensation is used in this event-only experiment.",
        ],
        "cases": cases,
    }
    (DATA / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (DATA / "results.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"status": results["status"], "rows": len(rows),
                      "cases": {name: {"rho_A": val["spectral_radius_A"], "healthy_mse": val["healthy_mse"],
                                       "quadrature_error": val["quadrature_checks"][-1]["silent_covariance_error_fro"]}
                                for name, val in cases.items()}}, indent=2))


if __name__ == "__main__":
    main()
