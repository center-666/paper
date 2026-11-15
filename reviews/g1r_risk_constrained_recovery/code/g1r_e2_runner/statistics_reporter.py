from __future__ import annotations

import csv
import json
import statistics
import sys
import tempfile
import time
import tracemalloc
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

from .config_loader import BASE, FrozenConfig, read_json
from .online_proposal import build_online_input, propose, record_dict
from .result_writer import canonical_json_bytes, write_exclusive
from .integrity_checker import validate_full_run
from .checkpoint_manager import CheckpointManager


def _bool(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1"}


def summarize_rows(config: FrozenConfig, rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute E2 statistics only after all frozen seeds are present."""
    code_path = str(config.base / "code")
    if code_path not in sys.path:
        sys.path.insert(0, code_path)
    import e2_statistics

    methods = {}
    strata = {method: {} for method in config.methods}
    for method in config.methods:
        normal = [dict(row, main_case=_bool(row["main_case"])) for row in rows
                  if row["scenario"] == "normal" and row["method"] == method
                  and _bool(row["main_case"])]
        attack = [dict(row, main_case=_bool(row["main_case"])) for row in rows
                  if row["scenario"] == "replay" and row["method"] == method
                  and _bool(row["main_case"])]
        for row in normal + attack:
            row["set_action_norm"] = float(row["set_action_norm"])
            if row["scenario"] == "replay":
                row["coverage_confirmed"] = _bool(row["coverage_confirmed"])
        gate = e2_statistics.evaluate_e2_counts(attack, normal)
        methods[method] = asdict(gate)
        methods[method]["main_case_rows"] = {
            "attack": len(attack), "normal": len(normal),
            "statistical_unit": "independent seed; event-age cases remain clustered",
        }
        methods[method]["diagnostics"] = {
            "attack_main_solver_rejects": sum(row["proposal_status"] == "SOLVER_REJECT" for row in attack),
            "attack_main_gate_rejects": sum(row["gate_status"] == "GATE_REJECT" for row in attack),
            "attack_main_denominator": len(attack),
            "attack_main_solver_reject_rate": (sum(row["proposal_status"] == "SOLVER_REJECT" for row in attack)
                                                / len(attack) if attack else None),
            "attack_main_gate_reject_rate": (sum(row["gate_status"] == "GATE_REJECT" for row in attack)
                                              / len(attack) if attack else None),
            "normal_solver_rejects_all_rows": sum(row["proposal_status"] == "SOLVER_REJECT"
                for row in rows if row["scenario"] == "normal" and row["method"] == method),
            "normal_gate_rejects_all_rows": sum(row["gate_status"] == "GATE_REJECT"
                for row in rows if row["scenario"] == "normal" and row["method"] == method),
            "normal_denominator": sum(row["scenario"] == "normal" and row["method"] == method
                                      for row in rows),
            "attack_solver_rejects_all_event_age_rows": sum(row["proposal_status"] == "SOLVER_REJECT"
                for row in rows if row["scenario"] == "replay" and row["method"] == method),
            "attack_gate_rejects_all_event_age_rows": sum(row["gate_status"] == "GATE_REJECT"
                for row in rows if row["scenario"] == "replay" and row["method"] == method),
            "attack_event_age_denominator": sum(row["scenario"] == "replay" and row["method"] == method
                                                for row in rows),
        }
        for event in config.events:
            for age in config.ages:
                rows_h = [row for row in rows if row["scenario"] == "replay"
                          and row["method"] == method and _event(row) == event
                          and _age(row) == age]
                n = len({int(row["seed"]) for row in rows_h})
                coverage = sum(_bool(row["coverage_confirmed"]) for row in rows_h)
                nonzero = sum(float(row["set_action_norm"]) > 1e-12 for row in rows_h)
                strata[method][f"{event[0]}:{event[1]}@{age}"] = {
                    "n_independent_seeds": n,
                    "coverage_count": coverage,
                    "coverage_rate": None if n == 0 else coverage / n,
                    "coverage_cp_one_sided_95_lower": (None if n == 0 else
                        e2_statistics.cp_lower(coverage, n)),
                    "nonzero_action_count": nonzero,
                    "nonzero_action_rate": None if n == 0 else nonzero / n,
                    "solver_reject_count": sum(row["proposal_status"] == "SOLVER_REJECT" for row in rows_h),
                    "gate_reject_count": sum(row["gate_status"] == "GATE_REJECT" for row in rows_h),
                    "solver_reject_rate": (sum(row["proposal_status"] == "SOLVER_REJECT" for row in rows_h)
                                           / n if n else None),
                    "gate_reject_rate": (sum(row["gate_status"] == "GATE_REJECT" for row in rows_h)
                                         / n if n else None),
                    "cluster_note": "each seed contributes one row per event-age; strata are paired, not independent across cells",
                }
    return {
        "result_type": "FORMAL_E2_STATISTICS_ONLY_AFTER_ALL_BATCHES",
        "methods": methods,
        "event_age_strata": strata,
        "formal_experiment_executed": False,
    }


def _event(row):
    value = row.get("event")
    if value in (None, "", "null"):
        return None
    if isinstance(value, str):
        value = json.loads(value)
    return tuple(map(int, value))


def _age(row):
    value = row.get("age")
    return None if value in (None, "", "null") else int(value)


def independent_recompute(config: FrozenConfig, normal_batch_files: tuple[Path, ...],
                          attack_batch_files: tuple[Path, ...]) -> dict[str, Any]:
    if len(normal_batch_files) != 10 or len(attack_batch_files) != 10:
        raise ValueError("E2 statistical audit requires all twenty frozen batches")
    rows = []
    for path in normal_batch_files + attack_batch_files:
        with path.open("r", encoding="utf-8", newline="") as stream:
            rows.extend(csv.DictReader(stream))
    normal_rows = [row for row in rows if row["scenario"] == "normal"]
    attack_rows = [row for row in rows if row["scenario"] == "replay"]
    validate_full_run(config, normal_rows, attack_rows)
    return summarize_rows(config, rows)


def benchmark_cached(config: FrozenConfig, public_model, cache_path: Path) -> dict[str, Any]:
    """Measure proposal-only work using cached Task 5 Debug z vectors."""
    expected = {f"{scenario}_{seed}"
                for scenario in ("clean", "replay_packet")
                for seed in range(141400000, 141400005)}
    with np.load(cache_path, allow_pickle=False) as archive:
        if set(archive.files) != expected:
            raise ValueError("Debug cache keys differ from the frozen five-seed cache")
        vectors = [np.asarray(archive[key], dtype=np.float64).copy() for key in sorted(expected)]
    if any(z.shape != (12,) or not np.all(np.isfinite(z)) for z in vectors):
        raise ValueError("Debug cache contains an invalid innovation")

    def invoke(z):
        records = []
        for method in config.methods:
            online = build_online_input(z, public_model, config.thresholds[method], method)
            records.append(propose(online))
        return records

    invoke(vectors[0])  # deterministic warm-up only
    one_start = time.perf_counter()
    one_records = invoke(vectors[0])
    one_seconds = time.perf_counter() - one_start
    batch_inputs = [vectors[index % len(vectors)] for index in range(20)]
    batch_start = time.perf_counter()
    batch_records = [record for z in batch_inputs for record in invoke(z)]
    batch_seconds = time.perf_counter() - batch_start
    tracemalloc.start()
    _ = [record for z in batch_inputs for record in invoke(z)]
    _, peak_memory = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    serialized_sizes = [len(canonical_json_bytes(record_dict(record))) for record in batch_records]
    with tempfile.TemporaryDirectory(prefix="g1r-e2-checkpoint-bench-") as directory:
        checkpoint_root = Path(directory)
        checkpoint_path = checkpoint_root / "checkpoint.json"
        checkpoint = CheckpointManager(checkpoint_path, "checkpoint-fixture", "dry_run")
        completed_paths = []
        for fixture_seed in range(900000, 900020):
            online_path = checkpoint_root / f"fixture_{fixture_seed}_online.jsonl"
            offline_path = checkpoint_root / f"fixture_{fixture_seed}_offline.csv"
            fixture_records = invoke(batch_inputs[fixture_seed % len(batch_inputs)])
            online_bytes = b"".join(canonical_json_bytes(record_dict(record))
                                     for record in fixture_records)
            offline_bytes = f"fixture_seed,completed\\n{fixture_seed},true\\n".encode()
            online_sha = write_exclusive(online_path, online_bytes)
            offline_sha = write_exclusive(offline_path, offline_bytes)
            checkpoint.mark_seed_complete("normal_fixture", fixture_seed,
                                          online_path, online_sha,
                                          offline_path, offline_sha)
            completed_paths.append((fixture_seed, online_path, offline_path))
        recovery_start = time.perf_counter()
        recovered = CheckpointManager(checkpoint_path, "checkpoint-fixture", "dry_run")
        verified = sum(recovered.seed_is_complete("normal_fixture", seed,
                                                   online, offline)
                       for seed, online, offline in completed_paths)
        checkpoint_recovery_seconds = time.perf_counter() - recovery_start
        if verified != 20:
            raise RuntimeError("checkpoint benchmark did not recover all 20 synthetic shards")
    per_proposal = batch_seconds / len(batch_records)
    total_proposals = 200 * len(config.methods) + 200 * len(config.events) * len(config.ages) * len(config.methods)
    debug_summary_path = config.base / "results/g1r_task5_debug_20261115_r04/summary.json"
    debug_summary = read_json(debug_summary_path)
    historical_total = float(debug_summary["elapsed_seconds"])
    # The Task 5 Debug wall time covers 5 fixed seeds, 10 Yang simulation calls,
    # and 30 proposal calls. Its ten simulator calls each contain five seeds;
    # use 55 seed-equivalent units (five data generations plus fifty passes).
    # tracemalloc is deliberately excluded from all timing intervals.
    debug_proposal_component = per_proposal * int(debug_summary["proposal_rows"])
    residual = max(0.0, historical_total - debug_proposal_component)
    baseline_units = 5 + 10 * 5
    per_data_or_sim_unit = residual / baseline_units
    e2_data_sim_units = 400 + 200 + 200 + 200 * len(config.events) * len(config.ages)
    estimated_sim_data = per_data_or_sim_unit * e2_data_sim_units
    estimated_proposal = per_proposal * total_proposals
    estimated_total = estimated_sim_data + estimated_proposal
    normal_batch_estimate = (20 * len(config.methods) * per_proposal
                             + 40 * per_data_or_sim_unit)
    attack_batch_estimate = (20 * len(config.events) * len(config.ages)
                             * len(config.methods) * per_proposal
                             + 520 * per_data_or_sim_unit)
    return {
        "scope": "cached Debug feature vectors only; no data generation or formal Seed use",
        "twenty_input_benchmark_note": "20 input rows are formed by repeating the ten saved Debug vectors; CPU timing covers proposal calls only, not scenario simulation",
        "cached_vectors": len(vectors),
        "single_seed_equivalent_seconds": one_seconds,
        "single_seed_equivalent_proposals": len(one_records),
        "twenty_seed_equivalent_seconds": batch_seconds,
        "twenty_seed_equivalent_feature_rows": len(batch_inputs),
        "twenty_seed_equivalent_unique_cached_vectors": len(vectors),
        "twenty_seed_equivalent_proposal_calls": len(batch_records),
        "twenty_normal_seed_batch_seconds_estimate": normal_batch_estimate,
        "twenty_attack_seed_batch_seconds_estimate": attack_batch_estimate,
        "twenty_seed_equivalent_peak_python_bytes": int(peak_memory),
        "checkpoint_recovery_20_fixture_shards_seconds": checkpoint_recovery_seconds,
        "checkpoint_recovery_verified_shards": verified,
        "checkpoint_benchmark_seed_scope": "synthetic identifiers 900000-900019; no trajectories or study Seeds",
        "serialized_proposal_record_bytes_mean": float(statistics.mean(serialized_sizes)),
        "serialized_proposal_record_bytes_max": int(max(serialized_sizes)),
        "e2_proposal_calls_planned": total_proposals,
        "e2_proposal_seconds_estimate": estimated_proposal,
        "e2_simulation_and_data_generation_unit_estimate_seconds": estimated_sim_data,
        "historical_debug_run_seconds": historical_total,
        "historical_debug_seed_count": debug_summary["seed_count"],
        "estimated_total_e2_seconds_coarse": estimated_total,
        "estimated_total_e2_hours_coarse": estimated_total / 3600.0,
        "estimated_total_e2_hours_range_0_5x_to_2x": [estimated_total * 0.5 / 3600.0,
                                                        estimated_total * 2.0 / 3600.0],
        "proposal_time_per_call_seconds": per_proposal,
        "historical_debug_proposal_component_seconds": debug_proposal_component,
        "historical_debug_residual_data_sim_seconds": residual,
        "simulation_estimate_note": "proposal time measured on cached z without tracemalloc; data/simulation component is a coarse residual from the archived Task 5 Debug duration and its recorded 5 generated seeds, 10 Yang passes, and 30 proposals. Range is planning-only and not a run guarantee.",
        "formal_execution": False,
    }
