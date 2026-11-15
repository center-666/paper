"""Create a truthful post-hoc addendum for model-builder inputs omitted at calibration."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "reviews/g1r_risk_constrained_recovery"
INPUTS = ("simulation/config.json",
          "simulation/reference_exploration_plan.json")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(out: Path):
    if out.exists():
        raise FileExistsError(f"Preserve existing model input addendum: {out}")
    start = json.loads((BASE / "sources/task5_completion_20261114/protected_start.json")
                       .read_text(encoding="utf-8"))
    original = json.loads(
        (BASE / "results/g1r_task5_calibration_20261115_r01/calibration_manifest.json")
        .read_text(encoding="utf-8"))
    recorded = set(original["source_sha256"])
    entries = []
    for relative in INPUTS:
        path = ROOT / relative
        current_hash = sha(path)
        snapshot_hash = start["tracked_sha256"].get(relative)
        if snapshot_hash is None:
            raise AssertionError(f"Task5 start snapshot omitted {relative}")
        entries.append({
            "path": relative,
            "current_sha256": current_hash,
            "task5_start_snapshot_sha256": snapshot_hash,
            "unchanged_since_task5_start": current_hash == snapshot_hash,
            "present_in_original_calibration_manifest": relative in recorded,
        })
    record = {
        "created_after_original_task5_calibration": True,
        "calibration_manifest_modified": False,
        "task5_start_snapshot": "reviews/g1r_risk_constrained_recovery/sources/task5_completion_20261114/protected_start.json",
        "original_calibration_manifest": "reviews/g1r_risk_constrained_recovery/results/g1r_task5_calibration_20261115_r01/calibration_manifest.json",
        "original_manifest_sha256": sha(BASE / "results/g1r_task5_calibration_20261115_r01/calibration_manifest.json"),
        "inputs": entries,
        "provenance_note": "Post hoc provenance addendum; does not imply these hashes were recorded in the original calibration manifest.",
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8", newline="\n")
    print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    main(args.out if args.out.is_absolute() else ROOT / args.out)
