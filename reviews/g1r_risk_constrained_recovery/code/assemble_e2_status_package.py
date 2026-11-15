"""Assemble the final B.1 status-resolution evidence package; no E2 execution."""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
import platform
from pathlib import Path
import subprocess
import sys

import numpy as np
import scipy

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "reviews/g1r_risk_constrained_recovery"
SOURCE_RUN = BASE / "results/g1r_e2_status_resolution_20261115_r05"
TEMPLATE_RUN = BASE / "results/g1r_e2_status_resolution_20261115_r09"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+"\n",
                    encoding="utf-8", newline="\n")


def main(out: Path):
    if out.exists():
        raise FileExistsError(f"Preserve previous final status package: {out}")
    out.mkdir(parents=True)
    # Reuse the already verified cached-input run; no proposal is recomputed.
    for name in ["cached_debug_features.npz", "proposal_equivalence.csv",
                 "equivalence_manifest.json"]:
        src = SOURCE_RUN / name
        if not src.is_file():
            raise FileNotFoundError(src)
        (out/name).write_bytes(src.read_bytes())
    for name in ["e2_log_schema.json", "model_builder_inputs_addendum.json"]:
        (out/name).write_bytes((BASE/name).read_bytes())
    seed_scan_path = (BASE/"results/g1r_pre_e2_readonly_audit_20261115_r04/e2_seed_scan.json")
    seed_scan = json.loads(seed_scan_path.read_text(encoding="utf-8"))
    if (seed_scan.get("collision_count") != 0
            or len(seed_scan.get("per_seed", [])) != 400
            or any(row.get("status") != "NO_COLLISION_IN_SCANNED_SCOPE"
                   for row in seed_scan["per_seed"])):
        raise ValueError("frozen E2 seed scan is incomplete or reports a collision")
    (out/"e2_seed_scan.json").write_bytes(seed_scan_path.read_bytes())
    template = json.loads((TEMPLATE_RUN/"e2_run_manifest.template.json").read_text(encoding="utf-8"))
    template.pop("implementation_commit_after_task_completion", None)
    template["execution_commit_sha_at_run_start"] = (
        "UNFILLED: record audited Task B.1 commit SHA only when E2 is separately authorized")
    template["unfilled_at_template_time"] = sorted(set(
        template["unfilled_at_template_time"] + ["execution_commit_sha_at_run_start"]))
    dump(out/"e2_run_manifest.template.json", template)

    subprocess.run([sys.executable, str(BASE/"code/test_e2_status_adapter.py"),
                    "--out", str(out/"adapter_tests.json")], check=True, cwd=ROOT)
    subprocess.run([sys.executable, str(BASE/"code/test_e2_deterministic_validation.py"),
                    "--out", str(out/"deterministic_validation.json")], check=True, cwd=ROOT)
    subprocess.run([sys.executable, str(BASE/"code/test_v2_data_mechanics.py"),
                    "--out", str(out/"data_mechanics.json")], check=True, cwd=ROOT)

    rows = list(csv.DictReader((out/"proposal_equivalence.csv").open(encoding="utf-8-sig")))
    stats = {}
    for method in sorted({row["method"] for row in rows}):
        subset = [row for row in rows if row["method"] == method]
        counts = lambda field: {value: sum(row[field] == value for row in subset)
                                for value in sorted({row[field] for row in subset})}
        stats[method] = {
            "debug_records": len(subset),
            "raw_status_counts": counts("raw_status"),
            "proposal_status_counts": counts("proposal_status"),
            "gate_status_counts": counts("gate_status"),
            "zero_or_unresolved_count": sum(
                row["certificate_zero_or_unresolved"].lower() == "true" for row in subset),
            "post_gate_nonzero_actions": sum(float(row["action_norm_after_gate"]) > 1e-12
                                             for row in subset),
            "interpretation": "fixed five-seed debug diagnostics only; not a rate estimate",
        }
    dump(out/"status_mapping_statistics.json", {
        "source": "proposal_equivalence.csv",
        "data_scope": "ten already cached Debug vectors; no new random data",
        "counts": stats,
    })

    protocol = json.loads((BASE/"protocol_v2.json").read_text(encoding="utf-8"))
    cal_path = BASE/"results/g1r_task5_calibration_20261115_r01/calibration_manifest.json"
    cal = json.loads(cal_path.read_text(encoding="utf-8"))
    threshold_path = BASE/"results/g1r_task5_calibration_20261115_r01/frozen_thresholds.json"
    blas = io.StringIO()
    import contextlib
    with contextlib.redirect_stdout(blas):
        np.show_config()
    runtime_matches = {
        "python": platform.python_version() == cal["python"],
        "numpy": np.__version__ == cal["numpy"],
        "scipy": scipy.__version__ == cal["scipy"],
        "blas_exact": blas.getvalue() == cal["blas_configuration"],
    }
    for key, path in [
        ("simulation/model.py", ROOT/"simulation/model.py"),
        ("simulation/engine.py", ROOT/"simulation/engine.py"),
        ("simulation/config.json", ROOT/"simulation/config.json"),
        ("simulation/reference_exploration_plan.json", ROOT/"simulation/reference_exploration_plan.json"),
        ("reviews/g1r_risk_constrained_recovery/protocol_v2.json", BASE/"protocol_v2.json"),
        ("reviews/g1r_risk_constrained_recovery/code/v2_estimators.py", BASE/"code/v2_estimators.py"),
        ("reviews/g1r_risk_constrained_recovery/code/calibrate_v2_normal.py", BASE/"code/calibrate_v2_normal.py"),
    ]:
        expected = cal["source_sha256"].get(key)
        runtime_matches[key] = expected is not None and sha(path) == expected
    input_addendum = json.loads(
        (BASE/"model_builder_inputs_addendum.json").read_text(encoding="utf-8"))
    for row in input_addendum["inputs"]:
        runtime_matches[row["path"]] = (
            sha(ROOT/row["path"]) == row["current_sha256"]
            == row["task5_start_snapshot_sha256"])
    source_paths = [
        BASE/"code/e2_status_adapter.py",
        BASE/"code/e2_statistics.py",
        BASE/"code/test_e2_status_adapter.py",
        BASE/"code/test_e2_statistics.py",
        BASE/"code/test_e2_deterministic_validation.py",
        BASE/"code/test_v2_data_mechanics.py",
        BASE/"code/verify_e2_adapter_equivalence.py",
        BASE/"code/assemble_e2_status_package.py",
        BASE/"code/v2_estimators.py",
        BASE/"code/calibrate_v2_normal.py",
        BASE/"protocol_v2.json", threshold_path, cal_path,
        ROOT/"simulation/model.py", ROOT/"simulation/engine.py",
        ROOT/"simulation/config.json", ROOT/"simulation/reference_exploration_plan.json",
        BASE/"model_builder_inputs_addendum.json", seed_scan_path,
    ]
    seed_scan_summary = {
        "path": "e2_seed_scan.json",
        "sha256": sha(seed_scan_path),
        "seed_count": len(seed_scan["per_seed"]),
        "collision_count": seed_scan["collision_count"],
        "scope_note": seed_scan["scope_note"],
    }
    env = json.loads((out/"e2_run_manifest.template.json").read_text(encoding="utf-8"))
    env_freeze = {
        "status": "FROZEN_AUDIT_WORKTREE_NOT_AN_EXECUTED_E2_RUN",
        "worktree": str(ROOT),
        "branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip(),
        "baseline_commit": "490e5b8f1212004407a0cdbfde224bf90a691da4",
        "source_equivalence_run": "g1r_e2_status_resolution_20261115_r05",
        "formal_seed_data_generated": False,
        "deterministic_fixture_seed_used": 0,
        "checkout_was_created_at_clean_baseline": True,
        "current_worktree_contains_this_audit_changes": True,
        "runtime_matches_calibration_manifest": runtime_matches,
        "all_runtime_and_core_hashes_match": all(runtime_matches.values()),
        "calibration_threshold_file_sha256": sha(threshold_path),
        "calibration_manifest_sha256": sha(cal_path),
        "thresholds": json.loads(threshold_path.read_text(encoding="utf-8"))["thresholds"],
        "e2_manifest_state": env["state"],
        "e2_execution_authorized": False,
        "new_communication_bytes": 0,
        "source_sha256": {p.relative_to(ROOT).as_posix(): sha(p) for p in source_paths},
        "seed_scan": seed_scan_summary,
        "scope_note": "E2 template is fully parameterized but intentionally retains owner authorization, run start time, and actual E2 commit/result fields as unfilled because E2 is not authorized or executed.",
    }
    dump(out/"environment_freeze.json", env_freeze)
    dump(out/"model_builder_inputs_addendum.json",
         json.loads((BASE/"model_builder_inputs_addendum.json").read_text(encoding="utf-8")))
    manifest_paths = [p for p in out.iterdir() if p.is_file() and p.name != "package_manifest.json"]
    manifest = {
        "run_id": out.name,
        "baseline_commit": "490e5b8f1212004407a0cdbfde224bf90a691da4",
        "source_cached_debug_run": "g1r_e2_status_resolution_20261115_r05",
        "e2_executed": False, "e3_executed": False,
        "new_random_trajectories": 0,
        "files_sha256": {p.name: sha(p) for p in sorted(manifest_paths)},
    }
    dump(out/"package_manifest.json", manifest)
    print(json.dumps({"run_id": out.name, "files": len(manifest_paths)+1,
                      "runtime_matches": runtime_matches,
                      "equivalence_records": len(rows),
                      "E2_executed": False, "E3_executed": False},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    main(args.out if args.out.is_absolute() else ROOT/args.out)
