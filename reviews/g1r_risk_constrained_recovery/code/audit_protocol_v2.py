"""Task 4 design audit only. No deployed policies, RNG, or E2/E3 data.

Checks frozen inputs, numerical risk margin, and fixed mathematical examples.
Refuses to overwrite an existing run, including a failed run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import time

import numpy as np
from scipy.special import erfc
from scipy.stats import beta, chi2


ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "reviews/g1r_risk_constrained_recovery"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8", newline="\n")


def fixed_examples():
    """Finite hand-checkable examples; not a new policy implementation."""
    points = np.array([[-2., 0.], [2., 0.]])
    center = np.zeros(2)
    assert np.max(np.sum((points - center) ** 2, axis=1)) == 4.
    assert np.linalg.norm(points.mean(axis=0)) == 0.
    for u in [np.array([.1, .2]), np.array([-.3, .1]), np.zeros(2)]:
        f = np.max(np.sum((points - u) ** 2, axis=1))
        assert f - 4. >= np.dot(u, u) - 1e-14

    # A single farthest point produces a tight dual bound under an active cap.
    capped_points = np.array([[2., 0.], [4., 0.]])
    weights = np.array([0., 1.])
    mean = weights @ capped_points
    cap = .5
    u = cap * mean / np.linalg.norm(mean)
    dual = (weights @ np.sum(capped_points ** 2, axis=1)
            - np.dot(mean, mean) + max(np.linalg.norm(mean) - cap, 0.) ** 2)
    upper = np.max(np.sum((capped_points - u) ** 2, axis=1))
    assert dual == upper == 12.25

    Q = np.diag([4., 1.])
    b = np.zeros(2)
    lam = 4. + 1e-8
    trust_upper = lam + b @ np.linalg.solve(lam * np.eye(2) - Q, b)
    trust_lower = np.array([1., 0.]) @ Q @ np.array([1., 0.])
    assert trust_lower == 4. and 0. < trust_upper - trust_lower < 1.1e-8
    # Verify the completed-square upper bound for nonzero b as well.
    b2 = np.array([1., .2])
    lam2 = 6.
    h = lam2 + b2 @ np.linalg.solve(lam2 * np.eye(2) - Q, b2)
    for v in [np.array([1., 0.]), np.array([-1., 0.]),
              np.array([0., 1.]), np.array([0., -1.]),
              np.array([1., 1.]) / math.sqrt(2.)]:
        assert v @ Q @ v + 2. * b2 @ v <= h

    before = (-2. + 1.) ** 2
    after = (-2. + 1. - 1.) ** 2
    assert before == 1. and after == 4.
    return {
        "conflicting_points_have_zero_score_and_zero_center": True,
        "strong_convexity_fixed_checks": True,
        "capped_center_primal_dual_tight_fixed_example": True,
        "trust_region_hard_case_and_completed_square": True,
        "perfect_decontamination_can_increase_true_loss": True,
        "scope": "fixed mathematical examples, not sampled study outcomes or solver performance",
    }


def risk_margin(protocol, task3):
    """Audit the chosen rounded cap using archived q; do not re-fit Task 3."""
    low, high = task3["Sigma_m_eigenvalues"]
    q = task3["tail_integration"]["quantile"]
    n = protocol["numerical_risk_margin_check"]["angular_panels"]
    phi = np.linspace(0., math.pi / 2., n + 1)
    v = high * np.cos(phi) ** 2 + low * np.sin(phi) ** 2
    f = np.sqrt(math.pi * v / 2.) * erfc(q / np.sqrt(2. * v))
    trapezoid_mean = (f[0] / 2. + f[-1] / 2. + np.sum(f[1:-1])) / n
    const = math.sqrt(math.pi / 2.)
    d = high - low
    m1 = const / (2. * math.sqrt(low)) + q / (2. * low)
    mv = (const / (4. * low ** 1.5) + q / (4. * low ** 2)
          + q ** 3 / (4. * low ** 3))
    m2 = mv * d ** 2 + 2. * d * m1
    discretization = (math.pi / (2. * n)) ** 2 * m2 / 12.
    roundoff = protocol["numerical_risk_margin_check"]["roundoff_allowance"]
    stoploss_point = protocol["alpha"] * q + trapezoid_mean
    engineering_upper = stoploss_point + discretization + roundoff
    guard = protocol["c_guard_engineering"]
    assert engineering_upper <= guard
    assert abs(stoploss_point - task3["c_alpha"]) < 1e-12
    alpha, cap, budget = (protocol["alpha"], protocol["U_common"],
                          protocol["normal_risk_budget_R"])
    risk = alpha * cap * cap + 2. * cap * guard
    assert risk < budget
    c_allowed = (budget - alpha * cap * cap) / (2. * cap)
    assert guard < c_allowed
    assert cap > task3["U_required_for_one_percent_gain"]
    return {
        "q_reused_no_quantile_refit": q,
        "stop_loss_point": float(stoploss_point),
        "second_derivative_upper_M2": m2,
        "trapezoid_exact_arithmetic_discretization_bound": discretization,
        "engineering_roundoff_allowance_not_formally_verified": roundoff,
        "c_engineering_upper": float(engineering_upper),
        "c_guard": guard,
        "largest_c_allowed_by_chosen_cap": c_allowed,
        "normal_risk_bound_using_guard": risk,
        "budget_R": budget,
        "positive_margin": budget - risk,
        "formal_directed_rounding_certificate": False,
        "claim": "conditional analytic certificate plus deterministic numerical margin evidence",
    }


def audit(out: Path):
    out.mkdir(parents=True, exist_ok=False)
    start = time.perf_counter()
    try:
        protocol = read(BASE / "protocol_v2.json")
        v1 = read(BASE / "protocol_v1.json")
        task3 = read(ROOT / protocol["normalrisk_summary"])
        snapshot = read(BASE / "sources/task4_protocol_v2_20261114/protected_before.json")
        for key in ["model_config", "saved_matrices", "receiver", "decision", "target",
                    "innovation_times", "gap", "events_edge_r", "main_event",
                    "nominal_replay_age", "pressure_ages", "alpha", "beta",
                    "beta_parameter", "beta_compatibility", "W", "primary_R_over_J0",
                    "minimum_practical_relative_gain", "nominal_prior", "e2_gate",
                    "e3_bootstrap_resamples", "e3_main_comparators"]:
            assert protocol[key] == v1[key], key
        assert protocol["normal_calibration"]["count"] == 199
        assert protocol["normal_calibration"]["order_index_1based"] == 190
        assert protocol["normal_calibration"]["comparison"] == "strictly greater"
        assert protocol["normal_calibration"]["thresholds"] is None
        assert protocol["implementation_manifest"] is None
        assert not any(protocol["execution_authorization"].values())
        assert protocol["training_count"] == protocol["new_trajectories_in_current_delivery"] == 0
        assert protocol["seeds_used"] == []
        for name, expected in protocol["input_sha256"].items():
            assert sha(ROOT / name) == expected, name

        current_sets = []
        for group in protocol["seed_reservations"].values():
            current_sets.append(set(range(group["start"], group["start"] + group["count"])))
        assert sum(map(len, current_sets)) == len(set.union(*current_sets))
        old_sets = [set(range(g["start"], g["start"] + g["count"]))
                    for g in v1["seed_reservations"].values()]
        assert set.union(*current_sets).isdisjoint(set.union(*old_sets))

        matrix_rows = []
        with np.load(ROOT / protocol["joint_statistics_npz"], allow_pickle=False) as archive:
            assert archive["Sigma_eta"].shape == (12, 12)
            for edge, r in protocol["events_edge_r"]:
                indices = [i for i, key in enumerate(archive["case_edge_r_age"])
                           if list(key[:2]) == [edge, r]]
                assert len(indices) == 3
                nominal = next(i for i in indices if archive["case_edge_r_age"][i, 2] == 64)
                O, G = archive["O"][nominal], archive["G"][nominal]
                for ix in indices:
                    assert np.array_equal(O, archive["O"][ix])
                    assert np.array_equal(G, archive["G"][ix])
                info = O.T @ np.linalg.solve(archive["Sigma_eta"], O)
                np.linalg.cholesky(info)
                cond = float(np.linalg.cond(info))
                assert cond < protocol["solver_spec"]["maximum_condition_number"]
                matrix_rows.append({"edge": edge, "r": r, "I_condition_number": cond})

        coverage_lower = float(beta.ppf(.05, 190, 11))
        nonzero_lower = float(beta.ppf(.05, 100, 101))
        normal_max = max(k for k in range(200)
                         if beta.ppf(.95, k + 1, 200 - k) <= .1)
        assert coverage_lower >= .9 and nonzero_lower >= .4 and normal_max == 12
        assert math.ceil(200 * (1. - protocol["alpha"])) == 190
        protected_changes = [name for name, h in snapshot["protected_files"].items()
                             if not (ROOT / name).is_file() or sha(ROOT / name) != h]
        assert set(protected_changes) <= set(snapshot["allowed_existing_changes"]), protected_changes

        # Only check relative links, never access an external page.
        local_links = 0
        for name in protocol["documents"]:
            text = (BASE / name).read_text(encoding="utf-8")
            for href in re.findall(r"\]\(([^)]+)\)", text):
                if "://" in href or href.startswith("#"):
                    continue
                assert ((BASE / name).parent / href.split("#")[0]).exists(), (name, href)
                local_links += 1

        numeric = risk_margin(protocol, task3)
        examples = fixed_examples()
        source_paths = [BASE / "protocol_v2.json", Path(__file__).resolve(),
                        BASE / "sources/task4_protocol_v2_20261114/protected_before.json"]
        source_paths.extend(BASE / n for n in protocol["documents"])
        frozen = {
            "run_id": out.name, "scope": "Task 4 deterministic design audit only",
            "baseline_commit": protocol["baseline_commit"],
            "sha256": {p.relative_to(ROOT).as_posix(): sha(p) for p in source_paths},
            "input_sha256": protocol["input_sha256"],
            "new_trajectories": 0, "seeds_used": [],
            "deployed_policy_source_hashes": None, "numeric_calibration_thresholds": None,
        }
        write(out / "frozen_plan.json", frozen)
        write(out / "risk_margin_check.json", numeric)
        checks = {
            "old_input_hashes_match": True, "v1_core_model_gates_preserved": True,
            "protected_previous_tracked_files": len(snapshot["protected_files"]),
            "existing_changes_this_task": protected_changes,
            "v2_seed_reservations_disjoint_and_disjoint_from_v1": True,
            "complete_old_run_seed_collision_check": "PENDING_BEFORE_ANY_SAMPLE_GENERATION",
            "normal_calibration_marginal_bound": .05,
            "coverage190_CP_lower": coverage_lower,
            "nonzero100_CP_lower": nonzero_lower,
            "normal_max_count_for_original_point10_upper": normal_max,
            "parameter_chi2_threshold": float(chi2.ppf(1-.025/8, 2)),
            "compatibility_chi2_threshold": float(chi2.ppf(1-.025/8, 10)),
            "public_nominal_information_matrix_checks": matrix_rows,
            "O_and_G_independent_of_replay_age_in_archived_assets": True,
            "fixed_math_examples": examples, "local_links_checked": local_links,
            "no_online_algorithm_implemented_or_run": True,
        }
        write(out / "checks.json", checks)
        summary = {
            "run_id": out.name, "result": "PASS_DESIGN_AUDIT_ONLY",
            "risk_certificate": "CONDITIONAL_ON_EXACT_MODEL_INFORMATION_AND_NUMERICAL_UPPER",
            "U_common": protocol["U_common"],
            "normal_risk_budget_R": protocol["normal_risk_budget_R"],
            "normal_risk_guarded_numeric_bound": numeric["normal_risk_bound_using_guard"],
            "positive_budget_margin": numeric["positive_margin"],
            "method_performance": "OPEN_NOT_TESTED", "algorithm_go": False,
            "paper_go": False, "E2_E3_run": False,
            "execution_authorized_by_this_design": False,
            "new_trajectories": 0, "seeds_used": [], "downloads": 0,
            "additional_communication_bytes": 0,
            "elapsed_seconds": time.perf_counter() - start,
        }
        write(out / "summary.json", summary)
        print(json.dumps(summary, ensure_ascii=False))
    except Exception as exc:
        write(out / "failure.json", {"type": type(exc).__name__, "message": str(exc),
                                      "elapsed_seconds": time.perf_counter() - start})
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    audit(Path(args.out).resolve())
