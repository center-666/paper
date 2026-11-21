"""Frozen stage-2 screening/confirmation. No tuning from the generated data."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
from pathlib import Path
import sys
import time

import numpy as np
import scipy
from core import Detectors, NAMES, quant, probabilities, silence, update_error, log_factor, bernoulli_kl

HERE = Path(__file__).resolve().parent
PROTOCOL = HERE / "protocol.json"
METHODS = (*NAMES, "oracle_matched_LR")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write(p, data):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                 encoding="utf8", newline="\n")


class Moments:
    def __init__(self):
        self.data = {}

    def add(self, name, values):
        x = np.asarray(values, dtype=float).reshape(-1)
        old = self.data.setdefault(name, [0, 0., 0.])
        old[0] += x.size
        old[1] += float(x.sum())
        old[2] += float(np.dot(x, x))

    def report(self):
        report = {}
        for key, (n, total, sq) in self.data.items():
            if not n:
                report[key] = {"n": 0, "mean": None, "se": None}
                continue
            var = max(0., (sq - total * total / n) / (n - 1)) if n > 1 else 0.
            report[key] = {"n": n, "mean": total / n, "se": np.sqrt(var / n),
                           "sum": total, "sum_squares": sq}
        return report


def batch(model, b, onset_kind, count, seed, protocol, summaries):
    A, Q, R, Z, delta = (model[k] for k in ("A", "Q", "R", "Z", "delta"))
    streams = [np.random.default_rng(s) for s in np.random.SeedSequence(seed).spawn(4)]
    phys, event, phase_rng, schedule = streams
    onset = (schedule.integers(50, 201, size=count) if isinstance(onset_kind, str)
             else np.full(count, onset_kind, dtype=int))
    end = int(onset.max()) + max(protocol["horizons_after_onset"])
    eh = np.sqrt(model["P0"]) * phys.normal(size=count)
    ea = eh.copy()
    Ph = np.full(count, model["P0"])
    Pa = Ph.copy()
    D = np.zeros(count)
    health = Detectors(count, protocol["candidate_strengths"], protocol["candidate_weights"],
                       protocol["alpha"], protocol["global_horizon_budget"])
    attack = Detectors(count, protocol["candidate_strengths"], protocol["candidate_weights"],
                       protocol["alpha"], protocol["global_horizon_budget"])
    tau_oracle = np.full(count, -1, dtype=np.int32)
    oracle_ll = np.zeros(count)
    cum_kl = np.zeros(count)
    cum_mse = np.zeros(count)
    cum_clean = np.zeros(count)
    cum_bias = np.zeros(count)
    cum_sends = np.zeros(count)
    cum_pre_mse = np.zeros((len(METHODS), count))
    cum_pre_bias = np.zeros_like(cum_pre_mse)
    drift_residual = np.zeros(count)
    max_abs_error = 0.
    max_abs_bias = 0.

    for t in range(end + 1):
        v = np.sqrt(R) * phys.normal(size=count)
        w = np.sqrt(Q) * phys.normal(size=count)
        phase = delta * (2 * phase_rng.random(count) - 1) if t else np.zeros(count)
        # Work relative to the healthy prior center. No exponentially large
        # absolute U1 state is ever formed; physical innovations are exact.
        center_h = quant(0., delta, phase)
        separation = eh - ea
        center_a = quant(separation, delta, phase) - separation
        u = event.random(count)
        sent_h = u > np.exp(-.5 * Z * (eh + v - center_h) ** 2)
        sent_a = u > np.exp(-.5 * Z * (ea + v - center_a) ** 2)

        if t:
            health.step(t, ~sent_h, nu_h, q_h)
            attack.step(t, ~sent_a, nu_a, q_a)
            active_previous = (t - 1) >= onset
            oracle_ll += np.where(active_previous, log_factor(~sent_a, true_p, nu_a), 0.)
            cum_kl += np.where(active_previous, bernoulli_kl(true_p, nu_a), 0.)
            drift_residual += np.where(active_previous, true_p - (~sent_a), 0.)
            newly = (tau_oracle < 0) & (oracle_ll >= np.log(1 / protocol["alpha"]))
            tau_oracle[newly] = t

        tau = np.vstack((attack.tau, tau_oracle))
        for horizon in protocol["horizons_after_onset"]:
            selected = t == onset + horizon
            if not np.any(selected):
                continue
            stats = summaries[horizon]
            target_onset = onset[selected]
            stats.add("monitor_total_MSE", cum_mse[selected])
            stats.add("healthy_total_MSE", cum_clean[selected])
            stats.add("monitor_total_MSE_excess", (cum_mse - cum_clean)[selected])
            stats.add("total_bias_energy", cum_bias[selected])
            stats.add("total_sends", cum_sends[selected])
            stats.add("oracle_conditional_KL", cum_kl[selected])
            stats.add("oracle_log_LR", oracle_ll[selected])
            stats.add("event_minus_expected_residual", drift_residual[selected])
            for i, name in enumerate(METHODS):
                tt = tau[i, selected]
                prefalse = (tt >= 0) & (tt <= target_onset)
                eligible = ~prefalse
                detected = (tt > target_onset) & (tt <= t)
                delay = np.where(detected, tt - target_onset, horizon)
                stats.add(name + "/pre_onset_alarm", prefalse)
                stats.add(name + "/detection_unconditional", detected)
                stats.add(name + "/detection_eligible", detected[eligible])
                stats.add(name + "/restricted_delay_eligible", delay[eligible])
                stats.add(name + "/delay_detected_only", delay[detected])
                stats.add(name + "/pre_MSE", cum_pre_mse[i, selected])
                stats.add(name + "/pre_MSE_eligible", cum_pre_mse[i, selected][eligible])
                stats.add(name + "/pre_bias_energy", cum_pre_bias[i, selected])
                if i < len(NAMES):
                    stats.add(name + "/healthy_alarm_by_endpoint", health.tau[i, selected] >= 0)
            common = ((tau[0, selected] < 0) | (tau[0, selected] > target_onset)) & (
                (tau[3, selected] < 0) | (tau[3, selected] > target_onset))
            stats.add("D3_minus_D0_pre_MSE_common_eligible",
                      (cum_pre_mse[3, selected] - cum_pre_mse[0, selected])[common])

        action = np.where((t >= onset) & sent_a, b, 0.)
        ep_h, Pph, Kh = update_error(eh, Ph, center_h, v, sent_h, 0., model)
        ep_a, Ppa, Ka = update_error(ea, Pa, center_a, v, sent_a, action, model)
        D = (1 - Ka) * A * D - Ka * action
        active = t >= onset
        cum_mse += np.where(active, ep_a ** 2, 0.)
        cum_clean += np.where(active, ep_h ** 2, 0.)
        cum_bias += np.where(active, D ** 2, 0.)
        cum_sends += active & sent_a
        alive = (tau < 0) & active[None, :]
        cum_pre_mse += alive * ep_a[None, :] ** 2
        cum_pre_bias += alive * D[None, :] ** 2
        nu_h, q_h = probabilities(Pph, Kh, sent_h, model, protocol["candidate_strengths"])
        nu_a, q_a = probabilities(Ppa, Ka, sent_a, model, protocol["candidate_strengths"])
        true_p = silence(Ppa, D, model)
        eh, ea = A * ep_h + w, A * ep_a + w
        Ph, Pa = A * A * Pph + Q, A * A * Ppa + Q
        max_abs_error = max(max_abs_error, float(np.max(np.abs(ea))))
        max_abs_bias = max(max_abs_bias, float(np.max(np.abs(D))))
    return {"max_abs_prior_error": max_abs_error, "max_abs_bias": max_abs_bias}


def healthy_batch(model, count, seed, protocol, summaries):
    A, Q, R, Z, delta = (model[k] for k in ("A", "Q", "R", "Z", "delta"))
    phys, event, phase_rng = [
        np.random.default_rng(s) for s in np.random.SeedSequence(seed).spawn(3)]
    e = np.sqrt(model["P0"]) * phys.normal(size=count)
    P = np.full(count, model["P0"])
    horizon = protocol["health_long_horizon"]
    detector = Detectors(count, protocol["candidate_strengths"], protocol["candidate_weights"],
                         protocol["alpha"], horizon)
    for t in range(horizon + 1):
        v = np.sqrt(R) * phys.normal(size=count)
        w = np.sqrt(Q) * phys.normal(size=count)
        phase = delta * (2 * phase_rng.random(count) - 1) if t else np.zeros(count)
        r = quant(0., delta, phase)
        sent = event.random(count) > np.exp(-.5 * Z * (e + v - r) ** 2)
        if t:
            detector.step(t, ~sent, nu, q)
        if t in summaries:
            for i, name in enumerate(NAMES):
                summaries[t].add(name + "/healthy_alarm", detector.tau[i] >= 0)
        ep, Pp, K = update_error(e, P, r, v, sent, 0., model)
        nu, q = probabilities(Pp, K, sent, model, protocol["candidate_strengths"])
        e, P = A * ep + w, A * A * Pp + Q


def check_frozen():
    frozen = json.loads((HERE / "freeze.json").read_text(encoding="utf8"))
    for name, digest in frozen["input_hashes"].items():
        if sha(HERE / name) != digest:
            raise SystemExit("Frozen source changed: " + name)
    return frozen


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["screen", "final", "health_screen", "health_final"])
    parser.add_argument("--model", choices=["S1", "U1"], required=True)
    args = parser.parse_args()
    frozen = check_frozen()
    p = json.loads(PROTOCOL.read_text(encoding="utf8"))
    model = next(m for m in p["models"] if m["id"] == args.model)
    model_id = 0 if args.model == "S1" else 1
    final = args.stage.endswith("final")
    count = p["final_episodes_per_case"] if final else p["screen_episodes_per_case"]
    # Schema and code are identical in screening and independent confirmation.
    run_dir = HERE / "results" / args.stage
    run_dir.mkdir(parents=True, exist_ok=True)
    if args.stage.startswith("health"):
        path = run_dir / f"{args.model}.json"
        if path.exists():
            raise SystemExit("Output exists; refusing overwrite")
        summaries = {h: Moments() for h in (512, 1024, 2048, 8192)}
        started = time.perf_counter()
        for batch_index, start in enumerate(range(0, count, p["batch_size"])):
            n = min(count - start, p["batch_size"])
            seed = [p[args.stage + "_seed"], model_id, batch_index]
            healthy_batch(model, n, seed, p, summaries)
            print(args.stage, args.model, start + n, "/", count, flush=True)
        write(path, {"model": model, "stage": args.stage, "n": count,
                     "seconds": time.perf_counter() - started,
                     "statistics": {str(h): s.report() for h, s in summaries.items()},
                     "frozen_hash": sha(HERE / "freeze.json")})
        return
    for bi, b in enumerate(p["attack_strengths"]):
        for oi, onset in enumerate(p["onsets"]):
            path = run_dir / f"{args.model}_b{b:g}_onset{onset}.json"
            if path.exists():
                print("existing result retained", path.name, flush=True)
                continue
            summaries = {h: Moments() for h in p["horizons_after_onset"]}
            started = time.perf_counter()
            runtime = []
            for batch_index, start in enumerate(range(0, count, p["batch_size"])):
                n = min(count - start, p["batch_size"])
                seed = [p[args.stage + "_seed"], model_id, bi, oi, batch_index]
                runtime.append(batch(model, b, onset, n, seed, p, summaries))
            result = {
                "stage": args.stage, "model": model, "strength": b, "onset": onset,
                "n": count, "seconds": time.perf_counter() - started,
                "statistics": {str(h): s.report() for h, s in summaries.items()},
                "runtime_checks": runtime, "frozen_hash": sha(HERE / "freeze.json"),
                "estimates_unchanged_by_detectors": True,
                "instantaneous_oracle_pre_MSE": 0.0,
                "statistical_unit": "independent episode; correlated timesteps are not separate samples",
            }
            write(path, result)
            print(args.stage, path.name, "done", round(result["seconds"], 2), "s", flush=True)
    write(run_dir / f"{args.model}_complete.json", {
        "status": "COMPLETE", "stage": args.stage, "model": args.model, "cases": 12,
        "n_each": count, "runtime": {"python": sys.version, "numpy": np.__version__,
                                    "scipy": scipy.__version__, "platform": platform.platform()}})


if __name__ == "__main__":
    main()
