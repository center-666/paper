from __future__ import annotations

import copy
import csv
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
SIM = ROOT / "simulation"
OUT = Path(__file__).resolve().parents[1] / "results" / "g1r_minimal_screen_20261112_02"
sys.path.insert(0, str(SIM))

from engine import simulate
from model import Model, generate_data


RUN_ID = "g1r_minimal_screen_20261112_02"
TRAIN = np.arange(9700000, 9700064)
CAL = np.arange(9800000, 9800048)
TEST = np.arange(9900000, 9900048)
R = 200
Q = 208
D = 216
WINDOW = 8
RECOVERY_END = 260
TARGET_NODE = 1
TARGET_EDGE_PAIR = (0, 1)
ATTACK_BIAS = np.array([1.2, -0.8])


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, rows) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def build_model() -> Model:
    cfg = json.loads((SIM / "config.json").read_text(encoding="utf-8"))
    ref = json.loads((SIM / "reference_exploration_plan.json").read_text(encoding="utf-8"))
    setting = next(x for x in ref["models"] if x["id"] == "heterogeneous_sensing")
    cfg.update(A=setting["A"], H_matrices=setting["H_matrices"], T=280, warmup=50)
    cfg["attack"].update(sender=0, receiver=1, start=R, end_inclusive=R,
                         bias=ATTACK_BIAS.tolist(), replay_packet_lag=8)
    cfg["cache_schedule_pattern"] = [8]
    cfg["cache_schedule_phase"] = 1
    return Model.build(cfg)


def common_schedule(model: Model, count: int) -> np.ndarray:
    t = np.arange(model.cfg["T"])
    out = np.zeros((count, model.cfg["T"], model.cfg["N"]), dtype=bool)
    for node in range(model.cfg["N"]):
        out[:, :, node] = (t % 8) == node
    out[:, 0, :] = True
    return out


def run(model, x, y, seeds, schedule, scenario="clean", method="yang", monitor=None):
    return simulate(model, x, y, seeds, method, scenario=scenario, schedule=schedule,
                    collect=False, cache_monitor=monitor, cap=np.inf)


def innovations(run_out, y, model, node, times):
    predicted = np.einsum("mn,stn->stm", model.H[node], run_out.estimates[:, times, node])
    return y[:, times, node] - predicted


def estimate_attack(z, J, precision):
    info = J.T @ precision @ J
    covariance = np.linalg.pinv(info, rcond=1e-10)
    a_hat = covariance @ J.T @ precision @ z
    lr = float(z @ precision @ z - (z - J @ a_hat) @ precision @ (z - J @ a_hat))
    return a_hat, covariance, max(lr, 0.0)


def receiver_replay(model, y, schedule, run_out, trial, scenario, drop_target):
    """Replay one receiver from the pre-event checkpoint using packets it received."""
    node = TARGET_NODE
    edge_ids = np.flatnonzero(model.edges[:, 1] == node)
    src = model.edges[:, 0]
    target = int(np.flatnonzero(np.all(model.edges == TARGET_EDGE_PAIR, axis=1))[0])
    estimate = run_out.estimates[trial, R, node].copy()
    payload = np.zeros((len(edge_ids), model.cfg["n"]))
    last_rx = np.full(len(edge_ids), -1, dtype=int)
    for z, e in enumerate(edge_ids):
        prior = np.flatnonzero(schedule[trial, :R, src[e]])
        prior = prior[prior < R]
        if len(prior):
            t0 = int(prior[-1])
            payload[z] = run_out.estimates[trial, t0, src[e]]
            last_rx[z] = t0

    out = np.zeros((model.cfg["T"] + 1, model.cfg["n"]))
    out[R] = estimate
    for t in range(R, model.cfg["T"]):
        innovation = y[trial, t, node] - model.H[node] @ estimate
        nxt = model.A @ estimate + model.gains[t, node] @ innovation
        consensus = np.zeros(model.cfg["n"])
        for z, e in enumerate(edge_ids):
            fresh = bool(schedule[trial, t, src[e]])
            if drop_target and e == target and t == R:
                fresh = False
            if fresh:
                if e == target and t == R:
                    if scenario == "replay_packet":
                        source_time = int(run_out.replay_source[trial, t])
                        payload[z] = run_out.estimates[trial, source_time, src[e]]
                    else:
                        payload[z] = run_out.estimates[trial, t, src[e]] + ATTACK_BIAS
                else:
                    payload[z] = run_out.estimates[trial, t, src[e]]
                last_rx[z] = t
            age = t - last_rx[z] if last_rx[z] >= 0 else 0
            aligned = model.powers[age] @ payload[z]
            consensus += aligned - estimate
        estimate = nxt + model.cfg["epsilon"] * model.A @ consensus
        out[t + 1] = estimate
    return out


def local_checkpoint_filter(model, y, run_out, trial, start=R):
    """Ordinary local-only replay from the receiver's pre-event checkpoint."""
    node = TARGET_NODE
    estimate = run_out.estimates[trial, start, node].copy()
    out = np.zeros((model.cfg["T"] + 1, model.cfg["n"]))
    out[start] = estimate
    for t in range(start, model.cfg["T"]):
        innovation = y[trial, t, node] - model.H[node] @ estimate
        estimate = model.A @ estimate + model.local_gains[t, node] @ innovation
        out[t + 1] = estimate
    return out


class IsolateAfterDetection:
    def __init__(self, model, detection_time):
        self.edges = len(model.edges)
        self.target = int(np.flatnonzero(np.all(model.edges == TARGET_EDGE_PAIR, axis=1))[0])
        self.detection_time = detection_time

    def update(self, t, fresh, age, aligned, measurement, local_hat):
        w = np.ones(fresh.shape)
        if t >= self.detection_time:
            w[:, self.target] = 0.0
        return w


def metrics(error, clean_error, node, start, end):
    sl = slice(start, end)
    receiver = float(np.mean(error[sl, node]))
    network = float(np.mean(error[sl]))
    clean_receiver = float(np.mean(clean_error[sl, node]))
    clean_network = float(np.mean(clean_error[sl]))
    return {
        "receiver_mse": receiver,
        "receiver_clean_mse": clean_receiver,
        "receiver_excess_mse": receiver - clean_receiver,
        "network_mse": network,
        "network_clean_mse": clean_network,
        "network_excess_mse": network - clean_network,
    }


def main() -> None:
    if OUT.exists():
        raise FileExistsError(f"Preserve existing run: {OUT}")
    OUT.mkdir(parents=True)
    started = time.perf_counter()
    model = build_model()
    schedule_all = common_schedule(model, len(TRAIN) + len(CAL) + len(TEST))
    seeds_all = np.r_[TRAIN, CAL, TEST]
    x_all, y_all = generate_data(model, seeds_all)
    ntr, ncal = len(TRAIN), len(CAL)
    xtr, ytr, strn, schtr = x_all[:ntr], y_all[:ntr], TRAIN, schedule_all[:ntr]
    xcal, ycal, scal, schcal = x_all[ntr:ntr+ncal], y_all[ntr:ntr+ncal], CAL, schedule_all[ntr:ntr+ncal]
    xtest, ytest, stest, schtest = x_all[ntr+ncal:], y_all[ntr+ncal:], TEST, schedule_all[ntr+ncal:]
    target_edge = int(np.flatnonzero(np.all(model.edges == TARGET_EDGE_PAIR, axis=1))[0])
    packet_time = np.flatnonzero(schtest[0, :, TARGET_EDGE_PAIR[0]] & (np.arange(model.cfg["T"]) == R))
    if not len(packet_time):
        raise AssertionError("The fixed schedule must create a real send at the registered attack time")

    clean_train = run(model, xtr, ytr, strn, schtr)
    clean_cal = run(model, xcal, ycal, scal, schcal)
    clean_test = run(model, xtest, ytest, stest, schtest)

    # Train a full covariance for the post-cache local-innovation vector.
    residual_times = np.arange(Q + 1, D + 1)
    train_z = innovations(clean_train, ytr, model, TARGET_NODE, residual_times).reshape(ntr, -1)
    mu = train_z.mean(axis=0)
    covariance = np.cov(train_z, rowvar=False, ddof=1)
    scale = max(float(np.trace(covariance) / len(mu)), 1e-8)
    covariance = (covariance + covariance.T) / 2 + 1e-4 * scale * np.eye(len(mu))
    precision = np.linalg.inv(covariance)

    # A unit packet perturbation gives the exact linear response under this frozen mode schedule.
    basis_responses = []
    basis_global = []
    for j in range(model.cfg["n"]):
        old_bias = model.cfg["attack"]["bias"]
        unit = np.eye(model.cfg["n"])[j]
        model.cfg["attack"]["bias"] = unit.tolist()
        basis = run(model, xtr[:1], ytr[:1], strn[:1], schtr[:1], scenario="single_step")
        basis_responses.append(innovations(basis, ytr[:1], model, TARGET_NODE, residual_times)[0].reshape(-1)
                               - innovations(clean_train, ytr, model, TARGET_NODE, residual_times)[0].reshape(-1))
        basis_global.append(basis.estimates[0] - clean_train.estimates[0])
        model.cfg["attack"]["bias"] = old_bias
    J = np.column_stack(basis_responses)
    S = np.stack(basis_global, axis=-1)
    singular = np.linalg.svd(J, compute_uv=False)
    if len(singular) < model.cfg["n"] or singular[-1] < 1e-8:
        raise RuntimeError(f"Attack-effect residual is rank-deficient: singular values={singular.tolist()}")

    # Verify schedule-conditional linearity independently on another seed.
    linearity_errors = []
    old_bias = model.cfg["attack"]["bias"]
    for j in range(model.cfg["n"]):
        model.cfg["attack"]["bias"] = np.eye(model.cfg["n"])[j].tolist()
        b = run(model, xtr[1:2], ytr[1:2], strn[1:2], schtr[1:2], scenario="single_step")
        c = run(model, xtr[1:2], ytr[1:2], strn[1:2], schtr[1:2])
        expected = S[:, :, :, j]
        linearity_errors.append(float(np.max(np.abs((b.estimates[0] - c.estimates[0]) - expected))))
    model.cfg["attack"]["bias"] = old_bias

    # Calibrate one likelihood-improvement gate on independent normal data.
    cal_z = innovations(clean_cal, ycal, model, TARGET_NODE, residual_times).reshape(ncal, -1) - mu
    cal_lr = []
    for z in cal_z:
        _, _, lr = estimate_attack(z, J, precision)
        cal_lr.append(lr)
    gate = float(np.quantile(cal_lr, 0.95, method="higher"))

    case_rows = []
    seed_rows = []
    packet_rows = []
    normal_cor_mat = []
    for scenario in ("single_step", "replay_packet"):
        attacked = run(model, xtest, ytest, stest, schtest, scenario=scenario)
        isolates = run(model, xtest, ytest, stest, schtest, scenario=scenario,
                       method="capped", monitor=IsolateAfterDetection(model, D))
        # Receiver-local rollback is computed only from that node's retained measurements and received packets.
        for s, seed in enumerate(stest):
            rec_actual = receiver_replay(model, ytest, schtest, attacked, s, scenario, drop_target=False)
            rec_drop = receiver_replay(model, ytest, schtest, attacked, s, scenario, drop_target=True)
            if np.max(np.abs(rec_actual[R:] - attacked.estimates[s, R:, TARGET_NODE])) > 2e-8:
                raise AssertionError("Receiver replay does not reproduce the logged Yang-form trace")
            local = local_checkpoint_filter(model, ytest, attacked, s)
            z = innovations(attacked, ytest, model, TARGET_NODE, residual_times)[s].reshape(-1) - mu
            a_hat, a_cov, lr = estimate_attack(z, J, precision)
            use = lr > gate
            corrected_local = attacked.estimates[s, :, TARGET_NODE].copy()
            if use:
                corrected_local[D+1:] -= np.einsum("tnp,p->tn", S[D+1:, TARGET_NODE], a_hat)
            corrected_global = attacked.estimates[s].copy()
            if use:
                corrected_global[D+1:] -= np.einsum("tnip,p->tni", S[D+1:], a_hat)
            oracle_local = attacked.estimates[s, :, TARGET_NODE].copy()
            oracle_global = attacked.estimates[s].copy()
            source = int(attacked.replay_source[s, R]) if scenario == "replay_packet" else -1
            if scenario == "replay_packet":
                a_true = clean_test.estimates[s, source, TARGET_EDGE_PAIR[0]] - clean_test.estimates[s, R, TARGET_EDGE_PAIR[0]]
            else:
                a_true = ATTACK_BIAS.copy()
            oracle_local[D+1:] -= np.einsum("tnp,p->tn", S[D+1:, TARGET_NODE], a_true)
            oracle_global[D+1:] -= np.einsum("tnip,p->tni", S[D+1:], a_true)

            true_err = np.sum((xtest[s, :, None, :] - attacked.estimates[s]) ** 2, axis=-1)
            clean_err = np.sum((xtest[s, :, None, :] - clean_test.estimates[s]) ** 2, axis=-1)
            isolate_err = np.sum((xtest[s, :, None, :] - isolates.estimates[s]) ** 2, axis=-1)
            local_replay_err = np.sum((xtest[s] - rec_drop) ** 2, axis=-1)
            local_filter_err = np.sum((xtest[s] - local) ** 2, axis=-1)
            gls_local_err = np.sum((xtest[s] - corrected_local) ** 2, axis=-1)
            gls_global_err = np.sum((xtest[s, :, None, :] - corrected_global) ** 2, axis=-1)
            oracle_local_err = np.sum((xtest[s] - oracle_local) ** 2, axis=-1)
            oracle_global_err = np.sum((xtest[s, :, None, :] - oracle_global) ** 2, axis=-1)
            end = min(RECOVERY_END + 1, model.cfg["T"] + 1)
            if scenario == "replay_packet":
                source_age = R - source
            else:
                source_age = 0
            packet_rows.append({"scenario": scenario, "seed": int(seed), "send_time": R,
                "source_time": source, "content_age": source_age,
                "replacement_count": int(attacked.injected[s, R]),
                "payload_changed": bool(np.linalg.norm(a_true) > 1e-12),
                "cache_end_time": Q, "detection_time": D,
                "detection_after_cache_end": bool(D > Q)})
            row = {"scenario": scenario, "seed": int(seed), "method": "attack_no_defense",
                   "attack_window_receiver_mse": float(true_err[R+1:end, TARGET_NODE].mean()),
                   "attack_window_network_mse": float(true_err[R+1:end].mean()),
                   "recovery_receiver_mse": float(true_err[D+1:end, TARGET_NODE].mean()),
                   "recovery_network_mse": float(true_err[D+1:end].mean()),
                   "recovery_excess_receiver_mse": float((true_err[D+1:end, TARGET_NODE] - clean_err[D+1:end, TARGET_NODE]).mean()),
                   "recovery_excess_network_mse": float((true_err[D+1:end] - clean_err[D+1:end]).mean()),
                   "attack_offset_norm": float(np.linalg.norm(a_true)), "gls_offset_estimate_norm": float(np.linalg.norm(a_hat)),
                   "gls_offset_error_norm": float(np.linalg.norm(a_hat-a_true)), "lr_score": lr,
                   "correction_triggered": bool(use), "gate_95pct": gate}
            seed_rows.append(row)
            method_errors = {
                "attack_no_defense": (true_err[:, TARGET_NODE], true_err),
                "isolate_after_d": (isolate_err[:, TARGET_NODE], isolate_err),
                "receiver_drop_and_replay": (local_replay_err, None),
                "receiver_local_filter_from_checkpoint": (local_filter_err, None),
                "candidate_gls_receiver_only": (gls_local_err, None),
                "candidate_gls_global_with_correction_broadcast": (gls_global_err[:, TARGET_NODE], gls_global_err),
                "oracle_known_attack_influence_receiver": (oracle_local_err, None),
                "oracle_known_attack_influence_global": (oracle_global_err[:, TARGET_NODE], oracle_global_err),
            }
            for method, (er, en) in method_errors.items():
                receiver_slice = er[D+1:end]
                network_slice = en[D+1:end] if en is not None else None
                case_rows.append({"scenario": scenario, "seed": int(seed), "method": method,
                    "receiver_recovery_mse": float(receiver_slice.mean()),
                    "receiver_clean_mse": float(clean_err[D+1:end, TARGET_NODE].mean()),
                    "receiver_excess_mse": float((receiver_slice-clean_err[D+1:end, TARGET_NODE]).mean()),
                    "network_recovery_mse": float(network_slice.mean()) if network_slice is not None else None,
                    "network_clean_mse": float(clean_err[D+1:end].mean()) if network_slice is not None else None,
                    "network_excess_mse": float((network_slice-clean_err[D+1:end]).mean()) if network_slice is not None else None,
                    "gls_triggered": bool(use) if method.startswith("candidate") else None,
                    "global_correction_resource_note": "one event/edge/time plus 2-D offset broadcast; not implemented or charged" if method == "candidate_gls_global_with_correction_broadcast" else ""})

    # Normal false-correction cost on a separate test split with no attack.
    for s, seed in enumerate(stest):
        z = innovations(clean_test, ytest, model, TARGET_NODE, residual_times)[s].reshape(-1) - mu
        a_hat, _, lr = estimate_attack(z, J, precision)
        use = lr > gate
        err = np.sum((xtest[s, :, None, :] - clean_test.estimates[s]) ** 2, axis=-1)
        adjusted = clean_test.estimates[s, :, TARGET_NODE].copy()
        if use:
            adjusted[D+1:] -= np.einsum("tnp,p->tn", S[D+1:, TARGET_NODE], a_hat)
        adj_err = np.sum((xtest[s] - adjusted) ** 2, axis=-1)
        normal_cor_mat.append({"seed": int(seed), "lr_score": lr, "correction_triggered": bool(use),
            "receiver_normal_mse": float(err[D+1:RECOVERY_END+1, TARGET_NODE].mean()),
            "receiver_corrected_mse": float(adj_err[D+1:RECOVERY_END+1].mean())})

    summary = []
    for scenario in ("single_step", "replay_packet"):
        subset = [r for r in case_rows if r["scenario"] == scenario]
        for method in dict.fromkeys(r["method"] for r in subset):
            rs = [r for r in subset if r["method"] == method]
            summary.append({"scenario": scenario, "method": method, "seeds": len(rs),
                "receiver_recovery_mse_mean": float(np.mean([r["receiver_recovery_mse"] for r in rs])),
                "receiver_excess_mse_mean": float(np.mean([r["receiver_excess_mse"] for r in rs])),
                "network_recovery_mse_mean": float(np.nanmean([np.nan if r["network_recovery_mse"] is None else r["network_recovery_mse"] for r in rs])) if any(r["network_recovery_mse"] is not None for r in rs) else None,
                "network_excess_mse_mean": float(np.nanmean([np.nan if r["network_excess_mse"] is None else r["network_excess_mse"] for r in rs])) if any(r["network_excess_mse"] is not None for r in rs) else None})
    write_json(OUT / "config.json", {"run_id": RUN_ID, "model": model.cfg, "schedule": "exogenous gap8, phase step 1; all methods share it",
        "attack_time": R, "cache_end_time": Q, "detection_time": D, "post_cache_residual_window": [Q+1, D],
        "test_scenarios": ["single_step FDI", "one legal historical packet Replay"],
        "seeds": {"train": TRAIN.tolist(), "calibration": CAL.tolist(), "test": TEST.tolist()},
        "threshold": "95th percentile likelihood improvement on independent clean calibration seeds",
        "exploratory_only": True, "global_correction_requires_extra_broadcast": True})
    write_csv(OUT / "per_seed_methods.csv", case_rows)
    write_csv(OUT / "per_seed_attacks.csv", seed_rows)
    write_csv(OUT / "packet_audit.csv", packet_rows)
    write_csv(OUT / "normal_correction_audit.csv", normal_cor_mat)
    write_json(OUT / "diagnostics.json", {"attack_sensitivity_singular_values": singular.tolist(),
        "unit_response_linearity_max_abs_by_direction": linearity_errors,
        "gate_threshold_95pct": gate, "calibration_clean_trigger_rate": float(np.mean(np.asarray(cal_lr) > gate)),
        "normal_test_trigger_rate": float(np.mean([r["correction_triggered"] for r in normal_cor_mat])),
        "normal_test_mse_change": float(np.mean([r["receiver_corrected_mse"]-r["receiver_normal_mse"] for r in normal_cor_mat])),
        "receiver_replay_matches_original_trace": True,
        "sample_size": len(TEST), "statistical_unit": "independent seed; exploratory screening only"})
    sources = [Path(__file__), SIM / "model.py", SIM / "engine.py", SIM / "config.json", SIM / "reference_exploration_plan.json"]
    write_json(OUT / "source_hashes.json", {p.name: sha256(p) for p in sources})
    write_json(OUT / "summary.json", {"run_id": RUN_ID, "results": summary,
        "elapsed_seconds": time.perf_counter()-started,
        "limitations": ["48 paired test seeds only", "fixed exogenous schedule", "single attack event", "no adaptive schedule feedback", "global correction broadcast unimplemented and uncharged"]})
    print(json.dumps({"run_id": RUN_ID, "summary": summary, "diagnostics": json.loads((OUT/"diagnostics.json").read_text(encoding="utf-8"))}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
