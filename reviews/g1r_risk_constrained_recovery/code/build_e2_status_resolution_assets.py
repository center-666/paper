"""Assemble provenance/schema/template assets; never launches or samples E2."""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import platform
import subprocess

import numpy as np
import scipy

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "reviews/g1r_risk_constrained_recovery"
SOURCE_RUN = BASE / "results/g1r_e2_status_resolution_20261115_r05"
RUN = BASE / "results/g1r_e2_status_resolution_20261115_r09"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+"\n",
                    encoding="utf-8", newline="\n")


def main():
    if RUN.exists():
        raise FileExistsError(f"Preserve previous status package: {RUN}")
    RUN.mkdir(parents=True)
    for name in ["cached_debug_features.npz", "proposal_equivalence.csv",
                 "equivalence_manifest.json", "adapter_tests.json"]:
        (RUN/name).write_bytes((SOURCE_RUN/name).read_bytes())
    eq_path = RUN / "proposal_equivalence.csv"
    rows = list(csv.DictReader(eq_path.open(encoding="utf-8-sig")))
    stats = {}
    for method in sorted({row["method"] for row in rows}):
        subset = [row for row in rows if row["method"] == method]
        stats[method] = {
            "records": len(subset),
            "raw_status_counts": {},
            "proposal_status_counts": {},
            "gate_status_counts": {},
            "execution_success_count": sum(float(row["action_norm_after_gate"]) > 1e-12
                                            for row in subset),
            "zero_or_unresolved_count": sum(
                row["certificate_zero_or_unresolved"].lower() == "true" for row in subset),
        }
        for field, key in [("raw_status", "raw_status_counts"),
                           ("proposal_status", "proposal_status_counts"),
                           ("gate_status", "gate_status_counts")]:
            for value in [row[field] for row in subset]:
                stats[method][key][value] = stats[method][key].get(value, 0)+1
    dump(RUN/"status_mapping_statistics.json", {
        "source": "proposal_equivalence.csv",
        "note": "Debug counts are diagnostics only, not rates or E2 evidence.",
        "counts": stats,
    })
    # Copy exactly the reviewed schema/addendum into the result package.
    for name in ["e2_log_schema.json", "model_builder_inputs_addendum.json"]:
        target = RUN/name
        if target.exists():
            raise FileExistsError(target)
        target.write_bytes((BASE/name).read_bytes())
    protocol = json.loads((BASE/"protocol_v2.json").read_text(encoding="utf-8"))
    calibration = json.loads((BASE/"results/g1r_task5_calibration_20261115_r01/calibration_manifest.json").read_text(encoding="utf-8"))
    threshold_file = BASE/"results/g1r_task5_calibration_20261115_r01/frozen_thresholds.json"
    input_addendum = json.loads((BASE/"model_builder_inputs_addendum.json").read_text(encoding="utf-8"))
    blas = io.StringIO()
    with __import__("contextlib").redirect_stdout(blas):
        np.show_config()
    runtime = {"python": platform.python_version(), "numpy": np.__version__,
               "scipy": scipy.__version__, "blas_configuration": blas.getvalue()}
    runtime_matches = {"python": runtime["python"] == calibration["python"],
                       "numpy": runtime["numpy"] == calibration["numpy"],
                       "scipy": runtime["scipy"] == calibration["scipy"],
                       "blas_exact": runtime["blas_configuration"] == calibration["blas_configuration"]}
    for source, expected in calibration["source_sha256"].items():
        runtime_matches[source] = sha(ROOT/source) == expected
    for row in input_addendum["inputs"]:
        runtime_matches[row["path"]] = sha(ROOT/row["path"]) == row["current_sha256"] == row["task5_start_snapshot_sha256"]
    current_sources = [
        BASE/"code/e2_status_adapter.py",
        BASE/"code/verify_e2_adapter_equivalence.py",
        BASE/"code/test_e2_status_adapter.py",
        BASE/"code/e2_statistics.py",
        BASE/"code/test_e2_statistics.py",
        BASE/"code/test_e2_deterministic_validation.py",
        BASE/"code/test_v2_data_mechanics.py",
        BASE/"code/v2_estimators.py",
        BASE/"code/calibrate_v2_normal.py",
        BASE/"protocol_v2.json", threshold_file,
        BASE/"results/g1r_task5_calibration_20261115_r01/calibration_manifest.json",
        BASE/"results/g1r_task5_calibration_20261115_r01/calibration_scores.csv",
        ROOT/"simulation/model.py", ROOT/"simulation/engine.py",
        ROOT/"simulation/config.json", ROOT/"simulation/reference_exploration_plan.json",
        BASE/"results/g1r_replay_joint_20261114_r01/replay_joint_matrices.npz",
        BASE/"model_builder_inputs_addendum.json",
        RUN/"equivalence_manifest.json",
    ]
    env = {
        "status": "PREPARED_FOR_OWNER_REVIEW_E2_NOT_EXECUTED",
        "worktree_path": str(ROOT),
        "worktree_branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip(),
        "worktree_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "required_baseline_commit": "490e5b8f1212004407a0cdbfde224bf90a691da4",
        "checkout_created_clean_at_frozen_baseline": True,
        "is_worktree_clean_at_asset_generation": not bool(subprocess.check_output(["git", "status", "--short"], cwd=ROOT, text=True).strip()),
        "design": {
            "v2_protocol_sha256": sha(BASE/"protocol_v2.json"),
            "task5_calibration_threshold_sha256": sha(threshold_file),
            "task5_calibration_source_manifest_sha256": sha(BASE/"results/g1r_task5_calibration_20261115_r01/calibration_manifest.json"),
            "task5_calibration_manifest_originally_omitted_inputs": input_addendum,
        },
        "runtime": runtime,
        "runtime_and_task5_assets_match_calibration": runtime_matches,
        "all_calibration_assets_and_runtime_match": all(runtime_matches.values()),
        "source_sha256": {p.relative_to(ROOT).as_posix(): sha(p) for p in current_sources},
        "e2_seeds": {
            "normal": {"start": 141420000, "count": 200},
            "attack": {"start": 141430000, "count": 200},
            "seed_scan": "reviews/g1r_risk_constrained_recovery/results/g1r_pre_e2_readonly_audit_20261115_r04/e2_seed_scan.json"},
        "shared_engine_model_unchanged": True,
        "note": "This environment record freezes the adapter audit/runtime. E2 requires a separate authorized run and its manifest must record the resulting commit SHA.",
    }
    dump(RUN/"environment_freeze.json", env)
    template = {
        "run_id": "g1r_e2_run_<authorized-date>_r01",
        "state": "TEMPLATE_NOT_EXECUTED",
        "execution_authorized": False,
        "base_commit": env["worktree_head"],
        "baseline_commit_required": env["required_baseline_commit"],
        "implementation_commit_after_task_completion": "fill with audited Task B.1 commit before an authorized E2 run",
        "environment_freeze_ref": "environment_freeze.json",
        "adapter_source_sha256": sha(BASE/"code/e2_status_adapter.py"),
        "adapter_equivalence_run": "g1r_e2_status_resolution_20261115_r05",
        "model_builder_input_addendum": "model_builder_inputs_addendum.json",
        "protocol_v2_sha256": env["design"]["v2_protocol_sha256"],
        "calibration_thresholds_sha256": env["design"]["task5_calibration_threshold_sha256"],
        "thresholds": json.loads(threshold_file.read_text(encoding="utf-8"))["thresholds"],
        "normal_calibration_run": "g1r_task5_calibration_20261115_r01",
        "run_type": "E2 only; E3 is a separate authorization",
        "model_and_attack": {
            "model_config": protocol["model_config"],
            "fixed_schedule": "t=0 all nodes; thereafter sender j transmits iff t mod 8=j",
            "receiver": 1, "decision_time": 216, "target_state": 217,
            "innovation_times": [211, 212, 213, 214, 215, 216],
            "attack": "single historical packet replay on edge 0->1 at r=200",
            "candidate_events": protocol["events_edge_r"],
            "nominal_age": 64, "pressure_ages": [32, 96],
        "replay_source_rule": "For each event (edge,r) and age a, set replay_packet_lag=a//8 in the simulator; offline-verify source_send_time==r-a and that packet was actually sent. Do not disclose the selected event or age to the proposal.",
            "online_age_disclosure": "none; estimator always uses the frozen nominal model",
        },
        "case_counts": {"normal_main_seed_rows_per_method": 200,
                        "attack_seed_count": 200,
                        "attack_event_age_cases_per_seed": 24,
                        "attack_proposal_rows_all_methods": 14400,
                        "normal_proposal_rows_all_methods": 600,
                        "primary_main_case_rows_per_method": 200},
        "methods": list(protocol["methods"]),
        "common_constraints": {"U": protocol["U_common"], "alpha": protocol["alpha"],
                               "normal_R_over_J0": protocol["primary_R_over_J0"],
                               "beta": protocol["beta"],
                               "new_communication_bytes": 0},
        "seeds": {"normal": {"start": 141420000, "count": 200},
                  "attack": {"start": 141430000, "count": 200},
                  "paired_statistical_unit": "independent Seed; within-seed events and ages remain clustered"},
        "gate": {"coverage_count_min": 190, "coverage_cp_one_sided_95_lower_min": .90,
                 "set_attack_nonzero_count_min": 100, "nonzero_cp_lower_min": .40,
                 "normal_nonzero_count_max": 12, "normal_cp_upper_max": .10},
        "log_schema": "e2_log_schema.json",
        "online_entry": "e2_status_adapter.propose_adapted(z, frozen_public_model, threshold, method)",
        "offline_evaluation": "event, age, true impact and set coverage are joined only after proposal/gate",
        "failure_policy": "retain all rows; no seed replacement, threshold changes, or E3 start",
        "outputs_required": ["config.json", "source_hashes.json", "per_seed_metrics.csv",
                             "gate_counts.json", "failure_cases.json"],
        "unfilled_at_template_time": ["owner_authorization_record", "start_timestamp",
                                      "post-commit HEAD", "actual per-seed results", "E2 gate decision"],
    }
    dump(RUN/"e2_run_manifest.template.json", template)
    print(json.dumps({"run_id": RUN.name, "status": "ASSET_BUNDLE_READY_NOT_E2",
                      "added": ["status_mapping_statistics.json", "e2_log_schema.json",
                                "model_builder_inputs_addendum.json", "environment_freeze.json",
                                "e2_run_manifest.template.json"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
