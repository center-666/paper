"""One predeclared rank-one sensing pressure probe for the cache-residency candidate."""
from __future__ import annotations
import argparse, copy, csv, hashlib, json, shutil, sys, time
from pathlib import Path
import numpy as np
from scipy import stats
from model import Model, generate_data
from engine import simulate, basic_metrics
from cache_screen import get_schedule
from sequential_cache import PhaseStatistics, SequentialController, PHASES, phase_rates
from run_study import write_json, write_csv, paired_interval
from validation_summary import holm, paired_p


def seed_array(spec):
    return np.arange(spec["start"], spec["start"] + spec["count"])


def make_config(base, plan, schedule_name):
    cfg = copy.deepcopy(base)
    cfg.update(A=plan["A"], H_matrices=plan["H_matrices"], R_matrices=plan["R_matrices"])
    cfg["cache_schedule_pattern"] = plan["schedules"][schedule_name]
    cfg["cache_schedule_phase"] = plan["phase_step"]
    for split, spec in plan["splits"].items():
        cfg[split + "_seeds"] = spec
    cfg["attack"].update(matched_replay_time_lag=80, low_bias_factor=0.25)
    return cfg


def method_args(method):
    if method == "mean":
        return "mean", False
    if method == "carry_energy_cusum":
        return "white_cusum", True
    if method == "carry_signed_cusum":
        return "white_signed_cusum", True
    raise ValueError(method)


def fit_schedule(cfg, plan, folder):
    model = Model.build(cfg)
    data = {}
    for split in ("train", "calibration", "design", "tune", "normal_audit"):
        seeds = seed_array(cfg[split + "_seeds"])
        x, y = generate_data(model, seeds)
        data[split] = (x, y, seeds, get_schedule(model, len(seeds)))

    x, y, seeds, schedule = data["train"]
    # The reference run must retain cap_norms; the later calibration/test runs do not.
    reference = simulate(model, x, y, seeds, "yang", schedule=schedule, collect=True)
    cap = float(np.quantile(reference.cap_norms.ravel(), cfg["cap_quantile"]))

    choices = []
    x, y, seeds, schedule = data["design"]
    for half_life in plan["half_lives"]:
        monitor = SequentialController(model, half_life=half_life)
        run = simulate(model, x, y, seeds, "capped", schedule=schedule, cap=cap,
                       cache_monitor=monitor, collect=False)
        sq = np.sum((run.estimates - x[:, :, None, :]) ** 2, axis=-1)
        choices.append({"half_life": half_life,
                        "normal_design_mse": float(sq[:, cfg["warmup"] + 1:].mean())})
    half_life = min(choices, key=lambda row: row["normal_design_mse"])["half_life"]

    episodes = {}
    for split in ("train", "calibration"):
        x, y, seeds, schedule = data[split]
        collector = SequentialController(model, half_life=half_life, record_residuals=True)
        simulate(model, x, y, seeds, "capped", schedule=schedule, cap=cap,
                 cache_monitor=collector, collect=False)
        episodes[split] = collector.finish()
    statistics = PhaseStatistics.fit(
        episodes["train"], episodes["calibration"], len(model.edges), cfg["n"],
        cfg["max_interval"], cfg["warmup"], plan["window_length"],
        plan["signed_cusum_reference"], cfg["covariance_ridge_relative"])
    statistics.save(folder / "phase_statistics.npz")

    controls = {}
    tuning = []
    audit = []
    for method in ("mean", "carry_energy_cusum", "carry_signed_cusum"):
        detector, carry = method_args(method)
        lo = np.full(3, 0.05)
        hi = np.full(3, 40.0)
        for iteration in range(plan["threshold_tuning_rounds"]):
            multipliers = np.sqrt(lo * hi)
            x, y, seeds, schedule = data["tune"]
            monitor = SequentialController(model, statistics, detector, multipliers,
                                            half_life, carry_across_packets=carry)
            simulate(model, x, y, seeds, "capped", schedule=schedule, cap=cap,
                     cache_monitor=monitor, collect=False)
            rates = phase_rates(monitor.finish(), cfg["warmup"])
            tuning.append({"method": method, "round": iteration,
                           "multipliers": multipliers.tolist(), "rates": rates})
            realized = np.asarray([rates[phase]["false_isolation_rate"] for phase in PHASES])
            too_high = realized > plan["normal_target"]
            lo = np.where(too_high, multipliers, lo)
            hi = np.where(too_high, hi, multipliers)
        controls[method] = np.sqrt(lo * hi)

        x, y, seeds, schedule = data["normal_audit"]
        monitor = SequentialController(model, statistics, detector, controls[method],
                                        half_life, carry_across_packets=carry)
        simulate(model, x, y, seeds, "capped", schedule=schedule, cap=cap,
                 cache_monitor=monitor, collect=False)
        rates = phase_rates(monitor.finish(), cfg["warmup"])
        for phase in PHASES:
            audit.append({"method": method, "phase": phase,
                          "count": rates[phase]["count"],
                          "false_isolation_rate": rates[phase]["false_isolation_rate"]})

    write_json(folder / "frozen_controls.json", {
        "cap": cap, "half_life": half_life,
        "half_life_candidates": choices,
        "multipliers": {key: value.tolist() for key, value in controls.items()},
        "normal_target": plan["normal_target"]})
    write_json(folder / "tuning_history.json", tuning)
    write_csv(folder / "normal_audit_rates.csv", audit)
    return model, statistics, controls, cap, half_life


def run_case(model, statistics, controls, cap, half_life, method, scenario, x, y, seeds, schedule):
    if method == "local":
        run = simulate(model, x, y, seeds, "local", scenario, schedule, collect=False)
    elif method == "age_only":
        monitor = SequentialController(model, half_life=half_life)
        run = simulate(model, x, y, seeds, "capped", scenario, schedule, cap=cap,
                       cache_monitor=monitor, collect=False)
    else:
        detector, carry = method_args(method)
        monitor = SequentialController(model, statistics, detector, controls[method],
                                       half_life, carry_across_packets=carry)
        run = simulate(model, x, y, seeds, "capped", scenario, schedule, cap=cap,
                       cache_monitor=monitor, collect=False)
    metrics, error = basic_metrics(model, run, x)
    a = model.cfg["attack"]
    start, end = a["start"] + 1, a["end_inclusive"] + 2
    receiver = a["receiver"]
    metrics["receiver_attack_mse"] = error[:, start:end, receiver].mean(axis=1)
    metrics["receiver_clean_window_mse"] = error[:, cfg_warmup(model) + 1:, receiver].mean(axis=1)
    return run, metrics, error


def cfg_warmup(model):
    return model.cfg["warmup"]


def audit_run(model, run, x, schedule, scenario, method):
    assert np.isfinite(run.estimates).all()
    assert np.all((run.weights >= 0) & (run.weights <= 1))
    if method != "local":
        assert np.array_equal(run.sends, schedule)
    if scenario == "clean":
        assert not run.injected.any()
    a = model.cfg["attack"]
    for trial, t in zip(*np.where(run.injected)):
        assert a["start"] <= t <= a["end_inclusive"]
        assert run.sends[trial, t, a["sender"]]


def primary_comparisons(rows, plan):
    index = {(r["schedule"], r["edge_label"], r["method"], r["scenario"], int(r["seed"])): r for r in rows}
    tests = []
    all_rows = []
    for schedule in plan["schedules"]:
        for edge in plan["attack_edges"]:
            for scenario in ("step", "half_step"):
                for baseline in ("carry_energy_cusum", "carry_signed_cusum"):
                    seeds = sorted({int(r["seed"]) for r in rows
                                    if r["schedule"] == schedule and r["edge_label"] == edge})
                    candidate = np.asarray([float(index[schedule, edge, "mean", scenario, seed]["receiver_attack_mse"]) for seed in seeds])
                    base = np.asarray([float(index[schedule, edge, baseline, scenario, seed]["receiver_attack_mse"]) for seed in seeds])
                    candidate_clean = np.asarray([float(index[schedule, edge, "mean", "clean", seed]["receiver_attack_mse"]) for seed in seeds])
                    base_clean = np.asarray([float(index[schedule, edge, baseline, "clean", seed]["receiver_attack_mse"]) for seed in seeds])
                    diff = candidate - base
                    excess = (candidate - candidate_clean) - (base - base_clean)
                    practical_margin = candidate - 0.99 * base
                    p = paired_p(practical_margin)
                    _, lo, hi = paired_interval(diff)
                    _, elo, ehi = paired_interval(excess)
                    row = {
                        "schedule": schedule, "edge_label": edge, "scenario": scenario,
                        "candidate": "mean", "baseline": baseline, "seed_count": len(seeds),
                        "receiver_relative_gain": float(-diff.mean() / base.mean()),
                        "receiver_diff_mean": float(diff.mean()),
                        "receiver_diff_bootstrap95_low": float(lo),
                        "receiver_diff_bootstrap95_high": float(hi),
                        "attack_excess_diff_mean": float(excess.mean()),
                        "attack_excess_bootstrap95_low": float(elo),
                        "attack_excess_bootstrap95_high": float(ehi),
                        "practical_p": float(p),
                        "normal_network_relative_cost": float(np.mean([
                            float(index[schedule, edge, "mean", "clean", seed]["mse_all"]) /
                            float(index[schedule, edge, baseline, "clean", seed]["mse_all"]) - 1
                            for seed in seeds])),
                        "normal_receiver_relative_cost": float(np.mean([
                            float(index[schedule, edge, "mean", "clean", seed]["receiver_clean_window_mse"]) /
                            float(index[schedule, edge, baseline, "clean", seed]["receiver_clean_window_mse"]) - 1
                            for seed in seeds]))
                    }
                    all_rows.append(row)
                    if edge == "primary" and scenario == "step":
                        tests.append(row)
    adjusted = holm([r["practical_p"] for r in tests])
    for row, p in zip(tests, adjusted):
        row["holm_p"] = float(p)
        row["passes_local_probe"] = bool(row["receiver_relative_gain"] >= 0.01 and p < 0.05)
    return all_rows, tests


def main(plan_path, out_path):
    out = Path(out_path)
    if out.exists():
        raise FileExistsError("Preserve previous evidence; choose a new output directory")
    out.mkdir(parents=True)
    plan = json.loads(Path(plan_path).read_text(encoding="utf-8-sig"))
    base = json.loads(Path(plan["base_config"]).read_text(encoding="utf-8-sig"))
    write_json(out / "plan.json", plan)
    sources = out / "sources"
    sources.mkdir()
    for file in Path("simulation").glob("*.py"):
        shutil.copy2(file, sources / file.name)
    shutil.copy2(plan_path, sources / Path(plan_path).name)
    from datetime import datetime, timezone
    write_json(out / "registration.json", {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "plan_sha256": hashlib.sha256(Path(plan_path).read_bytes()).hexdigest(),
        "source_sha256": {file.name: hashlib.sha256(file.read_bytes()).hexdigest() for file in sources.iterdir()},
        "python": sys.version, "numpy": np.__version__, "test_data_generated_at_registration": False,
        "prior_results_seen": True, "no_test_retuning": True})

    rows = []
    normal_records = []
    started = time.perf_counter()
    for schedule_name in plan["schedules"]:
        folder = out / schedule_name
        folder.mkdir()
        cfg = make_config(base, plan, schedule_name)
        write_json(folder / "config.json", cfg)
        model, statistics, controls, cap, half_life = fit_schedule(cfg, plan, folder)
        seeds = seed_array(cfg["test_seeds"])
        x, y = generate_data(model, seeds)
        schedule = get_schedule(model, len(seeds))
        np.savez_compressed(folder / "test_inputs.npz", x=x, y=y, seeds=seeds, schedule=schedule)
        for edge_label, edge_pair in plan["attack_edges"].items():
            model.cfg["attack"].update(sender=edge_pair[0], receiver=edge_pair[1])
            edge_dir = folder / edge_label
            edge_dir.mkdir()
            write_json(edge_dir / "attack.json", model.cfg["attack"])
            for method in plan["methods"]:
                for scenario in plan["scenarios"]:
                    run, metrics, error = run_case(model, statistics, controls, cap, half_life,
                                                    method, scenario, x, y, seeds, schedule)
                    audit_run(model, run, x, schedule, scenario, method)
                    for s, seed in enumerate(seeds):
                        rows.append({
                            "schedule": schedule_name, "edge_label": edge_label,
                            "method": method, "scenario": scenario, "seed": int(seed),
                            "mse_all": float(metrics["mse_all"][s]),
                            "mse_attack_window": float(metrics["mse_attack_window"][s]),
                            "receiver_attack_mse": float(metrics["receiver_attack_mse"][s]),
                            "receiver_clean_window_mse": float(metrics["receiver_clean_window_mse"][s]),
                            "edge_messages": float(metrics["edge_messages"][s]),
                            "mean_received_weight": float(metrics["mean_received_weight"][s])
                        })
                    np.savez_compressed(edge_dir / (method + "__" + scenario + ".npz"),
                                        estimates=run.estimates, weights=run.weights,
                                        sends=run.sends, injected=run.injected,
                                        cache_bad=run.cache_bad)
        write_csv(out / "per_seed_metrics.csv", rows)
        print(json.dumps({"schedule": schedule_name, "rows": len(rows)}), flush=True)

    comparisons, tests = primary_comparisons(rows, plan)
    write_csv(out / "comparisons.csv", comparisons)
    write_csv(out / "primary_tests.csv", tests)
    write_json(out / "execution.json", {
        "completed": True, "elapsed_seconds": time.perf_counter() - started,
        "method_trajectories": len(rows), "test_seeds": len(seeds),
        "new_simulations": True, "scope": "single rank-one sensing pressure probe"})
    write_json(out / "gate.json", {
        "scope": "Descriptive pressure probe; does not replace the failed main gate",
        "primary_tests": len(tests),
        "primary_local_probe_passes": sum(bool(row.get("passes_local_probe", False)) for row in tests)})
    print("COMPLETED " + str(out.resolve()), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", default="simulation/partial_observability_probe_plan.json")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    main(args.plan, args.out)
