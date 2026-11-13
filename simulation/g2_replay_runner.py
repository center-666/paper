"""Small, paired closed-loop Replay screen for G2.

The selector callback receives only a current transmitted packet, earlier
captured packets, the last delivered payload, timing, public A/H and its own
random coin. It never receives receiver measurements, estimates or true state.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import shutil
import sys
import time
import traceback
from pathlib import Path

import numpy as np
from scipy import stats

from cache_monitor import CacheMonitor, CacheEpisode
from cache_screen import MonitorController
from calibration import Calibration, fit_control, interval_bins, quadratic
from engine import simulate
from model import Model, generate_data
from run_study import write_csv, write_json
from sequential_cache import PhaseStatistics, SequentialController, PHASES, phase_rates, retune_multipliers


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "2026-11-13_g2_replay_effectiveness_v3"
PLAN_PATH = ROOT / "reviews/fdi_replay_20261112/g2_screen_plan.json"
SELECTOR_IMPLEMENTATIONS = {
    "fixed_lag8": ("fixed_lag8", None),
    "random_history": ("random_history", None),
    "nearest_current_sender": ("nearest_current", None),
    "risk_greedy_forced_fallback": ("risk_greedy_forced", 1.0),
    "risk_greedy_natural_budget_0.25": ("risk_greedy_natural", 0.25),
    "risk_greedy_natural_budget_1.0": ("risk_greedy_natural", 1.0),
}
METHOD_IMPLEMENTATIONS = {
    "raw_yang_no_cap": "raw_yang",
    "cap_only": "cap_only",
    "zhou_random_protection": "zhou_random",
    "spatial_hard": "spatial_hard",
    "episode_prefix_mean": "episode_mean",
    "energy_cusum": "energy_cusum",
}


def repeated_schedule(cfg, count, gaps, phase_step):
    period = sum(gaps)
    positions = np.r_[0, np.cumsum(gaps)[:-1]]
    schedule = np.zeros((count, cfg["T"], cfg["N"]), dtype=bool)
    ticks = np.arange(cfg["T"])
    for node in range(cfg["N"]):
        phase = (positions + node * phase_step) % period
        schedule[:, :, node] = np.isin(ticks % period, phase)
    schedule[:, 0] = True
    return schedule


class ReplaySelector:
    def __init__(self, mode, calibration, edge, cfg, budget=None):
        self.mode = mode
        self.calibration = calibration
        self.edge = int(edge)
        self.cfg = cfg
        self.budget = budget

    def __call__(self, t, current, history_times, history_values,
                 last_delivered, delta, A, H_receiver, A_delta, rng):
        if not len(history_times):
            return None
        history_times = history_times[-64:]
        history_values = history_values[-64:]
        if np.any(history_times >= t):
            raise AssertionError("history contains a non-historical packet")
        if self.mode == "fixed_lag8":
            return int(history_times[max(0, len(history_times) - 8)])
        if self.mode == "random_history":
            return int(history_times[int(rng.integers(len(history_times)))])

        displacement = history_values - current
        if self.mode == "nearest_current":
            index = int(np.argmin(np.sum(displacement * displacement, axis=1)))
            return int(history_times[index])

        projected = displacement @ H_receiver.T
        spatial = quadratic(projected, np.zeros(projected.shape[-1]),
                            self.calibration.space_precision[self.edge])
        spatial = spatial / self.calibration.space_q[self.edge]
        time_bin = int(interval_bins(np.asarray(delta), self.cfg))
        time_residual = history_values - A_delta @ last_delivered
        temporal = quadratic(time_residual, self.calibration.time_mu[self.edge, time_bin],
                             self.calibration.time_precision[self.edge, time_bin])
        temporal = temporal / self.calibration.time_q[self.edge, time_bin]
        magnitude = np.sum((displacement @ A.T) ** 2, axis=1)
        eligible = (spatial <= float(self.budget)) & (temporal <= 1.0)
        if np.any(eligible):
            candidates = np.flatnonzero(eligible)
            index = int(candidates[np.argmax(magnitude[candidates])])
        elif self.mode == "risk_greedy_forced":
            combined = spatial + temporal
            candidates = np.flatnonzero(np.isclose(combined, combined.min(), rtol=1e-12, atol=1e-12))
            index = int(candidates[np.argmax(magnitude[candidates])])
        else:
            return None
        return int(history_times[index])


class AlarmCapture:
    def __init__(self, inner, seeds, horizon, edges):
        self.inner = inner
        self.alarm = np.zeros((seeds, horizon, edges), dtype=bool)

    def update(self, t, fresh, age, aligned, measurement, local_hat):
        weight = self.inner.update(t, fresh, age, aligned, measurement, local_hat)
        bad = getattr(self.inner, "bad", None)
        if bad is not None:
            self.alarm[:, t] = np.asarray(bad, bool)
        return weight

    def finish(self):
        if hasattr(self.inner, "finish"):
            return self.inner.finish()
        return None


class AgeMeanMonitor(MonitorController):
    def __init__(self, model, statistics):
        super().__init__(model, statistics, "mean_cache", 1.0)
        self.half_life = 4.0

    def update(self, t, fresh, age, aligned, measurement, local_hat):
        return super().update(t, fresh, age, aligned, measurement, local_hat) * np.exp(-np.log(2) * age / self.half_life)


def load_phase_statistics(path):
    with np.load(path) as f:
        meta = json.loads(str(f["metadata"]))
        obj = PhaseStatistics(meta["E"], meta["m"], meta["max_length"], meta["warmup"],
                              meta["window"], meta["signed_reference"])
        obj.counts = meta["counts"]
        for method in obj.thresholds:
            key = "threshold_" + method
            if key in f.files:
                obj.thresholds[method] = f[key].copy()
        for row in obj.counts:
            phase = PHASES.index(row["phase"])
            edge, length = row["edge"], row["length"]
            prefix = f"p{phase}_e{edge}_l{length}_"
            fit = {k[len(prefix):]: f[k].copy() for k in f.files if k.startswith(prefix)}
            fit.update(fallback=row["fallback"], train_count=row["train_count"])
            obj.models[phase, edge, length] = fit
        return obj


def build_model(plan):
    cfg = json.loads((ROOT / "simulation/config.json").read_text(encoding="utf-8"))
    model_spec = plan["model"]
    cfg.update(A=model_spec["A"], Q=model_spec["Q"], P0=model_spec["P0"],
               H_matrices=model_spec["H_matrices"], R_variances=model_spec["measurement_variances"])
    cfg["T"] = int(model_spec["horizon"])
    cfg["cache_schedule_pattern"] = plan["communication"]["schedules"]["irregular"]
    cfg["cache_schedule_phase"] = plan["communication"]["node_phase_step"]
    sender, receiver = model_spec["primary_attack_edge"]
    cfg["attack"].update(sender=int(sender), receiver=int(receiver),
                          start=int(model_spec["attack_interval_inclusive"][0]),
                          end_inclusive=int(model_spec["attack_interval_inclusive"][1]))
    return Model.build(cfg)


def frozen_plan_parts(plan):
    if plan.get("run_id") != "2026-11-12_g2_replay_effectiveness_v1":
        raise ValueError("Unexpected frozen G2 plan identifier")
    selector_names = tuple(x for x in plan["replay_selectors"] if x != "no_attack")
    method_names = tuple(plan["defenses"])
    if set(selector_names) != set(SELECTOR_IMPLEMENTATIONS):
        raise ValueError("Frozen selector list has no exact implementation mapping")
    if set(method_names) != set(METHOD_IMPLEMENTATIONS):
        raise ValueError("Frozen defense list has no exact implementation mapping")
    splits = {name.removesuffix("_seeds"): spec for name, spec in plan["calibration"].items()
              if name.endswith("_seeds") and isinstance(spec, dict) and {"start", "count"} <= set(spec)}
    required_splits = {"train", "calibration", "design", "tune", "normal_audit", "test"}
    if set(splits) != required_splits:
        raise ValueError(f"Frozen seed splits mismatch: {sorted(splits)}")
    if not plan["communication"]["same_schedule_for_every_selector_and_defense"]:
        raise ValueError("G2 requires one common exogenous schedule")
    return selector_names, method_names, splits


def collect_normal_episodes(model, x, y, seeds, schedule, cap):
    collector = SequentialController(model, half_life=4, record_residuals=True)
    run = simulate(model, x, y, seeds, "capped", schedule=schedule, cap=cap,
                   cache_monitor=collector, collect=True)
    episodes = collector.finish()
    return run, episodes


def episode_fpr(alarm, sends, model, edge, warmup=0):
    sender = int(model.edges[edge, 0])
    records = []
    for trial in range(len(sends)):
        times = np.flatnonzero(sends[trial, :, sender])
        for idx, start in enumerate(times):
            complete = idx + 1 < len(times)
            stop = int(times[idx + 1]) if complete else sends.shape[1]
            if not complete or start < warmup:
                continue
            records.append({"trial": trial, "start": int(start), "length": stop - int(start),
                            "alarm": bool(np.any(alarm[trial, start:stop, edge])), "complete": True})
    rate = float(np.mean([r["alarm"] for r in records])) if records else float("nan")
    return rate, records


def attack_packet_records(model, run, seeds, schedule, selector, method):
    target = int(np.flatnonzero(np.all(model.edges == [model.cfg["attack"]["sender"], model.cfg["attack"]["receiver"]], axis=1))[0])
    sender = model.cfg["attack"]["sender"]
    attack = model.cfg["attack"]
    result = []
    for trial, seed in enumerate(seeds):
        times = [int(t) for t in np.flatnonzero(schedule[trial, :, sender])]
        delivered_source = None
        previous_receive = None
        previous_replayed = False
        for t in times:
            source = int(run.replay_source[trial, t])
            replaced = bool(run.injected[trial, t])
            if previous_receive is None:
                previous_receive = t
                delivered_source = t
                previous_replayed = False
                continue
            gap = t - previous_receive
            if attack["start"] <= t <= attack["end_inclusive"]:
                payload_changed = False
                age = None
                if replaced:
                    age = t - source
                    payload_changed = bool(np.linalg.norm(run.estimates[trial, t, sender] - run.estimates[trial, source, sender]) > 1e-12)
                    if not (0 <= source < t and schedule[trial, source, sender]):
                        raise AssertionError("selected source is not a prior transmitted sender packet")
                delivered = source if replaced else t
                source_gap = delivered - int(delivered_source)
                result.append({
                    "seed": int(seed), "selector": selector, "method": method,
                    "time": t, "target_edge": target,
                    "send_opportunity": True, "replacement_attempted": replaced,
                    "payload_changed": payload_changed, "source_time": source if replaced else -1,
                    "content_age": age if replaced else 0, "receiver_gap": gap,
                    "delivered_source_gap": source_gap,
                    "matched_gap": bool(source_gap == gap),
                    "consecutive_historical_fragment": bool(replaced and previous_replayed and source_gap == gap),
                })
            delivered_source = source if replaced else t
            previous_replayed = replaced
            previous_receive = t
    return result


def alarms_for_run(method, run, alarm_capture):
    if alarm_capture is not None:
        return alarm_capture.alarm
    if method == "interval_scale":
        return run.weights < 0.5
    if method in {"zhou_random", "spatial_hard"}:
        return run.weights <= 0.5
    return np.zeros_like(run.weights, dtype=bool)


def run_method(model, x, y, seeds, schedule, method, selector=None,
               calibration=None, controls=None, cap=np.inf,
               cache_statistics=None, phase_statistics=None):
    controls = controls or {}
    monitor = None
    actual_method = method
    if method == "raw_yang":
        actual_method, ctrl, fit, bound = "yang", 1.0, None, np.inf
    elif method == "cap_only":
        actual_method, ctrl, fit, bound = "capped", 1.0, None, cap
    elif method == "zhou_random":
        ctrl, fit, bound = controls[method], None, cap
    elif method in {"spatial_hard", "interval_scale"}:
        ctrl, fit, bound = controls[method], calibration, cap
    elif method == "episode_mean":
        actual_method, ctrl, fit, bound = "capped", 1.0, None, cap
        monitor = AlarmCapture(AgeMeanMonitor(model, cache_statistics), len(seeds), model.cfg["T"], len(model.edges))
    elif method == "energy_cusum":
        actual_method, ctrl, fit, bound = "capped", 1.0, None, cap
        monitor = AlarmCapture(SequentialController(model, phase_statistics, "white_cusum",
            controls[method], 4.0, carry_across_packets=True), len(seeds), model.cfg["T"], len(model.edges))
    elif method == "local":
        actual_method, ctrl, fit, bound = "local", 1.0, None, np.inf
    else:
        raise ValueError(method)
    run = simulate(model, x, y, seeds, actual_method,
                   scenario="replay_selector" if selector is not None else "clean",
                   schedule=schedule, calibration=fit, control=ctrl, cap=bound,
                   collect=False, cache_monitor=monitor, replay_selector=selector)
    alarm = alarms_for_run(method, run, monitor)
    if monitor is not None:
        monitor.finish()
    return run, alarm


def errors(model, run, x):
    return np.sum((run.estimates - x[:, :, None, :]) ** 2, axis=-1)


def recovery_duration(error, clean_error, last_attack_time, start, horizon, receiver, tolerance=0.1, streak=5):
    if last_attack_time is None:
        return 0, False
    first = last_attack_time + 1
    for t in range(max(first, start), horizon - streak + 1):
        e = np.sqrt(error[t:t + streak, receiver])
        c = np.sqrt(clean_error[t:t + streak, receiver])
        if np.all(e <= c + tolerance):
            return t - first, False
    return max(0, horizon - first), True


def cache_lifecycle(run, trial, sender, attack_start, attack_end):
    T = run.estimates.shape[1] - 1
    times = np.arange(T)
    attacked = np.flatnonzero(run.injected[trial] & (times >= attack_start) & (times <= attack_end))
    if not len(attacked):
        return None, None, None
    first, last = int(attacked[0]), int(attacked[-1])
    following = np.flatnonzero(run.sends[trial, last + 1:, sender])
    cache_exit = int(last + 1 + following[0]) if len(following) else None
    return first, last, cache_exit


def error_window_metrics(error, clean_error, receiver, start, stop):
    start = max(0, int(start))
    stop = min(error.shape[0], int(stop))
    if stop <= start:
        return {"state_count": 0, "receiver_mse": None, "receiver_clean_mse": None,
                "receiver_excess_mse": None, "receiver_cumulative_excess": 0.0,
                "network_mse": None, "network_clean_mse": None,
                "network_excess_mse": None, "network_cumulative_excess": 0.0}
    e = error[start:stop]
    c = clean_error[start:stop]
    rd = e[:, receiver] - c[:, receiver]
    nd = e.mean(axis=1) - c.mean(axis=1)
    return {"state_count": stop - start,
            "receiver_mse": float(e[:, receiver].mean()),
            "receiver_clean_mse": float(c[:, receiver].mean()),
            "receiver_excess_mse": float(rd.mean()),
            "receiver_cumulative_excess": float(rd.sum()),
            "network_mse": float(e.mean()),
            "network_clean_mse": float(c.mean()),
            "network_excess_mse": float(nd.mean()),
            "network_cumulative_excess": float(nd.sum())}


def paired_ci(values):
    values = np.asarray(values, float)
    n = len(values)
    mean = float(values.mean())
    if n < 2:
        return mean, None, None
    half = float(stats.t.ppf(0.975, n - 1) * values.std(ddof=1) / math.sqrt(n))
    return mean, mean - half, mean + half


def main(out_path):
    out = Path(out_path)
    if out.exists():
        raise FileExistsError("Run ID exists; preserve all existing results")
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    selector_names, method_names, splits = frozen_plan_parts(plan)
    out.mkdir(parents=True)
    model = build_model(plan)
    cfg = model.cfg
    schedule_info = plan["communication"]["schedules"]["irregular"]
    gap_schedule = repeated_schedule(cfg, 1, schedule_info, plan["communication"]["node_phase_step"])[0]
    edge = int(np.flatnonzero(np.all(model.edges == [0, 1], axis=1))[0])
    sender, receiver = 0, 1

    # Separate normal-data splits; the final attack seeds are never used to fit controls.
    seed_sets = {name: np.arange(spec["start"], spec["start"] + spec["count"], dtype=int)
                 for name, spec in splits.items()}
    data = {}
    for name, seeds in seed_sets.items():
        x, y = generate_data(model, seeds)
        schedule = np.broadcast_to(gap_schedule, (len(seeds),) + gap_schedule.shape).copy()
        data[name] = (x, y, seeds, schedule)

    started = time.perf_counter()
    tx, ty, ts, tsch = data["train"]
    raw_train = simulate(model, tx, ty, ts, "yang", schedule=tsch, collect=True)
    cap = float(np.quantile(raw_train.cap_norms.ravel(), cfg["cap_quantile"], method="higher"))
    train_run, train_eps = collect_normal_episodes(model, tx, ty, ts, tsch, cap)
    cx, cy, cs, csch = data["calibration"]
    cal_run, cal_eps = collect_normal_episodes(model, cx, cy, cs, csch, cap)
    train_cache_episodes = [CacheEpisode(int(ep.edge), ep.residuals) for ep in train_eps if ep.complete]
    calibration_cache_episodes = [CacheEpisode(int(ep.edge), ep.residuals) for ep in cal_eps if ep.complete]
    cache_statistics = CacheMonitor.fit(
        train_cache_episodes, calibration_cache_episodes,
        dict(enumerate(model.H[model.edges[:, 1]])), model.A,
        max_age=cfg["max_interval"] - 1, min_samples=40,
        ridge_relative=cfg["covariance_ridge_relative"], false_alarm_target=0.05)
    phase_statistics = PhaseStatistics.fit(
        train_eps, cal_eps, len(model.edges), cfg["n"], cfg["max_interval"], cfg["warmup"],
        window=4, signed_reference=0.5, ridge=cfg["covariance_ridge_relative"])
    calibration = Calibration.fit(train_run.observations, cal_run.observations, cfg, "interval_scale")

    # Independent design split determines the static thresholds and CUSUM multipliers.
    dx, dy, ds, dsch = data["design"]
    design_run, design_eps = collect_normal_episodes(model, dx, dy, ds, dsch, cap)
    target_obs = {k: v[design_run.observations["edge"] == edge] for k, v in design_run.observations.items()}
    controls = {
        "spatial_hard": fit_control("spatial_hard", target_obs, calibration, cfg),
        "zhou_random": fit_control("zhou_random", target_obs, calibration, cfg),
        "episode_mean": 1.0,
    }
    tune_x, tune_y, tune_s, tune_sched = data["tune"]
    multipliers = np.ones(3)
    tuning = []
    for iteration in range(4):
        detector = SequentialController(model, phase_statistics, "white_cusum", multipliers,
                                        4.0, carry_across_packets=True)
        simulate(model, tune_x, tune_y, tune_s, "capped", schedule=tune_sched, cap=cap,
                 cache_monitor=detector, collect=False)
        episodes = detector.finish()
        rates = phase_rates(episodes, cfg["warmup"])
        tuning.append({"iteration": iteration, "multipliers": multipliers.tolist(), "rates": rates})
        multipliers = retune_multipliers(episodes, cfg["warmup"])
    controls["energy_cusum"] = multipliers

    run_sources = {
        "engine.py": ROOT / "simulation/engine.py",
        "model.py": ROOT / "simulation/model.py",
        "calibration.py": ROOT / "simulation/calibration.py",
        "cache_monitor.py": ROOT / "simulation/cache_monitor.py",
        "cache_screen.py": ROOT / "simulation/cache_screen.py",
        "sequential_cache.py": ROOT / "simulation/sequential_cache.py",
        "g2_replay_runner.py": Path(__file__),
        "g2_screen_plan.json": PLAN_PATH,
    }
    write_json(out / "plan.json", plan)
    write_json(out / "config.json", cfg)
    write_json(out / "seeds.json", {k: v.tolist() for k, v in seed_sets.items()})
    write_json(out / "controls.json", {"cap": cap, **{k: float(v) if np.isscalar(v) else np.asarray(v).tolist() for k, v in controls.items()}, "threshold_tuning": tuning})
    write_json(out / "code_hashes.json", {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in run_sources.items()})
    calibration.save(out / "interval_scale_calibration.npz")
    cache_statistics.save(out / "cache_statistics.npz")
    phase_statistics.save(out / "phase_statistics.npz")

    audit_rows = []
    audit_x, audit_y, audit_s, audit_sched = data["normal_audit"]
    audit_runs = {}
    internal_methods = tuple(METHOD_IMPLEMENTATIONS[name] for name in method_names)
    method_labels = {METHOD_IMPLEMENTATIONS[name]: name for name in method_names}
    for method in internal_methods + ("local",):
        result, alarm = run_method(model, audit_x, audit_y, audit_s, audit_sched, method,
            calibration=calibration, controls=controls, cap=cap,
            cache_statistics=cache_statistics, phase_statistics=phase_statistics)
        audit_runs[method] = result
        fpr, records = episode_fpr(alarm, result.sends, model, edge, cfg["warmup"])
        err = errors(model, result, audit_x)
        audit_rows.append({"method": method_labels.get(method, method), "seed_count": len(audit_s), "complete_target_episodes": len(records),
            "right_censored_target_episodes": int(len(audit_s)), "episode_false_isolation": fpr,
            "normal_receiver_mse": float(err[:, cfg["warmup"] + 1:, receiver].mean()),
            "normal_network_mse": float(err[:, cfg["warmup"] + 1:].mean()),
            "mean_packets": float(result.sends.sum(axis=(1, 2)).mean()),
            "mean_edge_messages": float(result.sends[:, :, model.edges[:, 0]].sum(axis=(1, 2)).mean()),
            "payload_bytes_per_seed": float(result.sends[:, :, model.edges[:, 0]].sum(axis=(1, 2)).mean() * cfg["n"] * 8)})
    write_csv(out / "normal_audit.csv", audit_rows)

    # A small, independent pilot estimates whether 48 test seeds could resolve a 1% claim.
    pilot_clean, _ = run_method(model, dx, dy, ds, dsch, "raw_yang", cap=cap)
    pilot_attack, _ = run_method(model, dx, dy, ds, dsch, "raw_yang",
        selector=ReplaySelector("fixed_lag8", calibration, edge, cfg), calibration=calibration, cap=cap)
    clean_err = errors(model, pilot_clean, dx)[:, cfg["attack"]["start"] + 1:cfg["attack"]["end_inclusive"] + 2, receiver].mean(axis=1)
    pilot_err = errors(model, pilot_attack, dx)[:, cfg["attack"]["start"] + 1:cfg["attack"]["end_inclusive"] + 2, receiver].mean(axis=1)
    paired_relative = (pilot_err - clean_err) / np.maximum(clean_err, 1e-12)
    sd = float(paired_relative.std(ddof=1))
    n_1pct = int(math.ceil(((stats.norm.ppf(0.975) + stats.norm.ppf(0.8)) * sd / 0.01) ** 2)) if sd > 0 else 1
    write_json(out / "sample_size_pilot.json", {"pilot_seeds": ds.tolist(), "paired_relative_excess_sd": sd,
        "approx_n_for_80pct_power_at_1pct_relative_difference": n_1pct,
        "formula": "((z_0.975+z_0.80)*sd/0.01)^2; paired seed is unit",
        "interpretation": "Pilot estimate only; final G2 screen remains exploratory and does not make a 1% confirmatory claim."})

    test_x, test_y, test_s, test_sched = data["test"]
    np.savez_compressed(out / "test_inputs.npz", x=test_x, y=test_y, seeds=test_s, schedule=test_sched)
    clean_runs = {}
    clean_errors = {}
    curve_data = {}
    clean_summary_rows = []
    for method in internal_methods + ("local",):
        result, alarm = run_method(model, test_x, test_y, test_s, test_sched, method,
            calibration=calibration, controls=controls, cap=cap,
            cache_statistics=cache_statistics, phase_statistics=phase_statistics)
        clean_runs[method] = result
        clean_errors[method] = errors(model, result, test_x)
        label = method_labels.get(method, method)
        curve_data[f"no_attack_{label}"] = clean_errors[method].mean(axis=(0, 2))
        for idx, seed in enumerate(test_s):
            values = clean_errors[method][idx, cfg["warmup"] + 1:, :]
            clean_summary_rows.append({"method": label, "seed": int(seed),
                "receiver_mse": float(values[:, receiver].mean()),
                "network_mse": float(values.mean()),
                "node_broadcasts": int(result.sends[idx].sum()),
                "edge_messages": int(result.sends[idx, :, model.edges[:, 0]].sum()),
                "payload_bytes": int(result.sends[idx, :, model.edges[:, 0]].sum() * cfg["n"] * 8)})
    write_csv(out / "no_attack_baseline_per_seed.csv", clean_summary_rows)

    metric_rows = []
    seed_rows = []
    packet_rows = []
    alarm_rows = []
    phase_rows = []
    timing_rows = []
    time_archive = {}
    attack_start, attack_end = cfg["attack"]["start"], cfg["attack"]["end_inclusive"]
    for selector_name in selector_names:
        mode, budget = SELECTOR_IMPLEMENTATIONS[selector_name]
        policy = ReplaySelector(mode, calibration, edge, cfg, budget)
        for method in internal_methods:
            method_label = method_labels[method]
            run, alarm = run_method(model, test_x, test_y, test_s, test_sched, method,
                selector=policy, calibration=calibration, controls=controls, cap=cap,
                cache_statistics=cache_statistics, phase_statistics=phase_statistics)
            packet_records = attack_packet_records(model, run, test_s, test_sched, selector_name, method_label)
            packet_rows.extend(packet_records)
            assert np.array_equal(run.sends, test_sched), "G2 requires a common exogenous schedule"
            err = errors(model, run, test_x)
            clean = clean_errors[method]
            lo, hi = attack_start + 1, attack_end + 2
            receiver_mse = err[:, lo:hi, receiver].mean(axis=1)
            network_mse = err[:, lo:hi].mean(axis=(1, 2))
            receiver_delta = receiver_mse - clean[:, lo:hi, receiver].mean(axis=1)
            network_delta = network_mse - clean[:, lo:hi].mean(axis=(1, 2))
            receiver_max = np.sqrt(err[:, lo:hi, receiver].max(axis=1))
            network_max = np.sqrt(err[:, lo:hi].max(axis=(1, 2)))
            opportunities = np.sum(test_sched[:, attack_start:attack_end + 1, sender], axis=1)
            replacements = run.injected[:, attack_start:attack_end + 1].sum(axis=1)
            changed = np.asarray([sum(r["payload_changed"] for r in packet_records if r["seed"] == int(seed)) for seed in test_s])
            recovery = []
            censored = []
            last_times = []
            for idx in range(len(test_s)):
                injected_times = np.flatnonzero(run.injected[idx] & (np.arange(cfg["T"]) >= attack_start) & (np.arange(cfg["T"]) <= attack_end))
                last = int(injected_times[-1]) if len(injected_times) else None
                last_times.append(last if last is not None else -1)
                duration, right_censored = recovery_duration(err[idx], clean[idx], last,
                    attack_end + 2, cfg["T"] + 1, receiver)
                recovery.append(duration); censored.append(right_censored)
            fpr, _ = episode_fpr(alarm, run.sends, model, edge, cfg["warmup"])
            attacked_delay = []
            attacked_alarm = []
            per_op_detected = []
            for idx in range(len(test_s)):
                first_attack = np.flatnonzero(run.injected[idx] & (np.arange(cfg["T"]) >= attack_start) & (np.arange(cfg["T"]) <= attack_end))
                if len(first_attack):
                    start = int(first_attack[0])
                    alarm_times = np.flatnonzero(alarm[idx, start:, edge])
                    detected = bool(len(alarm_times))
                    attacked_alarm.append(detected)
                    attacked_delay.append(int(alarm_times[0]) if detected else None)
                else:
                    attacked_alarm.append(False)
                    attacked_delay.append(None)
                send_ts = np.flatnonzero(test_sched[idx, attack_start:attack_end + 1, sender]) + attack_start
                per_op_detected.append(float(np.mean([alarm[idx, t, edge] for t in send_ts])) if len(send_ts) else float("nan"))
            forced_names = set(plan["attack_information"]["same_replacement_count_group"])
            for idx, seed in enumerate(test_s):
                first, last, cache_exit = cache_lifecycle(run, idx, sender, attack_start, attack_end)
                if selector_name in forced_names:
                    assert replacements[idx] == opportunities[idx], (
                        f"{selector_name} did not replace every legal opportunity for seed {seed}")
                if first is None:
                    attack_timing = {"first_replacement_time": None, "last_replacement_time": None,
                                     "cache_exit_receive_time": None, "cache_exit_state_index": None}
                    phase_bounds = [
                        ("registered_attack_window", attack_start + 1, attack_end + 2),
                        ("actual_replacement_span", 0, 0),
                        ("post_attack_stale_cache", 0, 0),
                        ("after_replayed_payload_cache_exit", 0, 0),
                    ]
                else:
                    attack_timing = {"first_replacement_time": first, "last_replacement_time": last,
                                     "cache_exit_receive_time": cache_exit,
                                     "cache_exit_state_index": cache_exit + 1 if cache_exit is not None else None}
                    phase_bounds = [
                        ("registered_attack_window", attack_start + 1, attack_end + 2),
                        ("actual_replacement_span", first + 1, last + 2),
                        ("post_attack_stale_cache", last + 2,
                         cache_exit + 1 if cache_exit is not None else cfg["T"] + 1),
                        ("after_replayed_payload_cache_exit",
                         cache_exit + 1 if cache_exit is not None else cfg["T"] + 1,
                         cfg["T"] + 1),
                    ]
                for phase, start_state, stop_state in phase_bounds:
                    phase_rows.append({"selector": selector_name, "method": method_label,
                        "seed": int(seed), "phase": phase, "state_start_inclusive": int(start_state),
                        "state_stop_exclusive": int(stop_state),
                        **error_window_metrics(err[idx], clean[idx], receiver, start_state, stop_state)})

                if first is None:
                    alarm_time = None
                    alarm_before = None
                    alarm_window = {"state_count": 0, "receiver_cumulative_excess": 0.0,
                                    "network_cumulative_excess": 0.0}
                    after_alarm_window = {"state_count": 0, "receiver_cumulative_excess": 0.0,
                                          "network_cumulative_excess": 0.0}
                else:
                    alarm_hits = np.flatnonzero(alarm[idx, first:, edge])
                    alarm_time = int(first + alarm_hits[0]) if len(alarm_hits) else None
                    alarm_before = bool(np.any(alarm[idx, :first, edge]))
                    stop_before_alarm = alarm_time + 1 if alarm_time is not None else cfg["T"] + 1
                    alarm_window = error_window_metrics(err[idx], clean[idx], receiver,
                                                        first + 1, stop_before_alarm)
                    after_alarm_window = (error_window_metrics(err[idx], clean[idx], receiver,
                                                               alarm_time + 1, cfg["T"] + 1)
                                          if alarm_time is not None else
                                          {"state_count": 0, "receiver_cumulative_excess": 0.0,
                                           "network_cumulative_excess": 0.0})
                timing_rows.append({"selector": selector_name, "method": method_label, "seed": int(seed),
                    **attack_timing, "replacements": int(replacements[idx]),
                    "opportunities": int(opportunities[idx]),
                    "first_alarm_time": alarm_time,
                    "alarm_delay_from_first_replacement": alarm_time - first if first is not None and alarm_time is not None else None,
                    "alarm_right_censored": bool(first is not None and alarm_time is None),
                    "alarm_preexisted_first_replacement": alarm_before,
                    "receiver_excess_before_alarm_mse": alarm_window.get("receiver_excess_mse"),
                    "receiver_excess_before_alarm_cumulative": alarm_window["receiver_cumulative_excess"],
                    "receiver_states_before_alarm": alarm_window["state_count"],
                    "receiver_excess_after_alarm_cumulative": after_alarm_window["receiver_cumulative_excess"],
                    "network_excess_before_alarm_cumulative": alarm_window["network_cumulative_excess"],
                    "network_excess_after_alarm_cumulative": after_alarm_window["network_cumulative_excess"]})
            key = f"{selector_name}__{method_label}"
            time_archive[key + "__receiver_error_sq"] = err[:, :, receiver].astype(np.float64)
            time_archive[key + "__network_error_sq"] = err.mean(axis=2).astype(np.float64)
            time_archive[key + "__receiver_clean_error_sq"] = clean[:, :, receiver].astype(np.float64)
            time_archive[key + "__network_clean_error_sq"] = clean.mean(axis=2).astype(np.float64)
            time_archive[key + "__target_alarm"] = alarm[:, :, edge].astype(bool)
            time_archive[key + "__target_injected"] = run.injected.astype(bool)
            time_archive[key + "__target_source_time"] = run.replay_source.astype(np.int32)
            time_archive[key + "__target_weight"] = run.weights[:, :, edge].astype(np.float32)
            row = {
                "selector": selector_name, "method": method_label, "seed_count": len(test_s),
                "mean_attack_opportunities": float(opportunities.mean()), "mean_replacements": float(replacements.mean()),
                "mean_payload_changes": float(changed.mean()),
                "replacement_rate_per_opportunity": float(replacements.sum() / max(1, opportunities.sum())),
                "receiver_attack_mse": float(receiver_mse.mean()), "receiver_paired_excess_mse": float(receiver_delta.mean()),
                "receiver_excess_per_opportunity": float(np.sum(receiver_delta * (attack_end - attack_start + 1)) / max(1, opportunities.sum())),
                "receiver_excess_per_replacement": float(np.sum(receiver_delta * (attack_end - attack_start + 1)) / max(1, replacements.sum())),
                "receiver_excess_per_payload_change": float(np.sum(receiver_delta * (attack_end - attack_start + 1)) / max(1, changed.sum())),
                "network_attack_mse": float(network_mse.mean()), "network_paired_excess_mse": float(network_delta.mean()),
                "receiver_max_error": float(receiver_max.mean()), "network_max_error": float(network_max.mean()),
                "recovery_duration_mean": float(np.mean(recovery)), "recovery_right_censored_rate": float(np.mean(censored)),
                "episode_false_isolation_audit": next(r["episode_false_isolation"] for r in audit_rows if r["method"] == method_label),
                "attack_window_alarm_fraction_per_opportunity": float(np.mean(per_op_detected)),
                "attack_alarm_after_first_replacement_rate": float(np.mean(attacked_alarm)),
                "delay_mean_detected_seeds_only": float(np.mean([v for v in attacked_delay if v is not None])) if any(v is not None for v in attacked_delay) else None,
                "delay_right_censored_rate": float(np.mean([v is None for v in attacked_delay])),
                "mean_node_packets": float(run.sends.sum(axis=(1, 2)).mean()),
                "mean_edge_messages": float(run.sends[:, :, model.edges[:, 0]].sum(axis=(1, 2)).mean()),
                "payload_bytes_per_seed": float(run.sends[:, :, model.edges[:, 0]].sum(axis=(1, 2)).mean() * cfg["n"] * 8),
            }
            if len(receiver_delta) > 1:
                row["receiver_excess_ci95_low"], row["receiver_excess_ci95_high"] = paired_ci(receiver_delta)[1:]
                row["network_excess_ci95_low"], row["network_excess_ci95_high"] = paired_ci(network_delta)[1:]
            else:
                row["receiver_excess_ci95_low"] = row["receiver_excess_ci95_high"] = None
                row["network_excess_ci95_low"] = row["network_excess_ci95_high"] = None
            metric_rows.append(row)
            alarm_rows.append({"selector": selector_name, "method": method_label,
                "episode_false_isolation_audit": row["episode_false_isolation_audit"],
                "attack_window_alarm_fraction_per_opportunity": row["attack_window_alarm_fraction_per_opportunity"],
                "attack_alarm_after_first_replacement_rate": row["attack_alarm_after_first_replacement_rate"],
                "delay_mean_detected_seeds_only": row["delay_mean_detected_seeds_only"],
                "delay_right_censored_rate": row["delay_right_censored_rate"]})
            curve_data[f"{selector_name}_{method_label}"] = err.mean(axis=(0, 2))
            for idx, seed in enumerate(test_s):
                metric_rows[-1]  # keep seed-level row group adjacent without changing aggregate schema
                # Seed-level table is the inferential unit; no packet is treated as an independent replicate.
                seed_rows.append({"selector": selector_name, "method": method_label, "seed": int(seed),
                    "receiver_attack_mse": float(receiver_mse[idx]), "receiver_paired_excess_mse": float(receiver_delta[idx]),
                    "network_attack_mse": float(network_mse[idx]), "network_paired_excess_mse": float(network_delta[idx]),
                    "opportunities": int(opportunities[idx]), "replacements": int(replacements[idx]),
                    "payload_changes": int(changed[idx]), "recovery_duration": int(recovery[idx]),
                    "recovery_right_censored": bool(censored[idx]), "last_replacement_time": int(last_times[idx])})

    write_csv(out / "per_seed_metrics.csv", seed_rows)
    write_csv(out / "selector_method_summary.csv", metric_rows)
    write_csv(out / "packet_opportunities.csv", packet_rows)
    write_csv(out / "alarm_summary.csv", alarm_rows)
    write_csv(out / "phase_metrics_per_seed.csv", phase_rows)
    write_csv(out / "detection_timing_per_seed.csv", timing_rows)
    np.savez_compressed(out / "mse_curves.npz", **curve_data)
    np.savez_compressed(out / "mse_timeline_per_seed.npz", seeds=test_s, **time_archive)
    write_json(out / "completion.json", {"completed": True, "run_id": RUN_ID,
        "elapsed_seconds": time.perf_counter() - started, "test_seed_count": len(test_s),
        "independent_unit": "seed", "closed_loop": True, "fixed_exogenous_schedule": True,
        "registered_selectors": selector_names, "registered_defenses": method_names,
        "registered_no_attack_baseline": True, "registered_local_baseline": True,
        "cache_exit_and_pre_alarm_timing_saved": True,
        "no_large_scale_parameter_search": True, "confirmatory_claim": False,
        "output_hashes": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()}})
    print(json.dumps({"run_id": RUN_ID, "test_seeds": len(test_s), "methods": len(method_names),
                      "selectors": len(selector_names), "summary": str(out / "selector_method_summary.csv")}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(ROOT / "simulation/g2_runs" / RUN_ID))
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    if args.preflight_only:
        frozen = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
        selectors, methods, split_specs = frozen_plan_parts(frozen)
        model = build_model(frozen)
        schedule = repeated_schedule(model.cfg, 1, frozen["communication"]["schedules"]["irregular"],
                                     frozen["communication"]["node_phase_step"])
        expected = np.asarray(frozen["model"]["A"], float)
        assert np.array_equal(model.A, expected)
        assert model.cfg["T"] == frozen["model"]["horizon"]
        assert model.cfg["attack"]["start"] == frozen["model"]["attack_interval_inclusive"][0]
        assert model.cfg["attack"]["end_inclusive"] == frozen["model"]["attack_interval_inclusive"][1]
        assert schedule.shape == (1, model.cfg["T"], model.cfg["N"])
        print(json.dumps({"status": "PREFLIGHT_PASS", "plan_run_id": frozen["run_id"],
                          "selectors": selectors, "defenses": methods,
                          "seed_splits": sorted(split_specs), "model_shape": [model.cfg["N"], model.cfg["n"]],
                          "horizon": model.cfg["T"], "schedule_shape": list(schedule.shape)}, indent=2))
    else:
        try:
            main(args.out)
        except Exception as exc:
            failure_dir = Path(args.out)
            if failure_dir.is_dir() and not (failure_dir / "completion.json").exists():
                write_json(failure_dir / "failure.json", {
                    "run_id": RUN_ID, "status": "FAILED_PARTIAL_RUN",
                    "error": repr(exc), "traceback": traceback.format_exc(),
                    "frozen_plan_sha256": hashlib.sha256(PLAN_PATH.read_bytes()).hexdigest(),
                    "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    "simulation_results_are_not_final": True})
            raise
