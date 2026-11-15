"""Read-only checks for the completed Task 5 debug and calibration runs."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "reviews/g1r_risk_constrained_recovery"

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main(out: Path):
    if out.exists():
        raise FileExistsError(f"Preserve existing validation: {out}")
    protocol = load(BASE / "protocol_v2.json")
    collision = load(BASE / "sources/task5_v2_20261114_r06/seed_collision_scan.json")
    prior = load(BASE / "sources/task5_completion_20261114/protected_start.json")
    debug_dir = BASE / "results/g1r_task5_debug_20261115_r05"
    cal_dir = BASE / "results/g1r_task5_calibration_20261115_r01"
    debug = load(debug_dir / "summary.json")
    cal = load(cal_dir / "calibration_manifest.json")
    frozen = load(cal_dir / "frozen_thresholds.json")
    cal_summary = load(cal_dir / "summary.json")
    rows = list(csv.DictReader((cal_dir / "calibration_scores.csv").open(encoding="utf-8-sig")))
    methods = tuple(protocol["methods"])
    seeds = list(range(141410000, 141410199))
    thresholds, ties, statuses = {}, {}, {}
    for method in methods:
        rs = [row for row in rows if row["method"] == method]
        assert len(rs) == 199 and sorted(int(row["seed"]) for row in rs) == seeds
        scores = sorted(float(row["score"]) for row in rs)
        thresholds[method] = scores[189]
        assert thresholds[method] == cal["thresholds"][method] == frozen["thresholds"][method]
        statuses[method] = {}
        for row in rs:
            statuses[method][row["status"]] = statuses[method].get(row["status"], 0) + 1
        assert statuses[method] == cal_summary["status_counts"][method]
        assert statuses[method].get("SOLVER_REJECT", 0) == 0
        ties[method] = {"greater": sum(score > scores[189] for score in scores),
                        "equal": sum(score == scores[189] for score in scores),
                        "positive_scores": sum(score > 0 for score in scores)}
    assert thresholds["set_constrained_chebyshev"] == 0.0
    assert ties["set_constrained_chebyshev"]["positive_scores"] == 0
    assert sha(cal_dir / "calibration_scores.csv") == frozen["trajectory_file_sha256"]
    assert frozen["strict_comparison"] == ">"
    source_checks = {name: sha(ROOT / name) == digest
                     for name, digest in cal["source_sha256"].items()}
    assert all(source_checks.values()), [k for k, v in source_checks.items() if not v]
    debug_rows = list(csv.DictReader((debug_dir / "proposal_debug.csv").open(encoding="utf-8-sig")))
    assert len(debug_rows) == 30
    assert debug["status_counts"] == {method: {"VALID": 10} for method in methods}
    assert all(float(row["action_norm"]) <= protocol["U_common"] + 1e-14 for row in debug_rows)
    assert debug["seeds_used"] == list(range(141400000, 141400005))
    assert not debug["E2"] and not debug["E3"]
    assert not collision["text_file_collisions"]
    assert not collision["oversize_files_unscanned"] and not collision["unreadable_files"]
    assert all(not item.get("hits") and not item.get("skipped_members")
               for item in collision["zip_archives"])
    assert sha(ROOT / "simulation/engine.py") == protocol["input_sha256"]["simulation/engine.py"]
    assert sha(ROOT / "simulation/model.py") == protocol["input_sha256"]["simulation/model.py"]
    changed = [name for name, digest in prior["tracked_sha256"].items()
               if not (ROOT / name).is_file() or sha(ROOT / name) != digest]
    allowed = {"reviews/g1r_risk_constrained_recovery/11_v2_solver_and_information_contract.md",
               "reviews/g1r_risk_constrained_recovery/EXECUTIVE_SUMMARY.md"}
    assert set(changed) <= allowed, changed
    record = {
        "date": "2026-11-15",
        "baseline_commit": cal["baseline_commit"],
        "result": "TASK5_IMPLEMENTATION_AND_CALIBRATION_COMPLETE_E2_NOT_RUN",
        "scope": "Task 5 only; no E2/E3 or performance claim",
        "protected_tracked_files": len(prior["tracked_sha256"]),
        "preexisting_tracked_files_modified": changed,
        "debug_run_id": debug["run_id"],
        "debug_seeds": debug["seeds_used"],
        "debug_trajectories": debug["new_trajectories"],
        "debug_status_counts": debug["status_counts"],
        "calibration_run_id": cal["run_id"],
        "calibration_seed_start": cal["seed_start"],
        "calibration_seed_count": cal["seed_count"],
        "calibration_thresholds": thresholds,
        "threshold_tie_audit": ties,
        "calibration_status_counts": statuses,
        "calibration_sources_all_match": True,
        "collision_scan": {"files": collision["scanned_workspace_files"],
                           "archives": len(collision["zip_archives"]),
                           "collisions": 0, "unreadable": 0, "oversize": 0},
        "E2_readiness": {
            "technical_preconditions": "PASS_FOR_OWNER_REVIEW",
            "Set_score_degeneracy": "all 199 normal calibration scores are zero; threshold is zero",
            "E2_performance_gates": "UNTESTED",
            "E2_execution": "NOT_RUN",
            "E3_execution": "NOT_RUN",
            "authorization": "separate owner review required"},
        "performance_claim": "NONE"}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8", newline="\n")
    print(json.dumps(record, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    main(args.out if args.out.is_absolute() else ROOT / args.out)
