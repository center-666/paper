"""Exact public-model Gaussian loadings and budget checks. No sampled paths.

Reuse archived O/G responses; do not call simulate, generate_data, or any RNG.
Two independent healthy coordinate recursions check the new cross-time moments.
This is task-2 analysis, NOT an E2 set detector or a recovery implementation.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

sys.dont_write_bytecode = True
import numpy as np
from scipy.stats import chi2

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulation"))
sys.path.insert(0, str(ROOT / "reviews/cross_phase_identifiability_audit/code"))
from model import Model
from phase_matrix_audit import reset, transition


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_json(path, value):
    def native(x):
        if isinstance(x, np.ndarray):
            return x.tolist()
        if isinstance(x, np.generic):
            return x.item()
        raise TypeError(type(x).__name__)
    Path(path).write_text(json.dumps(value, default=native, ensure_ascii=False,
                                   indent=2, allow_nan=False) + "\n",
                          encoding="utf-8", newline="\n")


def save_csv(path, rows):
    with Path(path).open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def noise_columns(model, t):
    n, N = model.cfg["n"], model.cfg["N"]
    start = n + t * n * (N + 1)
    return slice(start, start+n), slice(start+n, start+n*(N+1))


def healthy_error_coordinates(model, schedule, target, times, snapshots):
    """Rows: physical x, true-minus-estimate errors, aligned cache errors."""
    N, n, E = model.cfg["N"], model.cfg["n"], len(model.edges)
    qdim = n + target * n * (N+1)
    block = N + E
    Z = np.zeros(((block+1)*n, qdim))
    Z[:, :n] = np.tile(np.linalg.cholesky(model.P0), (block+1, 1))
    Lq = np.linalg.cholesky(model.Q)
    Lr = np.zeros((N*n, N*n))
    for i in range(N):
        Lr[i*n:(i+1)*n, i*n:(i+1)*n] = np.linalg.cholesky(model.R[i])
    eta, hats = [], {}
    for t in range(target):
        Z[n:] = reset(model, schedule[t]) @ Z[n:]
        if t in snapshots:
            hats[t] = np.stack([Z[:n] - Z[(i+1)*n:(i+2)*n] for i in range(N)])
        wsl, vsl = noise_columns(model, t)
        if t in times:
            j = 1
            row = model.H[j] @ Z[(j+1)*n:(j+2)*n]
            row[:, vsl.start+j*n:vsl.start+(j+1)*n] += np.linalg.cholesky(model.R[j])
            eta.append(row)
        F, D, _ = transition(model, t)
        next_Z = np.zeros_like(Z)
        next_Z[:n] = model.A @ Z[:n]
        next_Z[n:] = F @ Z[n:]
        next_Z[:, wsl] += np.tile(Lq, (block+1, 1))
        next_Z[n:, vsl] += D @ Lr
        Z = next_Z
    return {"eta": np.concatenate(eta), "e0": -Z[2*n:3*n],
            "x_target": Z[:n], "hats": hats}


def healthy_raw_coordinates(model, schedule, target, times, snapshots):
    """Independent original x/estimate/raw-cache equations, not error F."""
    N, n, E = model.cfg["N"], model.cfg["n"], len(model.edges)
    qdim = n + target*n*(N+1)
    x = np.zeros((n, qdim))
    x[:, :n] = np.linalg.cholesky(model.P0)
    estimates = np.zeros((N, n, qdim))
    raw = np.zeros((E, n, qdim))
    last = np.full(E, -1, int)
    eta, hats = [], {}
    for t in range(target):
        for e, (j, _) in enumerate(model.edges):
            if schedule[t, j]:
                raw[e] = estimates[j]
                last[e] = t
        assert np.all(last >= 0)
        aligned = np.stack([model.powers[t-last[e]] @ raw[e] for e in range(E)])
        if t in snapshots:
            hats[t] = estimates.copy()
        wsl, vsl = noise_columns(model, t)
        innovations = np.stack([model.H[i] @ (x-estimates[i]) for i in range(N)])
        for i in range(N):
            innovations[i, :, vsl.start+i*n:vsl.start+(i+1)*n] += np.linalg.cholesky(model.R[i])
        if t in times:
            eta.append(innovations[1].copy())
        next_estimates = np.zeros_like(estimates)
        for i in range(N):
            incoming = np.flatnonzero(model.edges[:, 1] == i)
            consensus = np.sum(aligned[incoming] - estimates[i], axis=0)
            next_estimates[i] = (model.A @ estimates[i] + model.gains[t, i] @ innovations[i]
                                 + model.cfg["epsilon"] * model.A @ consensus)
        estimates = next_estimates
        x = model.A @ x
        x[:, wsl] += np.linalg.cholesky(model.Q)
    return {"eta": np.concatenate(eta), "e0": estimates[1]-x,
            "x_target": x, "hats": hats}


def scalar_cross_correlation_check():
    theta = np.array([[-.25, -.25, 0.]])
    eta = np.array([[.75, -.25, 1.]])
    O = np.array([[.4]])
    Z = eta + O @ theta
    assert np.isclose((theta @ eta.T).item(), -.125)
    assert np.isclose((theta @ Z.T).item(), -.075)
    assert np.isclose((Z @ Z.T).item(), 1.545)
    independent_cross = (theta @ theta.T @ O.T).item()
    assert independent_cross > 0
    return {"theta_eta": -.125, "theta_z": -.075, "z_variance": 1.545,
            "incorrect_independent_theta_z": independent_cross,
            "conditional_mean_coefficient_sign_would_flip": True}


def main(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    protocol_path = HERE / "protocol_v1.json"
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    config_path = ROOT / protocol["model_config"]
    archived_path = ROOT / protocol["saved_matrices"]
    source_paths = [Path(__file__), protocol_path, HERE/"06_experiment_preregistration.md",
                    config_path, archived_path, ROOT/"simulation/model.py",
                    ROOT/"simulation/engine.py",
                    ROOT/"reviews/cross_phase_identifiability_audit/code/phase_matrix_audit.py"]
    save_json(out/"frozen_plan.json", {
        "run_id": out.name, "scope": "task1/task2 exact Gaussian matrices; NO sampled trajectories",
        "baseline_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip(),
        "source_sha256": {p.relative_to(ROOT).as_posix(): sha(p) for p in source_paths},
        "protocol": protocol, "new_trajectories": 0, "random_seeds_used": [],
    })
    try:
        cfg = json.loads(config_path.read_text(encoding="utf-8"))["model"]
        model = Model.build(cfg)
        target, times = protocol["target"], protocol["innovation_times"]
        ages = sorted(protocol["pressure_ages"] + [protocol["nominal_replay_age"]])
        schedule = np.stack([np.arange(cfg["T"]) % 8 == j for j in range(cfg["N"])], axis=1)
        schedule[0] = True
        events = np.asarray(protocol["events_edge_r"], int)
        required = {int(r) for _, r in events} | {int(r-age) for _, r in events for age in ages}
        error = healthy_error_coordinates(model, schedule, target, times, required)
        direct = healthy_raw_coordinates(model, schedule, target, times, required)
        errors = {name: float(np.max(np.abs(error[name]-direct[name])))
                  for name in ("eta", "e0", "x_target")}
        errors["sender_snapshot_coefficients"] = max(float(np.max(np.abs(error["hats"][t]-direct["hats"][t]))) for t in required)
        assert max(errors.values()) <= protocol["analytic_tolerances"]["coefficient_absolute"], errors
        eta, e0 = error["eta"], error["e0"]
        Sigma_eta = eta @ eta.T
        P0_actual = e0 @ e0.T
        J0 = float(np.trace(P0_actual))
        ratios = [protocol["primary_R_over_J0"]] + protocol["sensitivity_R_over_J0"]
        caps = {ratio: (ratio*J0)/(np.sqrt(protocol["alpha"])*(np.sqrt(J0*(1+ratio))+np.sqrt(J0))) for ratio in ratios}
        nominal_J0 = float(np.trace(model.nominal_covariance[target, 2:4, 2:4]))
        arrays = {"eta_loading": eta, "e0_loading": e0,
                  "Sigma_eta": Sigma_eta, "P0_actual": P0_actual,
                  "schedule": schedule, "A": model.A, "H": model.H,
                  "gains": model.gains[:target], "events": events, "ages": np.asarray(ages)}
        case_arrays = {name: [] for name in [
            "case_edge_r_age", "theta_loading", "O", "G", "Sigma_theta_theta", "Sigma_theta_eta",
            "Sigma_theta_z", "Sigma_zz", "Sigma_e0_theta", "Sigma_e0_z", "Sigma_ea",
            "B_theta_z", "B_delta_z", "B_e0_z", "posterior_theta_covariance"]}
        rows, budgets = [], []
        covariance_errors = []
        with np.load(archived_path, allow_pickle=False) as old:
            selected = np.flatnonzero(np.repeat(np.isin(old["times_P"], times), cfg["n"]))
            split = len(old["times_C"]) * cfg["n"]
            old_eta = old["Sigma"][split:, split:][np.ix_(selected, selected)]
            archived_eta_error = float(np.max(np.abs(Sigma_eta-old_eta)))
            assert np.allclose(Sigma_eta, old_eta, rtol=1e-8, atol=1e-10), archived_eta_error
            for edge, r in events:
                j = int(model.edges[edge, 0])
                k = next(k for k, h in enumerate(old["events"]) if np.array_equal(h, [edge, r]))
                O, G = old["O_P"][k, selected], old["G_dplus1"][k]
                assert np.linalg.matrix_rank(O, tol=1e-10) == 2
                for age in ages:
                    s = int(r-age)
                    assert 0 <= s < r and schedule[s, j] and schedule[r, j]
                    Theta = error["hats"][s][j] - error["hats"][int(r)][j]
                    Theta_check = direct["hats"][s][j] - direct["hats"][int(r)][j]
                    assert np.allclose(Theta, Theta_check, rtol=1e-8, atol=1e-10)
                    Z = eta + O @ Theta
                    Delta = G @ Theta
                    Ea = e0 + Delta
                    Tcov, Cte = Theta @ Theta.T, Theta @ eta.T
                    Ctz = Tcov @ O.T + Cte
                    Szz = Sigma_eta + O @ Tcov @ O.T + O @ Cte + Cte.T @ O.T
                    Szz = (Szz+Szz.T)/2
                    np.linalg.cholesky(Szz)
                    assert np.allclose(Ctz, Theta @ Z.T, rtol=1e-8, atol=1e-10)
                    assert np.allclose(Szz, Z @ Z.T, rtol=1e-8, atol=1e-10)
                    Ce0t, Ce0z = e0 @ Theta.T, e0 @ Z.T
                    Btheta = np.linalg.solve(Szz, Ctz.T).T
                    Bdelta = G @ Btheta
                    Be0 = np.linalg.solve(Szz, Ce0z.T).T
                    Vtheta = Tcov - Btheta @ Ctz.T
                    Vtheta = (Vtheta+Vtheta.T)/2
                    residual_theta = Theta-Btheta @ Z
                    error_cov = float(np.linalg.norm(Vtheta-residual_theta @ residual_theta.T)/max(1., np.linalg.norm(Tcov)))
                    covariance_errors.append(error_cov)
                    assert error_cov < 1e-8
                    assert np.linalg.eigvalsh(Vtheta)[0] >= -1e-9*max(1.,np.linalg.norm(Tcov))
                    Sa = Ea @ Ea.T
                    Ja = float(np.trace(Sa))
                    direct_Ja = J0 + float(np.trace(G @ Tcov @ G.T)) + 2*float(np.trace(Ce0t @ G.T))
                    assert np.isclose(Ja, direct_Ja, rtol=1e-8, atol=1e-10)
                    residual_impact_action = Ea-Bdelta @ Z
                    residual_state_action = Ea-(Bdelta+Be0) @ Z
                    soft_impact_mse = float(np.sum(residual_impact_action**2))
                    state_mean_mse = float(np.sum(residual_state_action**2))
                    objective_gap = float(np.trace(Be0 @ Szz @ Be0.T))
                    assert np.isclose(soft_impact_mse-state_mean_mse, objective_gap, rtol=1e-8, atol=1e-10)
                    effect_rms = float(np.linalg.norm(Delta))
                    joint = np.concatenate([Theta, Z, e0])
                    joint_cov = joint @ joint.T
                    assert np.linalg.eigvalsh(joint_cov)[0] > -1e-9*max(1.,np.linalg.norm(joint_cov))
                    correlation = np.linalg.solve(np.linalg.cholesky(Tcov), Cte)
                    correlation = np.linalg.solve(np.linalg.cholesky(Sigma_eta), correlation.T).T
                    values = {"case_edge_r_age": [int(edge), int(r), age], "theta_loading": Theta,
                              "O": O, "G": G, "Sigma_theta_theta": Tcov, "Sigma_theta_eta": Cte,
                              "Sigma_theta_z": Ctz, "Sigma_zz": Szz, "Sigma_e0_theta": Ce0t,
                              "Sigma_e0_z": Ce0z, "Sigma_ea": Sa, "B_theta_z": Btheta,
                              "B_delta_z": Bdelta, "B_e0_z": Be0,
                              "posterior_theta_covariance": Vtheta}
                    for name in case_arrays:
                        case_arrays[name].append(values[name])
                    rows.append({"edge": int(edge), "sender": j, "r": int(r), "q": int(r+8),
                                 "source": s, "age": age, "J0": J0, "theta_rms": float(np.linalg.norm(Theta)),
                                 "effect_rms": effect_rms, "Ja": Ja, "MSE_excess_vs_healthy": Ja-J0,
                                 "health_effect_cross_MSE_term": 2*float(np.trace(Ce0t @ G.T)),
                                 "theta_eta_covariance_norm": float(np.linalg.norm(Cte)),
                                 "max_theta_eta_canonical_correlation": float(np.linalg.svd(correlation, compute_uv=False)[0]),
                                 "independence_omission_relative_Szz": float(np.linalg.norm(O @ Cte+Cte.T @ O.T)/np.linalg.norm(Szz)),
                                 "unbounded_known_h_soft_impact_true_MSE_reference": soft_impact_mse,
                                 "unbounded_known_h_true_state_MMSE_reference": state_mean_mse,
                                 "objective_gap": objective_gap,
                                 "Sigma_zz_min_eigenvalue": float(np.linalg.eigvalsh(Szz)[0])})
                    for ratio, U in caps.items():
                        upper = 1-max(1-U/np.sqrt(Ja), 0.)**2
                        budgets.append({"edge": int(edge), "r": int(r), "age": age, "R_over_J0": ratio,
                                        "R": ratio*J0, "U": U, "U_over_effect_rms": U/effect_rms,
                                        "Ja": Ja, "any_capped_action_relative_gain_upper": upper,
                                        "excluded_at_one_percent": bool(upper < protocol["minimum_practical_relative_gain"])})
        arrays.update({k: np.asarray(v) for k,v in case_arrays.items()})
        matrix_path = out/"replay_joint_matrices.npz"
        np.savez_compressed(matrix_path, **arrays)
        save_csv(out/"joint_cases.csv", rows)
        save_csv(out/"budget_feasibility.csv", budgets)
        main_budget = next(b for b in budgets if [b["edge"],b["r"]]==protocol["main_event"]
                           and b["age"]==64 and b["R_over_J0"]==.01)
        main_case = next(row for row in rows if [row["edge"],row["r"]]==protocol["main_event"] and row["age"]==64)
        checks = {"coordinate_loading_max_errors": errors,
                  "archived_healthy_innovation_covariance_absolute_error": archived_eta_error,
                  "posterior_covariance_relative_identity_max": max(covariance_errors),
                  "scalar_correlation_sign_test": scalar_cross_correlation_check(),
                  "cases": len(rows), "legal_sources": True, "all_joint_covariances_PSD": True,
                  "no_ridge": True, "new_trajectories": 0}
        save_json(out/"checks.json", checks)
        summary = {"run_id":out.name, "status":"COMPLETE_TASK1_TASK2",
                   "J0_actual_cached": J0, "P0_actual_cached": P0_actual,
                   "nominal_instantaneous_reported_J0": nominal_J0,
                   "caps_by_budget_ratio": {str(r): u for r,u in caps.items()},
                   "chi_square_parameter_threshold": float(chi2.ppf(1-.025/8,2)),
                   "chi_square_compatibility_threshold": float(chi2.ppf(1-.025/8,10)),
                   "main_case": main_case, "main_budget": main_budget,
                   "pre_E2_budget_decision": "BUDGET_INFEASIBLE_STOP" if main_budget["excluded_at_one_percent"] else "NOT_ANALYTICALLY_EXCLUDED; E2 NOT RUN",
                   "matrix_file_sha256": sha(matrix_path), "checks": checks,
                   "elapsed_seconds": time.perf_counter()-started,
                   "new_trajectories":0,"seeds_used":[],"additional_communication_bytes":0}
        save_json(out/"summary.json", summary)
        print(json.dumps({k:summary[k] for k in ["run_id","J0_actual_cached","caps_by_budget_ratio","pre_E2_budget_decision","elapsed_seconds"]}))
    except Exception as exc:
        save_json(out/"failure.json", {"exception_type":type(exc).__name__,"message":str(exc),
                                      "elapsed_seconds":time.perf_counter()-started})
        raise


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",required=True)
    main(parser.parse_args().out)
