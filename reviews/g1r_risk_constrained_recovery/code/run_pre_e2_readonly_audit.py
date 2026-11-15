"""Read-only Stage A evidence aggregation; no RNG or study-trajectory generation."""
from __future__ import annotations
import argparse
import csv
import hashlib
import inspect
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "reviews/g1r_risk_constrained_recovery"
sys.path.insert(0, str(BASE / "code"))
import v2_estimators as est
from test_v2_estimators import public_model


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main(out: Path):
    if out.exists():
        raise FileExistsError(f"Preserve previous Stage A evidence: {out}")
    protocol = read(BASE / "protocol_v2.json")
    prior = read(BASE / "sources/task5_completion_20261114/protected_start.json")
    calibration = read(BASE / "results/g1r_task5_calibration_20261115_r01/calibration_manifest.json")
    frozen = read(BASE / "results/g1r_task5_calibration_20261115_r01/frozen_thresholds.json")
    debug = read(BASE / "results/g1r_task5_debug_20261115_r05/summary.json")
    scan = read(BASE / "results/g1r_pre_e2_readonly_audit_20261115_r04/e2_seed_scan.json")
    zero = read(BASE / "results/g1r_pre_e2_readonly_audit_20261115_r01/set_zero_diagnosis.json")
    fixture_path = BASE / "results/g1r_pre_e2_readonly_audit_20261115_r05/mechanics_fixture.json"
    fixture = read(fixture_path)

    cal_sources = {name: {"expected": digest,
                          "actual": sha(ROOT/name),
                          "matches": sha(ROOT/name) == digest}
                   for name, digest in calibration["source_sha256"].items()}
    build_inputs = {}
    for name in ["simulation/config.json", "simulation/reference_exploration_plan.json"]:
        current = sha(ROOT/name)
        protected = prior["tracked_sha256"][name]
        build_inputs[name] = {"current_sha256": current,
                              "pre_task5_snapshot_sha256": protected,
                              "unchanged_since_task5_start": current == protected}

    branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    status = subprocess.check_output(["git", "status", "--short"], cwd=ROOT, text=True).splitlines()
    protocol_hash = sha(BASE/"protocol_v2.json")
    assert protocol_hash == calibration["source_sha256"]["reviews/g1r_risk_constrained_recovery/protocol_v2.json"]

    # Exercise status metadata on a deterministic zero-score public model.
    tiny = public_model()
    zero_proposal = est.propose_set(np.zeros(2), tiny)
    assert zero_proposal.score == 0.0 and np.all(zero_proposal.action == 0.0)
    zero_status_audit = {
        "proposal_status": zero_proposal.status,
        "certificate_zero_or_unresolved": bool((zero_proposal.certificate or {}).get("zero_or_unresolved")),
        "expected_frozen_status_name": "ZERO_OR_UNRESOLVED",
        "contract_match": zero_proposal.status == "ZERO_OR_UNRESOLVED",
    }
    invalid_soft = est.propose_soft(np.array([np.nan, 0.0]), tiny)
    input_status_audit = {
        "actual_status": invalid_soft.status,
        "expected_status_for_nonfinite_z": "INPUT_INVALID",
        "fail_closed_zero_action": bool(np.all(invalid_soft.action == 0.0)),
        "category_match": invalid_soft.status == "INPUT_INVALID",
    }

    if len(scan["per_seed"]) != 400:
        raise AssertionError("expected a per-seed status for all 400 frozen E2 seeds")
    if scan["collision_count"] != 0:
        raise AssertionError("E2 seed collision scan reported a historical match")
    if not all(source["matches"] for source in cal_sources.values()):
        raise AssertionError("calibration source hash mismatch")
    if not all(value["unchanged_since_task5_start"] for value in build_inputs.values()):
        raise AssertionError("model-builder config changed after Task5 start")

    record = {
        "run_id": out.parent.name,
        "scope": "Stage A read-only evidence; no new study trajectory or E2/E3 data",
        "baseline_commit": "cca08e75f95bd61425a980efde5d80ece00cf7fe",
        "current_head": head,
        "branch": branch,
        "worktree_clean": len(status) == 0,
        "worktree_status_lines": status,
        "task5_calibration_protocol_hash_matches": True,
        "protocol_runtime_status_note": {
            "protocol_v2_status": protocol["status"],
            "normal_calibration_status_in_protocol": protocol["normal_calibration"]["status"],
            "actual_runtime_thresholds_saved_separately": True,
            "protocol_file_edited_after_calibration": False},
        "calibration_source_hashes": cal_sources,
        "model_builder_input_hashes": build_inputs,
        "calibration_thresholds": frozen["thresholds"],
        "debug_run": {"run_id": debug["run_id"], "status_counts": debug["status_counts"]},
        "e2_seed_scan": {"run": "g1r_pre_e2_readonly_audit_20261115_r04",
                          "collision_count": scan["collision_count"],
                          "per_seed_rows": len(scan["per_seed"]),
                          "workspace_files": scan["workspace_file_count"],
                          "npz_npy_scanned": scan["npz_npy_scanned"],
                          "npz_npy_count": scan["npz_npy_count"],
                          "zip_archives": len(scan["zip_archives"]),
                          "numeric_errors": len(scan["numeric_array_errors"]),
                          "zip_errors": len(scan["zip_errors"]),
                          "external_media_scanned": False},
        "normal_set_diagnosis": {
            "seeds": len(zero["calibration"]["per_seed"]),
            "all_scores_zero_and_bounds_zero": zero["calibration"]["all_scores_zero"] and zero["calibration"]["all_score_bounds_zero"],
            "all_8_candidates_compatible": zero["calibration"]["all_eight_candidates_compatible"],
            "solver_rejects": sum(x["solver_reject"] for x in zero["calibration"]["per_seed"]),
            "per_event_geometry_available": False,
            "reason_limit": zero["calibration"]["cause_boundary"]},
        "debug_zero_diagnosis": [
            {"feature_key": row["feature_key"],
             "proposal_status": row["proposal_status"],
             "score": row["proposal_score"],
             "compatible_events": row["compatible_event_count"],
             "origin_containing_events": [event["event"] for event in row["per_event_origin_membership"] if event["origin_in_this_ellipse"]],
             "minimum_support_subset": row["smallest_support_subset_containing_zero"]}
            for row in zero["debug"] if row["feature_key"].startswith("replay_packet") and row["proposal_score"] == 0.0],
        "status_contract_audit": {"zero_or_unresolved": zero_status_audit,
                                   "soft_nonfinite_input": input_status_audit},
        "deterministic_data_mechanics_fixture": fixture,
        "new_e2_or_performance_trajectory": False,
        "fixed_seed_fixture_detail": {"seed": fixture["fixed_fixture_seed"],
                                       "repeat_count": 2,
                                       "used_for_performance_or_calibration": False},
        "E2_or_E3_run": False,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8", newline="\n")
    print(json.dumps({"run_id": out.parent.name, "branch": branch, "head": head,
                      "worktree_clean": record["worktree_clean"],
                      "e2_collisions": scan["collision_count"],
                      "status_mismatches": int(not zero_status_audit["contract_match"])
                      + int(not input_status_audit["category_match"])},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    main(args.out if args.out.is_absolute() else ROOT / args.out)
