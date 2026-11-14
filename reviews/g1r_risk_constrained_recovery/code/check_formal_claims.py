"""Deterministic algebra and saved-matrix checks; no estimator or simulation."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
from pathlib import Path

import numpy as np
from scipy.stats import chi2

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parents[1]
OLD = ROOT / "reviews/cross_phase_identifiability_audit/results/c_phase_geometry_20261114_r01/pairwise_common_coordinates.npz"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False,
                                   allow_nan=False) + "\n", encoding="utf-8")


def main(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    plan = {
        "run_id": out.name,
        "baseline_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip(),
        "scope": "deterministic formulas and saved matrices only; no generated data, no detector prototype",
        "input_sha256": {str(OLD.relative_to(ROOT)): digest(OLD)},
        "source_sha256": digest(__file__),
        "python": platform.python_version(),
        "d": 216, "target_state_index": 217, "gap": 8,
        "eligible_rule": "q=r+8 < d",
        "common_post_cache_times": [211, 212, 213, 214, 215, 216],
        "beta_parameter_family": 0.05,
        "parameter_family_threshold": "chi2_2 quantile 1-beta/M; exact known healthy covariance only",
        "rank_tolerance": 1e-10,
        "random_seed": None, "new_trajectories": 0,
    }
    write_json(out / "frozen_plan.json", plan)

    # These are counterexamples to mathematical implications, not Yang scenarios.
    examples = {
        "unconstrained_radius_used_after_cap": {
            "D": [10.0], "cap": 1.0, "unconstrained_radius": 0.0,
            "feasible_center": 1.0, "actual_residual": 9.0,
        },
        "chebyshev_does_not_minimize_loss_increment": {
            "D_interval": [1.0, 10.0], "true_delta": 1.0,
            "healthy_error": 0.0, "center": 5.5,
            "uncorrected_squared_error": 1.0, "corrected_squared_error": 20.25,
        },
        "small_set_can_still_hurt_true_MSE": {
            "D_interval": [1.0, 1.2], "true_delta": 1.0,
            "healthy_error": -1.0, "center": 1.1,
            "radius": 0.1, "uncorrected_squared_error": 0.0,
            "corrected_squared_error": 1.21,
        },
        "distance_to_set_is_not_distance_to_convex_hull": {
            "D": [-2.0, 2.0], "distance_to_D": 2.0,
            "distance_to_conv_D": 0.0, "nonzero_uniformly_safe_action": False,
        },
        "finite_second_moment_does_not_give_pathwise_error_bound": {
            "probability_large_error": 0.01, "large_error_magnitude": 10.0,
            "second_moment": 1.0, "sqrt_second_moment": 1.0,
            "large_error_exceeds_sqrt_second_moment": True,
        },
    }
    assert examples["unconstrained_radius_used_after_cap"]["actual_residual"] > 0
    assert 20.25 > 1.0 and np.isclose((-1.1) ** 2, 1.21)

    # Exact 1D extrema validate the robust loss formula, including abstention.
    robust = []
    for lo, hi, B, U in [(1., 10., 0., 20.), (1., 1.2, 1., 20.),
                           (2., 3., .5, .7), (-2., 2., 0., 20.)]:
        p = lo if lo > 0 else hi if hi < 0 else 0.
        m = abs(p)
        u = np.sign(p) * min(U, max(m - B, 0.))
        worst = max(u*u - 2*(delta + e)*u
                    for delta in (lo, hi) for e in (-B, B))
        assert worst <= 1e-12
        robust.append({"D_interval": [lo, hi], "B": B, "cap": U,
                       "projection": p, "action": float(u),
                       "exact_worst_loss_increment": float(worst)})

    rows = []
    with np.load(OLD, allow_pickle=False) as data:
        events = data["events"]
        eligible = np.flatnonzero(events[:, 1] + 8 < 216)
        keep_times = data["times_P"] > int(np.max(events[eligible, 1] + 8))
        indices = np.flatnonzero(np.repeat(keep_times, 2))
        assert data["times_P"][keep_times].tolist() == plan["common_post_cache_times"]
        cov = data["Sigma"][16:, 16:][np.ix_(indices, indices)]
        L = np.linalg.cholesky(cov)
        threshold = float(chi2.ppf(1 - .05 / len(eligible), 2))
        for j in eligible:
            edge, r = map(int, events[j])
            O = data["O_P"][j, indices]
            G = data["G_dplus1"][j]
            white = np.linalg.solve(L, O)
            sv = np.linalg.svd(white, compute_uv=False)
            rank = int(np.sum(sv > 1e-10))
            assert rank == 2
            Vtheta = np.linalg.solve(white.T @ white, np.eye(2))
            Vdelta = G @ Vtheta @ G.T
            eigen = np.linalg.eigvalsh((Vdelta + Vdelta.T) / 2)
            rows.append({"edge": edge, "r": r, "q": r+8, "rank_white": rank,
                         "white_min_singular": float(sv[-1]),
                         "effect_error_covariance": Vdelta.tolist(),
                         "ellipsoid_outer_radius_at_family_beta": float(np.sqrt(threshold*eigen[-1])),
                         "zero_noise_assumed": False})

    alpha, Pbar, Rmax = .05, 1., .01
    U = (np.sqrt(Pbar+Rmax)-np.sqrt(Pbar)) / np.sqrt(alpha)
    bound = alpha*U*U+2*U*np.sqrt(alpha*Pbar)
    assert np.isclose(bound, Rmax)
    write_json(out / "checks.json", {
        "counterexamples": examples, "exact_1d_robust_checks": robust,
        "eligible_count": len(rows), "saved_matrix_geometry": rows,
        "parameter_family_chi_square_threshold": threshold,
        "normal_risk_budget_illustration_only": {
            "alpha": alpha, "Pbar": Pbar, "Rmax": Rmax,
            "U": float(U), "bound": float(bound), "not_a_frozen_method_parameter": True},
        "interpretation": [
            "Radii are unconditional known-event estimation-error scales with a finite-family union bound.",
            "No observed centers, event selection, union diameter, coverage, acceptance rate or MSE was evaluated.",
            "No data were generated and no extra seed was used.",
            "The exact 1D examples are mathematical counterexamples, not evidence of failure on the five-node model.",
        ],
    })
    print(json.dumps({"run_id": out.name, "checks": "PASS", "eligible_events": len(rows),
                      "new_trajectories": 0}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    main(parser.parse_args().out)
