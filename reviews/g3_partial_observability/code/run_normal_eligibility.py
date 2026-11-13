"""Exact fixed-schedule G3 normal covariance eligibility; no attack/MC search.

Does not modify the frozen plan or shared simulation modules. The short
deterministic impulse-basis check uses the accepted engine as an independent
reference, not as an input to covariance recursion.
"""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "reviews/g3_partial_observability"
SIM = ROOT / "simulation"
sys.path.insert(0, str(SIM))
from engine import simulate
from model import Model
from check_structure import augmented_matrix


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def schedule_from_plan(cfg, plan):
    com = plan["communication"]
    gaps = com["gap_pattern"]
    positions = np.r_[0, np.cumsum(gaps)[:-1]]
    ticks = np.arange(cfg["T"])
    schedule = np.empty((cfg["T"], cfg["N"]), dtype=bool)
    for node in range(cfg["N"]):
        phase = (positions + node*com["node_phase_step"]) % sum(gaps)
        schedule[:, node] = np.isin(ticks % sum(gaps), phase)
    if com["t0_all_nodes_send"]:
        schedule[0] = True
    return schedule


def noise_covariance(model, gain):
    N, n, E = model.cfg["N"], model.cfg["n"], len(model.edges)
    # The SAME process noise enters every node and every pre-receive cache.
    W = np.kron(np.ones((N+E, N+E)), model.Q)
    for node in range(N):
        sl = slice(node*n, (node+1)*n)
        W[sl, sl] += gain[node] @ model.R[node] @ gain[node].T
    return W


def node_traces(P, N, n):
    return np.asarray([np.trace(P[i*n:(i+1)*n, i*n:(i+1)*n]) for i in range(N)])


def exact_covariances(model, schedule):
    N, n, E, T = model.cfg["N"], model.cfg["n"], len(model.edges), model.cfg["T"]
    P = np.kron(np.ones((N+E, N+E)), model.P0)
    full = [P.copy()]
    traces = [node_traces(P, N, n)]
    minimum_eigenvalue = float(np.linalg.eigvalsh(P).min())
    localP = np.kron(np.ones((N, N)), model.P0)
    local_traces = [node_traces(localP, N, n)]
    for t in range(T):
        fresh = schedule[t, model.edges[:, 0]]
        M = augmented_matrix(model.A, model.H, model.gains[t], model.edges, fresh, model.cfg["epsilon"])
        P = M @ P @ M.T + noise_covariance(model, model.gains[t])
        P = (P + P.T)/2
        minimum_eigenvalue = min(minimum_eigenvalue, float(np.linalg.eigvalsh(P).min()))
        full.append(P.copy())
        traces.append(node_traces(P, N, n))
        F = np.zeros((N*n, N*n))
        W = np.kron(np.ones((N, N)), model.Q)
        for node in range(N):
            sl = slice(node*n, (node+1)*n)
            K = model.local_gains[t, node]
            F[sl, sl] = model.A-K@model.H[node]
            W[sl, sl] += K@model.R[node]@K.T
        localP = F@localP@F.T+W
        localP = (localP+localP.T)/2
        local_traces.append(node_traces(localP, N, n))
    return np.asarray(full), np.asarray(traces), np.asarray(local_traces), minimum_eigenvalue


def deterministic_basis_check(model, schedule, exact, horizon=8):
    """Sum independent unit-noise impulse outer products, not random sampling.

    All 2 + horizon*(2+5*2) independent x0/w/v basis directions are propagated
    in the actual accepted engine. Future noises are zero. Their summed outer
    products exactly reconstruct the finite-horizon covariance.
    """
    cfg = copy.deepcopy(model.cfg)
    cfg["T"] = horizon
    small = Model.build(cfg)
    N, n, E = cfg["N"], cfg["n"], len(model.edges)
    count = n+horizon*(n+N*n)
    initial = np.zeros((count, n))
    process = np.zeros((count, horizon, n))
    measurements = np.zeros((count, horizon, N, n))
    initial[:n] = np.linalg.cholesky(model.P0).T
    cursor = n
    for t in range(horizon):
        process[cursor:cursor+n, t] = np.linalg.cholesky(model.Q).T
        cursor += n
        for node in range(N):
            measurements[cursor:cursor+n, t, node] = np.linalg.cholesky(model.R[node]).T
            cursor += n
    assert cursor == count
    x = np.empty((count, horizon+1, n))
    y = np.empty((count, horizon, N, n))
    x[:, 0] = initial
    for t in range(horizon):
        y[:, t] = np.einsum("imn,sn->sim", model.H, x[:, t])+measurements[:, t]
        x[:, t+1] = x[:, t]@model.A.T+process[:, t]
    # These IDs only instantiate unused protection RNGs in clean raw Yang;
    # no stochastic state/noise seed or preregistered pilot seed is used.
    ids = np.arange(19000000, 19000000+count)
    sends = np.broadcast_to(schedule[None, :horizon], (count, horizon, N)).copy()
    run = simulate(small, x, y, ids, "yang", schedule=sends, collect=False)
    assert np.array_equal(run.sends, sends)
    assert np.max(np.abs(small.gains-model.gains[:horizon])) < 1e-14
    payload = np.zeros((count, E, n))
    last_receive = np.full(E, -1, dtype=int)
    rows = []
    z0 = np.tile(initial, (1, N+E))
    maxerror = float(np.max(np.abs(z0.T@z0-exact[0])))
    for t in range(horizon):
        fresh = schedule[t, model.edges[:, 0]]
        payload[:, fresh] = run.estimates[:, t, model.edges[fresh, 0]]
        last_receive[fresh] = t
        age = np.where(last_receive >= 0, t-last_receive, 0)
        aligned = np.einsum("eij,sej->sei", model.powers[age], payload)
        # e_next and c_next share precisely the same process-noise realization.
        estimates_error = x[:, t+1, None]-run.estimates[:, t+1]
        next_cache_error = x[:, t+1, None]-aligned@model.A.T
        z = np.concatenate((estimates_error.reshape(count, N*n), next_cache_error.reshape(count, E*n)), axis=1)
        gram = z.T@z
        error = float(np.max(np.abs(gram-exact[t+1])))
        maxerror = max(maxerror, error)
        rows.append({"state_index": t+1, "deterministic_source_count": count,
                     "all_covariance_blocks_max_absolute_error": error,
                     "fresh_edge_count": int(fresh.sum())})
    assert maxerror <= 1e-10, maxerror
    return rows, maxerror, count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="2026-11-13_g3_normal_eligibility_r01")
    args = parser.parse_args()
    if Path(args.run_id).name != args.run_id:
        raise ValueError("Run ID must be one directory name")
    out = BASE / "results" / args.run_id
    out.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    plan_path = BASE / "plan.json"
    dependency_paths = [plan_path, SIM/"model.py", SIM/"engine.py", BASE/"code/check_structure.py",
                        ROOT/"simulation/g2_runs/2026-11-13_g2_replay_effectiveness_v3/config.json"]
    protected = {str(p.relative_to(ROOT)).replace("\\", "/"): sha(p) for p in dependency_paths}
    write(out/"protected_source_hashes_before.json", protected)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    write(out/"plan_snapshot.json", plan)
    basecfg = json.loads(dependency_paths[-1].read_text(encoding="utf-8"))
    model_cfg = plan["model"]
    for key in ("N", "n", "T", "A", "Q", "P0", "R_variances", "edges_sender_receiver", "epsilon", "warmup"):
        basecfg[key] = copy.deepcopy(model_cfg[key])
    write(out/"preregistration.json", {"run_id": args.run_id,
        "parent_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "plan_sha256": sha(plan_path), "registered_before_computation": True,
        "stage": "exact normal eligibility only", "seed_sampling": "none; deterministic impulse-basis verification only",
        "tail_ratio_limit": 1.10, "eigenvalue_roundoff_tolerance": -1e-9,
        "deterministic_basis_max_error_tolerance": 1e-10,
        "no_attack_detector_or_calibration_runs": True})
    allrows, checks, summaries = [], [], []
    for name, H in (("partial", model_cfg["partial_H"]), ("full_rank_reference", model_cfg["full_rank_reference_H"])):
        cfg = copy.deepcopy(basecfg)
        cfg["H_matrices"] = copy.deepcopy(H)
        write(out/(name+"_config.json"), cfg)
        model = Model.build(cfg)
        schedule = schedule_from_plan(cfg, plan)
        full, traces, local, min_eigenvalue = exact_covariances(model, schedule)
        basis_rows, max_error, basis_count = deterministic_basis_check(model, schedule, full)
        for row in basis_rows:
            checks.append({"geometry": name, **row})
        receiver = plan["metrics"]["primary_receiver"]
        receiver_ratio = float(traces[350:400, receiver].mean()/traces[300:350, receiver].mean())
        network_ratio = float(traces[350:400].mean()/traces[300:350].mean())
        finite = bool(np.isfinite(full).all())
        psd = min_eigenvalue >= -1e-9
        passed = finite and psd and receiver_ratio <= 1.10 and network_ratio <= 1.10
        a, b = plan["metrics"]["normal_window"]
        summaries.append({"geometry": name, "finite": finite, "psd_roundoff_pass": psd,
            "min_augmented_covariance_eigenvalue": min_eigenvalue,
            "receiver_tail_ratio": receiver_ratio, "network_tail_ratio": network_ratio,
            "tail_ratio_limit": 1.10, "normal_covariance_eligibility_passed": passed,
            "exact_normal_receiver_mse": float(traces[a:b+1, receiver].mean()),
            "exact_normal_local_receiver_mse": float(local[a:b+1, receiver].mean()),
            "exact_normal_cooperation_relative_gain": float(1-traces[a:b+1, receiver].mean()/local[a:b+1, receiver].mean()),
            "cooperation_gate_status": "not evaluated: preregistered seed-bootstrap gate requires independent pilot/confirm",
            "deterministic_basis_covariance_error": max_error, "deterministic_basis_source_count": basis_count})
        for t in range(cfg["T"]+1):
            row = {"geometry": name, "state_index": t,
                "receiver_mse": float(traces[t, receiver]), "network_mse": float(traces[t].mean()),
                "local_receiver_mse": float(local[t, receiver]), "local_network_mse": float(local[t].mean())}
            for node in range(cfg["N"]):
                row[f"node{node}_mse"] = float(traces[t, node])
            allrows.append(row)
        # Full joint matrices and gains allow audit of all off-diagonal blocks.
        np.savez_compressed(out/(name+"_exact_covariance.npz"), covariance=full, node_mse=traces,
            local_node_mse=local, gains=model.gains, local_gains=model.local_gains, schedule=schedule)
    write_csv(out/"exact_mse_by_state.csv", allrows)
    write_csv(out/"deterministic_basis_checks.csv", checks)
    write(out/"summary.json", {"run_id": args.run_id, "normal_eligibility": summaries,
        "simulation_scope": "Only deterministic independent impulse bases in an 8-update engine check; no random trajectories or attack trials",
        "calibration": "not run", "pilot": "not run", "confirm": "not run", "gate_A": "not run", "gate_B": "not run",
        "elapsed_seconds": time.perf_counter()-started,
        "failure_classification": "normal finite-window covariance qualification failed" if not summaries[0]["normal_covariance_eligibility_passed"] else None,
        "does_not_establish": ["asymptotic stability or instability", "defense gap", "no value of partially observable research", "Gate A or B success"]})
    after = {str(p.relative_to(ROOT)).replace("\\", "/"): sha(p) for p in dependency_paths}
    assert protected == after
    write(out/"protected_source_hashes_after.json", after)
    write(out/"source_version.json", {"script_sha256": sha(Path(__file__)), "numpy": np.__version__,
        "plan_sha256": sha(plan_path), "all_protected_sources_unchanged": True})
    write(out/"output_hashes.json", {p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file()})
    print(json.dumps(summaries, ensure_ascii=False))


if __name__ == "__main__":
    main()
