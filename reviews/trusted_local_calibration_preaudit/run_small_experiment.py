"""Small paired pilot for trusted-local versus link-residual scale calibration.

Uses the frozen Baseline-Y5 estimator and engine with an external full-send
schedule. All noise generation and scale switching are local to this script.
"""
from __future__ import annotations

import json
import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "simulation"))
from engine import simulate
from model import Model


HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
RESULTS.mkdir(exist_ok=True)
N_CAL = 60
N_VAL = 60
N_TEST = 60
SEEDS = {
    "cal_c1": np.arange(51000, 51000 + N_CAL),
    "cal_step": np.arange(52000, 52000 + N_CAL),
    "val_c1": np.arange(61000, 61000 + N_VAL),
    "val_step": np.arange(62000, 62000 + N_VAL),
    "test_attack_c1": np.arange(71000, 71000 + N_TEST),
    "test_attack_step": np.arange(72000, 72000 + N_TEST),
}
WINDOW = 30
ALPHA_EPISODE = 0.05
ATTACK_BIAS = np.array([0.12, -0.08])
ATTACK_START, ATTACK_END = 200, 249
SCORE_SLICE = slice(ATTACK_START, ATTACK_END + 1)
METHODS = ("fixed_covariance", "oracle_covariance", "link_adaptive", "trusted_local")


def load_config():
    cfg = json.loads((ROOT / "simulation/config.json").read_text(encoding="utf-8"))
    cfg["attack"]["bias"] = ATTACK_BIAS.tolist()
    return cfg


def generate_data(model: Model, seeds: np.ndarray, noise_step: bool):
    cfg = model.cfg
    S, T, N, n = len(seeds), cfg["T"], cfg["N"], cfg["n"]
    x = np.empty((S, T + 1, n))
    y = np.empty((S, T, N, n))
    lp = np.linalg.cholesky(model.P0)
    lq = np.linalg.cholesky(model.Q)
    lr = np.linalg.cholesky(model.R)
    for si, seed in enumerate(seeds):
        rng = np.random.default_rng(int(seed))
        x[si, 0] = lp @ rng.standard_normal(n)
        for t in range(T):
            c = 4.0 if noise_step and t >= ATTACK_START else 1.0
            v = np.einsum("nij,nj->ni", lr, rng.standard_normal((N, n))) * np.sqrt(c)
            w = (lq @ rng.standard_normal(n)) * np.sqrt(c)
            y[si, t] = np.einsum("imn,n->im", model.H, x[si, t]) + v
            x[si, t + 1] = model.A @ x[si, t] + w
    return x, y


def covariance_sequences(model: Model, receiver: int):
    """Exact 12D joint covariance: Yang network + trusted local predictor.

    The measurement noise v_receiver drives both filters, and process noise is
    common to all six error blocks. No independence approximation is used.
    """
    N, n, T = model.cfg["N"], model.cfg["n"], model.cfg["T"]
    C = np.zeros((n, (N+1) * n))
    C[:, 0:n] = np.eye(n)
    C[:, -n:] = -np.eye(n)
    P = np.kron(np.ones((N+1, N+1)), model.P0)
    Pglobal = [P.copy()]
    Plocal = model.P0.copy()
    Plocal_seq = [Plocal.copy()]
    Qjoint = np.kron(np.ones((N+1, N+1)), model.Q)
    S0 = []
    U0 = []
    for t in range(T):
        S0.append(C @ P @ C.T)
        U0.append(model.H[receiver] @ Plocal @ model.H[receiver].T + model.R[receiver])
        Kbar = np.zeros((N*n, N*n))
        Hbar = np.zeros_like(Kbar)
        Rbar = np.zeros_like(Kbar)
        for i in range(N):
            sl = slice(i*n, (i+1)*n)
            Kbar[sl, sl] = model.gains[t, i]
            Hbar[sl, sl] = model.H[i]
            Rbar[sl, sl] = model.R[i]
        Kl = model.local_gains[t, receiver]
        Fl = model.A - Kl @ model.H[receiver]
        F = np.zeros_like(P)
        F[:N*n, :N*n] = np.kron(_mixing(model), model.A) - Kbar @ Hbar
        F[-n:, -n:] = Fl
        V = np.zeros(((N+1)*n, N*n))
        V[:N*n, :] = Kbar
        V[-n:, receiver*n:(receiver+1)*n] = Kl
        P = F @ P @ F.T + Qjoint + V @ Rbar @ V.T
        P = (P + P.T) / 2
        Pglobal.append(P.copy())
        Plocal = Fl @ Plocal @ Fl.T + model.Q + Kl @ model.R[receiver] @ Kl.T
        Plocal = (Plocal + Plocal.T) / 2
        Plocal_seq.append(Plocal.copy())
    return np.asarray(S0), np.asarray(U0), np.asarray(Pglobal), np.asarray(Plocal_seq)


def _mixing(model):
    N = model.cfg["N"]
    mix = np.eye(N)
    for sender, receiver in model.edges:
        mix[receiver, receiver] -= model.cfg["epsilon"]
        mix[receiver, sender] += model.cfg["epsilon"]
    return mix


def exact_scale_covariances(model: Model, noise_step: bool):
    """Healthy covariance oracle for c_t=1 then c_t=4, with frozen gains."""
    N, n, T = model.cfg["N"], model.cfg["n"], model.cfg["T"]
    receiver = int(model.cfg["attack"]["receiver"])
    C = np.zeros((n, (N+1) * n))
    C[:, 0:n] = np.eye(n)
    C[:, -n:] = -np.eye(n)
    P = np.kron(np.ones((N+1, N+1)), model.P0)
    Qjoint = np.kron(np.ones((N+1, N+1)), model.Q)
    Fseq, Wseq = [], []
    for t in range(T):
        Kbar = np.zeros((N*n, N*n))
        Hbar = np.zeros_like(Kbar)
        Rbar = np.zeros_like(Kbar)
        for i in range(N):
            sl = slice(i*n, (i+1)*n)
            Kbar[sl, sl] = model.gains[t, i]
            Hbar[sl, sl] = model.H[i]
            Rbar[sl, sl] = model.R[i]
        Kl = model.local_gains[t, receiver]
        F = np.zeros_like(P)
        F[:N*n, :N*n] = np.kron(_mixing(model), model.A) - Kbar @ Hbar
        F[-n:, -n:] = model.A - Kl @ model.H[receiver]
        V = np.zeros(((N+1)*n, N*n))
        V[:N*n, :] = Kbar
        V[-n:, receiver*n:(receiver+1)*n] = Kl
        W = Qjoint + V @ Rbar @ V.T
        c = 4.0 if noise_step and t >= ATTACK_START else 1.0
        P = F @ P @ F.T + c * W
        P = (P + P.T) / 2
        Fseq.append(F)
        Wseq.append(W)
    S = []
    P = np.kron(np.ones((N+1, N+1)), model.P0)
    S.append(C @ P @ C.T)
    for t in range(T):
        c = 4.0 if noise_step and t >= ATTACK_START else 1.0
        P = Fseq[t] @ P @ Fseq[t].T + c * Wseq[t]
        P = (P + P.T) / 2
        S.append(C @ P @ C.T)
    return np.asarray(S[:T])


def local_reference_innovations(model: Model, y: np.ndarray, receiver: int):
    S, T, n = y.shape[0], model.cfg["T"], model.cfg["n"]
    estimate = np.zeros((S, T + 1, n))
    innovation = np.empty((S, T, n))
    for t in range(T):
        innovation[:, t] = y[:, t, receiver] - estimate[:, t] @ model.H[receiver].T
        estimate[:, t + 1] = (estimate[:, t] @ model.A.T
                              + np.einsum("sij,sj->si", model.local_gains[t, receiver][None].repeat(S, 0), innovation[:, t]))
    return innovation, estimate


def run_pair(model: Model, seeds: np.ndarray, noise_step: bool, attacked: bool):
    x, y = generate_data(model, seeds, noise_step)
    schedule = np.ones((len(seeds), model.cfg["T"], model.cfg["N"]), dtype=bool)
    clean = simulate(model, x, y, seeds, method="yang", scenario="clean", schedule=schedule, collect=False)
    target = clean
    if attacked:
        target = simulate(model, x, y, seeds, method="yang", scenario="step", schedule=schedule, collect=False)
    receiver = int(model.cfg["attack"]["receiver"])
    source = int(model.cfg["attack"]["sender"])
    local_innov, reference = local_reference_innovations(model, y, receiver)
    link_residual = target.estimates[:, :-1, source] - reference[:, :-1]
    if attacked:
        link_residual[:, ATTACK_START:ATTACK_END + 1] += ATTACK_BIAS
    # Check reference against the unmodified engine's local-only Yang mode.
    local_engine = simulate(model, x, y, seeds, method="local", collect=False)
    assert np.max(np.abs(reference-local_engine.estimates[:, :, receiver])) < 1e-12
    return clean, target, link_residual, local_innov, reference


def scores_for(model, pair, S0, U0, S_oracle):
    clean, target, r, u = pair[:4]
    ns, T, d = r.shape
    link_nis = np.empty((ns, T))
    local_nis = np.empty((ns, T))
    fixed = np.empty((ns, T))
    oracle = np.empty((ns, T))
    for t in range(T):
        # At t=0 both estimates are exactly zero. Excluded from all test windows.
        invS0 = np.zeros_like(S0[t]) if t == 0 else np.linalg.inv(S0[t])
        invU0 = np.linalg.inv(U0[t])
        invSoracle = np.zeros_like(S_oracle[t]) if t == 0 else np.linalg.inv(S_oracle[t])
        fixed[:, t] = np.einsum("si,ij,sj->s", r[:, t], invS0, r[:, t])
        oracle[:, t] = np.einsum("si,ij,sj->s", r[:, t], invSoracle, r[:, t])
        link_nis[:, t] = fixed[:, t] / d
        local_nis[:, t] = np.einsum("si,ij,sj->s", u[:, t], invU0, u[:, t]) / d
    c_link = np.ones((ns, T))
    c_local = np.ones((ns, T))
    for t in range(T):
        lo = max(0, t - WINDOW)
        if t > lo:
            c_link[:, t] = np.mean(link_nis[:, lo:t], axis=1)
            c_local[:, t] = np.mean(local_nis[:, lo:t], axis=1)
    scores = {
        "fixed_covariance": fixed,
        "oracle_covariance": oracle,
        "link_adaptive": fixed / np.maximum(c_link, 1e-12),
        "trusted_local": fixed / np.maximum(c_local, 1e-12),
    }
    return scores, c_link, c_local, r, u


def episode_summary(scores, thresholds, label):
    out = {"label": label, "n": int(next(iter(scores.values())).shape[0]), "methods": {}}
    for name, score in scores.items():
        ep = np.max(score[:, SCORE_SLICE], axis=1)
        alarm = ep > thresholds[name]
        delay = []
        for row in score:
            hit = np.flatnonzero(row[SCORE_SLICE] > thresholds[name])
            if len(hit):
                delay.append(int(hit[0]))
        out["methods"][name] = {
            "threshold": float(thresholds[name]),
            "episode_alarms": int(np.sum(alarm)),
            "episode_far_or_pd": float(np.mean(alarm)),
            "mean_delay_if_detected": float(np.mean(delay)) if delay else None,
            "detected_count": int(len(delay)),
            "alarm_slots_per_1000": float(1000*np.mean(score[:, SCORE_SLICE] > thresholds[name])),
            "mean_delay_censored_at_50": float((sum(delay)+(len(ep)-len(delay))*50)/len(ep)),
        }
    return out


def main():
    cfg = load_config()
    model = Model.build(cfg)
    S0, U0, Pbase, Plocal = covariance_sequences(model, cfg["attack"]["receiver"])
    S_oracle_step = exact_scale_covariances(model, noise_step=True)
    S_oracle_static = exact_scale_covariances(model, noise_step=False)
    assert np.max(np.abs(Pbase[:, :10, :10]-model.nominal_covariance)) < 1e-12
    assert np.max(np.abs(Pbase[:, -2:, -2:]-Plocal)) < 1e-12
    assert np.max(np.abs(S_oracle_static-S0)) < 1e-12

    # Independent clean calibration, balanced over nominal and changed-noise runs.
    cal_c1 = run_pair(model, SEEDS["cal_c1"], noise_step=False, attacked=False)
    cal_step = run_pair(model, SEEDS["cal_step"], noise_step=True, attacked=False)
    cal_s1, *_ = scores_for(model, cal_c1, S0, U0, S_oracle_static)
    cal_ss, *_ = scores_for(model, cal_step, S0, U0, S_oracle_step)
    thresholds = {}
    for name in METHODS:
        maxes = np.concatenate([np.max(cal_s1[name][:, SCORE_SLICE], axis=1),
                                np.max(cal_ss[name][:, SCORE_SLICE], axis=1)])
        thresholds[name] = float(np.quantile(maxes, 1 - ALPHA_EPISODE, method="higher"))

    # Independent clean validation and matched attacks.
    val_c1 = run_pair(model, SEEDS["val_c1"], noise_step=False, attacked=False)
    val_step = run_pair(model, SEEDS["val_step"], noise_step=True, attacked=False)
    atk_c1 = run_pair(model, SEEDS["test_attack_c1"], noise_step=False, attacked=True)
    atk_step = run_pair(model, SEEDS["test_attack_step"], noise_step=True, attacked=True)

    val_c1_scores, val_c1_link, val_c1_local, *_ = scores_for(model, val_c1, S0, U0, S_oracle_static)
    val_step_scores, val_step_link, val_step_local, *_ = scores_for(model, val_step, S0, U0, S_oracle_step)
    atk_c1_scores, atk_c1_link, atk_c1_local, _, atk_c1_u = scores_for(model, atk_c1, S0, U0, S_oracle_static)
    atk_step_scores, atk_step_link, atk_step_local, _, atk_step_u = scores_for(model, atk_step, S0, U0, S_oracle_step)

    validation = [episode_summary(val_c1_scores, thresholds, "clean_c1"),
                  episode_summary(val_step_scores, thresholds, "clean_c1_to_c4")]
    attacks = [episode_summary(atk_c1_scores, thresholds, "attack_c1"),
               episode_summary(atk_step_scores, thresholds, "attack_c1_to_c4")]
    # Preserve trajectory-level evidence; no time samples treated as independent trials.
    score_sets = dict(zip(SEEDS, [cal_s1, cal_ss, val_c1_scores, val_step_scores,
                                 atk_c1_scores, atk_step_scores]))
    with (RESULTS/"per_seed_scores.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["split", "seed", "method", "episode_max", "episode_alarm",
                         "alarm_slots", "delay_censored_50"])
        for name, score_set in score_sets.items():
            for method, arr in score_set.items():
                for s, seed in enumerate(SEEDS[name]):
                    hits = arr[s, SCORE_SLICE] > thresholds[method]
                    times = np.flatnonzero(hits)
                    writer.writerow([name, int(seed), method, float(arr[s, SCORE_SLICE].max()),
                                     int(hits.any()), int(hits.sum()), int(times[0]) if len(times) else 50])
    paired_clean, paired_scale_changes = [], {}
    for label, pair, soracle in [("attack_c1", atk_c1, S_oracle_static),
                                ("attack_c1_to_c4", atk_step, S_oracle_step)]:
        clean_r = pair[0].estimates[:, :-1, 0] - pair[4][:, :-1]
        clean_pair = (pair[0], pair[0], clean_r, pair[3], pair[4])
        clean_score, clean_scale, clean_local, *_ = scores_for(model, clean_pair, S0, U0, soracle)
        bad_score, bad_scale, bad_local, *_ = scores_for(model, pair, S0, U0, soracle)
        paired_clean.append(episode_summary(clean_score, thresholds, label+"_paired_clean"))
        paired_scale_changes[label] = {
            "local_scale_max_abs_change": float(np.max(np.abs(clean_local-bad_local))),
            "link_clean_mean_220_249": float(clean_scale[:, 220:250].mean()),
            "link_attack_mean_220_249": float(bad_scale[:, 220:250].mean()),
        }

    # Raw nominal chi-square per-packet false alarm rates in the clean noise step.
    chi2_95_df2 = float(-2 * np.log(0.05))
    raw_step_fars = {}
    for name, score in val_step_scores.items():
        raw_step_fars[name] = float(np.mean(score[:, SCORE_SLICE] > chi2_95_df2))

    # Local reference innovations are computed from paired y and must be bitwise identical.
    # Above validation/test use distinct seeds, so verify equality on explicit paired runs.
    pair_clean = run_pair(model, np.arange(73000, 73000 + 8), noise_step=True, attacked=False)
    pair_attack = run_pair(model, np.arange(73000, 73000 + 8), noise_step=True, attacked=True)
    paired_local_diff = float(np.max(np.abs(pair_clean[3] - pair_attack[3])))

    def attack_scale_ratio(link_scale, local_scale):
        sl = slice(ATTACK_START + 20, ATTACK_END + 1)
        return {"link_scale_mean": float(np.mean(link_scale[:, sl])),
                "trusted_scale_mean": float(np.mean(local_scale[:, sl])),
                "link_scale_median": float(np.median(link_scale[:, sl])),
                "trusted_scale_median": float(np.median(local_scale[:, sl]))}

    result = {
        "study": "trusted local scale calibration small paired pilot",
        "implementation": "v1: received sender estimate minus trusted local reference; v0 invalidated",
        "frozen_baseline_commit": "9901785cf565e3bcfbe814080b04b997fd661377",
        "model": {"N": cfg["N"], "n": cfg["n"], "T": cfg["T"], "A": cfg["A"],
                  "Q": cfg["Q"], "P0": cfg["P0"], "H_scales": cfg["H_scales"],
                  "R_variances": cfg["R_variances"], "epsilon": cfg["epsilon"],
                  "topology": cfg["edges_sender_receiver"], "full_send_schedule": True},
        "noise_step": {"start": ATTACK_START, "Q_and_all_R_scale": 4.0,
                       "initial_P0_not_reset": True},
        "attack": {"link": "0->1", "times": [ATTACK_START, ATTACK_END],
                   "bias": ATTACK_BIAS.tolist(), "per_packet_energy": float(ATTACK_BIAS @ ATTACK_BIAS)},
        "scale_window": WINDOW,
        "episode_alpha_target": ALPHA_EPISODE,
        "seeds": {k: [int(v[0]), int(v[-1]), int(len(v))] for k, v in SEEDS.items()},
        "thresholds_empirical_95pct_episode_max": thresholds,
        "validation": validation,
        "attacks": attacks,
        "paired_clean_attack_seeds": paired_clean,
        "paired_scale_changes": paired_scale_changes,
        "joint_covariance": {"dimension": 12,
            "network_block_error": float(np.max(np.abs(Pbase[:, :10, :10]-model.nominal_covariance))),
            "local_block_error": float(np.max(np.abs(Pbase[:, -2:, -2:]-Plocal))),
            "S0_200": S0[200].tolist(),
            "independence_approximation_200": (Pbase[200, :2, :2]+Plocal[200]).tolist(),
            "Sstep_200": S_oracle_step[200].tolist(),
            "Sstep_201": S_oracle_step[201].tolist()},
        "raw_per_packet_FAR_at_nominal_chi2_df2_95": raw_step_fars,
        "scale_estimates_during_attack_step": attack_scale_ratio(atk_step_link, atk_step_local),
        "scale_estimates_during_attack_c1": attack_scale_ratio(atk_c1_link, atk_c1_local),
        "paired_trusted_local_innovation_max_difference": paired_local_diff,
        "chi2_df2_95_threshold": chi2_95_df2,
        "interpretation_limits": [
            "Pilot uses common multiplicative scaling of all Q and R, plus a single abrupt step; it does not support independent Q/R adaptation claims.",
            "Empirical episode thresholds use 120 independent clean trajectories and are exploratory, not formal false-alarm guarantees.",
            "Gains remain the frozen healthy nominal gains; no event triggering, watermarks, cache, or estimator modification is used.",
        ],
    }
    outpath = RESULTS / "pilot_summary.json"
    outpath.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
    for section in ("validation", "attacks", "paired_clean_attack_seeds"):
        for case in result[section]:
            print(case["label"], {m: v["episode_alarms"] for m,v in case["methods"].items()})
    print("raw_FAR", result["raw_per_packet_FAR_at_nominal_chi2_df2_95"])
    print("scales", paired_scale_changes)
    print("joint_covariance", result["joint_covariance"])


if __name__ == "__main__":
    main()
