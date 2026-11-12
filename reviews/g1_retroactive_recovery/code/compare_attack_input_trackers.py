from __future__ import annotations

import csv
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
BRANCH = Path(__file__).resolve().parents[1]
SIM = ROOT / "simulation"
OUT = BRANCH / "results" / "g1r_attack_input_tracker_20261112_02"
sys.path.insert(0, str(SIM))
sys.path.insert(0, str(BRANCH / "code"))

from engine import simulate
from model import generate_data
from minimal_recovery_screen import (
    ATTACK_BIAS, CAL, D, R, TARGET_EDGE_PAIR, TARGET_NODE, TEST, TRAIN,
    build_model, common_schedule, estimate_attack, innovations, write_csv, write_json,
)

Q = R + 8
END = 260
PREFIX_TIMES = np.arange(R, D + 1)
POST_TIMES = np.arange(Q + 1, D + 1)


def precision_from_samples(samples):
    mean = samples.mean(axis=0)
    covariance = np.cov(samples, rowvar=False, ddof=1)
    scale = max(float(np.trace(covariance) / covariance.shape[0]), 1e-8)
    covariance = (covariance + covariance.T) / 2 + 1e-4 * scale * np.eye(covariance.shape[0])
    chol = np.linalg.cholesky(covariance)
    return mean, covariance, np.linalg.solve(chol, np.eye(len(mean))), chol


def tracker_sequence(z, J, chol, m):
    # Cholesky whitening is causal: each new block contributes a new innovation
    # without revising any earlier whitened residual.
    zw = np.linalg.solve(chol, z)
    Jw = np.linalg.solve(chol, J)
    p = J.shape[1]
    info = np.zeros((p, p))
    score = np.zeros(p)
    estimates = []
    scores = []
    for k in range(len(z) // m):
        sl = slice(k*m, (k+1)*m)
        jk, zk = Jw[sl], zw[sl]
        info += jk.T @ jk
        score += jk.T @ zk
        cov = np.linalg.pinv(info, rcond=1e-10)
        theta = cov @ score
        estimates.append(theta.copy())
        scores.append(float(score @ theta))
    return np.asarray(estimates), np.asarray(scores), Jw, zw


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    OUT.mkdir(parents=True)
    started = time.perf_counter()
    model = build_model()
    seeds = np.r_[TRAIN, CAL, TEST]
    x, y = generate_data(model, seeds)
    schedule = common_schedule(model, len(seeds))
    ntr, ncal = len(TRAIN), len(CAL)
    xtr, ytr, strn, schtr = x[:ntr], y[:ntr], TRAIN, schedule[:ntr]
    xcal, ycal, scal, schcal = x[ntr:ntr+ncal], y[ntr:ntr+ncal], CAL, schedule[ntr:ntr+ncal]
    xtest, ytest, stest, schtest = x[ntr+ncal:], y[ntr+ncal:], TEST, schedule[ntr+ncal:]
    edge = int(np.flatnonzero(np.all(model.edges == TARGET_EDGE_PAIR, axis=1))[0])

    clean_tr = simulate(model, xtr, ytr, strn, "yang", schedule=schtr, collect=False)
    clean_cal = simulate(model, xcal, ycal, scal, "yang", schedule=schcal, collect=False)
    clean_test = simulate(model, xtest, ytest, stest, "yang", schedule=schtest, collect=False)

    # Unit input responses are conditioned on a registered event time and edge.
    Jprefix_cols, Sprefix_cols = [], []
    old_bias = model.cfg["attack"]["bias"]
    for j in range(model.cfg["n"]):
        unit = np.eye(model.cfg["n"])[j]
        model.cfg["attack"]["bias"] = unit.tolist()
        rr = simulate(model, xtr[:1], ytr[:1], strn[:1], "yang",
                      scenario="single_step", schedule=schtr[:1], collect=False)
        Jprefix_cols.append((innovations(rr, ytr[:1], model, TARGET_NODE, PREFIX_TIMES)[0]
                             - innovations(clean_tr, ytr, model, TARGET_NODE, PREFIX_TIMES)[0]).reshape(-1))
        Sprefix_cols.append(rr.estimates[0] - clean_tr.estimates[0])
    model.cfg["attack"]["bias"] = old_bias
    Jprefix = np.column_stack(Jprefix_cols)
    Sprefix = np.stack(Sprefix_cols, axis=-1)
    post_rows = np.concatenate([np.arange(t*model.cfg["n"], (t+1)*model.cfg["n"])
                                for t in POST_TIMES-R])
    Jpost = Jprefix[post_rows]

    tr_res = innovations(clean_tr, ytr, model, TARGET_NODE, PREFIX_TIMES).reshape(ntr, -1)
    mu_prefix, cov_prefix, _, chol_prefix = precision_from_samples(tr_res)
    tr_post = innovations(clean_tr, ytr, model, TARGET_NODE, POST_TIMES).reshape(ntr, -1)
    mu_post, cov_post, _, chol_post = precision_from_samples(tr_post)
    cal_prefix = innovations(clean_cal, ycal, model, TARGET_NODE, PREFIX_TIMES).reshape(ncal, -1) - mu_prefix
    cal_post = innovations(clean_cal, ycal, model, TARGET_NODE, POST_TIMES).reshape(ncal, -1) - mu_post
    cal_scores_prefix, cal_scores_post = [], []
    for z in cal_prefix:
        _, _, lr = estimate_attack(z, Jprefix, np.linalg.inv(cov_prefix))
        cal_scores_prefix.append(lr)
    for z in cal_post:
        _, _, lr = estimate_attack(z, Jpost, np.linalg.inv(cov_post))
        cal_scores_post.append(lr)
    gate_prefix = float(np.quantile(cal_scores_prefix, .95, method="higher"))
    gate_post = float(np.quantile(cal_scores_post, .95, method="higher"))

    rows, trajectories, traces, normal_rows = [], [], [], []
    for i, seed in enumerate(stest):
        z_prefix = innovations(clean_test, ytest, model, TARGET_NODE, PREFIX_TIMES)[i].reshape(-1)-mu_prefix
        z_post = innovations(clean_test, ytest, model, TARGET_NODE, POST_TIMES)[i].reshape(-1)-mu_post
        theta_prefix, _, lr_prefix = estimate_attack(z_prefix, Jprefix, np.linalg.inv(cov_prefix))
        theta_post, _, lr_post = estimate_attack(z_post, Jpost, np.linalg.inv(cov_post))
        for label, theta, lr, gate in (
            ("causal_input_tracker_full_residual_200_to_216", theta_prefix, lr_prefix, gate_prefix),
            ("post_cache_GLS_209_to_216", theta_post, lr_post, gate_post),
        ):
            corrected = clean_test.estimates[i].copy()
            trigger = bool(lr > gate)
            if trigger:
                corrected[D+1:] -= np.einsum("tnip,p->tni", Sprefix[D+1:], theta)
            before = np.sum((xtest[i, :, None, :]-clean_test.estimates[i])**2, axis=-1)
            after = np.sum((xtest[i, :, None, :]-corrected)**2, axis=-1)
            normal_rows.append({"seed": int(seed), "method": label, "likelihood_improvement": lr,
                "gate": gate, "false_correction": trigger,
                "receiver_mse_change": float(np.mean(after[D+1:END+1,TARGET_NODE]-before[D+1:END+1,TARGET_NODE])),
                "network_mse_change": float(np.mean(after[D+1:END+1]-before[D+1:END+1]))})
    for scenario in ("single_step", "replay_packet"):
        attacked = simulate(model, xtest, ytest, stest, "yang", scenario=scenario,
                            schedule=schtest, collect=False)
        clean_error = np.sum((xtest[:, :, None, :] - clean_test.estimates)**2, axis=-1)
        attack_error = np.sum((xtest[:, :, None, :] - attacked.estimates)**2, axis=-1)
        for i, seed in enumerate(stest):
            z_prefix = innovations(attacked, ytest, model, TARGET_NODE, PREFIX_TIMES)[i].reshape(-1) - mu_prefix
            z_post = innovations(attacked, ytest, model, TARGET_NODE, POST_TIMES)[i].reshape(-1) - mu_post
            recursive_theta, recursive_lr, _, _ = tracker_sequence(
                innovations(attacked, ytest, model, TARGET_NODE, PREFIX_TIMES)[i].reshape(-1)-mu_prefix,
                Jprefix, chol_prefix, model.cfg["n"])
            # Endpoint batch GLS and recursively accumulated whitened innovations must agree.
            batch_prefix, _, lr_prefix = estimate_attack(z_prefix, Jprefix, np.linalg.inv(cov_prefix))
            if np.max(np.abs(batch_prefix-recursive_theta[-1])) > 1e-8:
                raise AssertionError("Recursive tracker endpoint differs from batch GLS")
            theta_post, _, lr_post = estimate_attack(z_post, Jpost, np.linalg.inv(cov_post))

            source = int(attacked.replay_source[i, R]) if scenario == "replay_packet" else -1
            a_true = (clean_test.estimates[i, source, TARGET_EDGE_PAIR[0]]
                      - clean_test.estimates[i, R, TARGET_EDGE_PAIR[0]]) if scenario == "replay_packet" else ATTACK_BIAS.copy()
            for label, theta, lr, gate in (
                ("causal_input_tracker_full_residual_200_to_216", recursive_theta[-1], lr_prefix, gate_prefix),
                ("post_cache_GLS_209_to_216", theta_post, lr_post, gate_post),
            ):
                trigger = bool(lr > gate)
                corrected = attacked.estimates[i].copy()
                if trigger:
                    corrected[D+1:] -= np.einsum("tnip,p->tni", Sprefix[D+1:], theta)
                corrected_error = np.sum((xtest[i, :, None, :] - corrected)**2, axis=-1)
                loc = slice(D+1, END+1)
                rows.append({
                    "scenario": scenario, "seed": int(seed), "method": label,
                    "oracle_event_edge_and_time_used": True, "send_time": R,
                    "cache_replaced_time": Q, "estimate_time": D,
                    "source_time": source, "source_age": R-source if source >= 0 else 0,
                    "replacements": int(attacked.injected[i, R]),
                    "estimated_offset_norm": float(np.linalg.norm(theta)),
                    "offset_error_norm": float(np.linalg.norm(theta-a_true)),
                    "likelihood_improvement": lr, "normal_95_gate": gate, "correction_triggered": trigger,
                    "receiver_recovery_excess_mse_before": float((attack_error[i, loc, TARGET_NODE]-clean_error[i, loc, TARGET_NODE]).mean()),
                    "receiver_recovery_excess_mse_after": float((corrected_error[loc, TARGET_NODE]-clean_error[i, loc, TARGET_NODE]).mean()),
                    "network_recovery_excess_mse_before": float((attack_error[i, loc]-clean_error[i, loc]).mean()),
                    "network_recovery_excess_mse_after": float((corrected_error[loc]-clean_error[i, loc]).mean()),
                    "normal_false_alarm_rate_cal": float(np.mean(np.asarray(cal_scores_prefix if label.startswith("causal") else cal_scores_post) > gate)),
                })
            for age, th, score in zip(PREFIX_TIMES, recursive_theta, recursive_lr):
                traces.append({"scenario": scenario, "seed": int(seed), "time": int(age),
                               "theta_hat_norm": float(np.linalg.norm(th)), "recursive_lr": float(score),
                               "calibrated_gate": gate_prefix})
            trajectories.append({"scenario": scenario, "seed": int(seed),
                "batch_recursive_endpoint_abs_error": float(np.max(np.abs(batch_prefix-recursive_theta[-1])))})

    write_csv(OUT / "per_seed_comparison.csv", rows)
    write_csv(OUT / "recursive_trace.csv", traces)
    write_csv(OUT / "equivalence_checks.csv", trajectories)
    write_csv(OUT / "normal_test_audit.csv", normal_rows)
    summaries = []
    for scenario in ("single_step", "replay_packet"):
        for method in ("causal_input_tracker_full_residual_200_to_216", "post_cache_GLS_209_to_216"):
            subset = [r for r in rows if r["scenario"] == scenario and r["method"] == method]
            summaries.append({
                "scenario": scenario, "method": method, "n_seed": len(subset),
                "trigger_rate": float(np.mean([r["correction_triggered"] for r in subset])),
                "receiver_excess_before": float(np.mean([r["receiver_recovery_excess_mse_before"] for r in subset])),
                "receiver_excess_after": float(np.mean([r["receiver_recovery_excess_mse_after"] for r in subset])),
                "network_excess_before": float(np.mean([r["network_recovery_excess_mse_before"] for r in subset])),
                "network_excess_after": float(np.mean([r["network_recovery_excess_mse_after"] for r in subset])),
            })
    files = [Path(__file__), SIM / "engine.py", SIM / "model.py", BRANCH / "code/minimal_recovery_screen.py"]
    write_json(OUT / "config.json", {
        "run_id": OUT.name, "parent": "g1r_minimal_screen_20261112_02",
        "naming": "discrete Deghat-inspired unknown-input tracker structure; not a reproduction of Deghat's H-infinity/LMI observer",
        "model_and_schedule": "same Yang-form heterogeneous model and exogenous gap8 schedule",
        "event_information": "oracle event edge/time held fixed to compare estimator mechanisms; deployment event localization remains untested",
        "training_seeds": TRAIN.tolist(), "calibration_seeds": CAL.tolist(), "test_seeds": TEST.tolist(),
        "methods": ["causal input tracker using full residual prefix r..d", "GLS using post-cache-only residual window q+1..d"],
        "noise_model": "empirical full joint covariance of normal residual sequence, ridge 1e-4 relative scale",
        "normal_gate": "separate 95th percentile likelihood-improvement threshold for each window on independent calibration seeds",
        "communication": "no correction broadcast modeled; network correction is an offline information upper comparison",
        "exploratory_only": True,
    })
    write_json(OUT / "diagnostics.json", {
        "max_recursive_batch_endpoint_abs_error": max(r["batch_recursive_endpoint_abs_error"] for r in trajectories),
        "prefix_innovation_rows": len(PREFIX_TIMES), "post_cache_innovation_rows": len(POST_TIMES),
        "prefix_sensitivity_singular_values": np.linalg.svd(Jprefix, compute_uv=False).tolist(),
        "post_cache_sensitivity_singular_values": np.linalg.svd(Jpost, compute_uv=False).tolist(),
        "prefix_gate": gate_prefix, "post_cache_gate": gate_post,
        "per_seed_methods": len(rows), "paired_independent_seed_unit": True,
        "normal_test_false_correction_rate": {
            method: float(np.mean([r["false_correction"] for r in normal_rows if r["method"] == method]))
            for method in ("causal_input_tracker_full_residual_200_to_216", "post_cache_GLS_209_to_216")},
        "cost_note": "recursive tracker and post-cache GLS retain only 2x2 information and 2-vector score online if Cholesky whitening is precomputed; offline 34x34 / 16x16 covariance tables shared by model/schedule.",
    })
    write_json(OUT / "summary.json", {"run_id": OUT.name, "results": summaries,
        "elapsed_seconds": time.perf_counter()-started,
        "interpretation": "This tests whether the post-cache GLS is only a shorter-window version of standard recursive unknown-input estimation. Both use an oracle-known event; no novelty inference is permitted from this alone."})
    write_json(OUT / "source_hashes.json", {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
    print(json.dumps({"run_id": OUT.name, "summary": summaries, "diagnostics": json.loads((OUT/"diagnostics.json").read_text(encoding="utf-8"))}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
