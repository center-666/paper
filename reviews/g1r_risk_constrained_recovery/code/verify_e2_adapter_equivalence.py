"""Compare frozen and adapted proposal/gate outputs on cached five-seed Debug z."""
from __future__ import annotations
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "reviews/g1r_risk_constrained_recovery"
sys.path.insert(0, str(BASE / "code"))
import e2_status_adapter as adapter
import v2_estimators as frozen

DEFAULT_CACHE = Path(
    r"C:\Users\zhongxin\shixidoc\mypaper\reviews\g1r_risk_constrained_recovery"
    r"\results\g1r_task5_diagnosis_20261115_r01\debug_features.npz")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def native(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(k): native(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [native(v) for v in value]
    return value


def exact(left, right, label):
    a, b = native(left), native(right)
    if a != b:
        raise AssertionError(f"{label} changed: {a!r} != {b!r}")


def main(out: Path, debug_cache: Path):
    if out.exists():
        raise FileExistsError(f"Preserve previous equivalence run: {out}")
    if not debug_cache.is_file():
        raise FileNotFoundError(debug_cache)
    cache_sha = sha(debug_cache)
    artifacts = json.loads((BASE / "task5_artifact_manifest.json").read_text(encoding="utf-8"))
    expected_sha = artifacts["files"]["reviews/g1r_risk_constrained_recovery/results/g1r_task5_diagnosis_20261115_r01/debug_features.npz"]
    if cache_sha != expected_sha:
        raise ValueError("cached Debug feature SHA does not match Task5 artifact manifest")

    out.mkdir(parents=True)
    start = time.perf_counter()
    protocol = json.loads((BASE / "protocol_v2.json").read_text(encoding="utf-8"))
    frozen_thresholds = json.loads(
        (BASE / "results/g1r_task5_calibration_20261115_r01/frozen_thresholds.json")
        .read_text(encoding="utf-8"))
    calibration_manifest = json.loads(
        (BASE / "results/g1r_task5_calibration_20261115_r01/calibration_manifest.json")
        .read_text(encoding="utf-8"))
    public = frozen.public_model_from_npz(ROOT / protocol["joint_statistics_npz"], protocol)
    expected_keys = {f"{scenario}_{seed}"
                     for scenario in ("clean", "replay_packet")
                     for seed in range(141400000, 141400005)}
    inputs = {}
    with np.load(debug_cache, allow_pickle=False) as archive:
        assert set(archive.files) == expected_keys
        for key in sorted(expected_keys):
            z = np.asarray(archive[key], dtype=np.float64)
            if z.shape != (12,) or not np.all(np.isfinite(z)):
                raise AssertionError(f"bad Debug vector {key}")
            inputs[key] = z.copy()
    cached_copy = out / "cached_debug_features.npz"
    np.savez_compressed(cached_copy, **inputs)

    rows = []
    status_counts = {}
    eq_counts = {k: 0 for k in ["score", "proposal_vector", "raw_status",
                                 "certificate", "gate_status", "gate_vector"]}
    for key, z in inputs.items():
        scenario, seed_text = key.rsplit("_", 1)
        seed = int(seed_text)
        for method in protocol["methods"]:
            threshold = float(frozen_thresholds["thresholds"][method])
            reference_raw = frozen.propose(z, public, method)
            adapted = adapter.propose_adapted(z, public, threshold, method)
            raw = adapted.raw
            if raw is None:
                raise AssertionError(f"{key}/{method}: adapter omitted raw Proposal")
            expected_gate = frozen.apply_gate(reference_raw, threshold)
            exact(reference_raw.score, raw.score, f"{key}/{method}/score")
            exact(reference_raw.action, raw.action, f"{key}/{method}/proposal")
            exact(reference_raw.status, raw.status, f"{key}/{method}/raw status")
            exact(reference_raw.certificate or {}, raw.certificate or {},
                  f"{key}/{method}/certificate")
            exact(expected_gate.status, adapted.gated.status, f"{key}/{method}/gate status")
            exact(expected_gate.action, adapted.gated.action, f"{key}/{method}/gate action")
            exact(expected_gate.action, adapted.final_action, f"{key}/{method}/final action")
            assert adapted.raw is raw
            for field in eq_counts:
                eq_counts[field] += 1
            status_counts.setdefault(method, {})
            status_counts[method][adapted.proposal_status] = (
                status_counts[method].get(adapted.proposal_status, 0) + 1)
            cert = raw.certificate or {}
            rows.append({
                "scenario": scenario, "seed": seed, "method": method,
                "raw_status": raw.status,
                "proposal_status": adapted.proposal_status,
                "gate_status": adapted.gate_status,
                "score_before_gate": raw.score, "threshold": threshold,
                "proposal_norm_before_gate": float(np.linalg.norm(raw.action)),
                "action_norm_after_gate": adapted.action_norm_after_gate,
                "certificate_zero_or_unresolved": adapted.certificate_zero_or_unresolved,
                "coverage_candidates": cert.get("coverage_candidates", ""),
                "score_lower": cert.get("score_lower", ""),
                "score_upper": cert.get("score_upper", ""),
                "center_gap_squared": cert.get("gap_squared", ""),
                "solver_stage": cert.get("stage", ""),
                "solver_reason": cert.get("reason", ""),
                "raw_proposal_json": json.dumps(native({
                    "method": raw.method, "score": raw.score, "status": raw.status,
                    "event": raw.event, "action": raw.action,
                    "certificate": raw.certificate or {}}), sort_keys=True),
                "gated_proposal_json": json.dumps(native({
                    "method": expected_gate.method, "score": expected_gate.score,
                    "status": expected_gate.status, "event": expected_gate.event,
                    "action": expected_gate.action,
                    "certificate": expected_gate.certificate or {}}), sort_keys=True),
            })
    with (out / "proposal_equivalence.csv").open("w", encoding="utf-8-sig",
                                                 newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    source_paths = [Path(__file__).resolve(), Path(adapter.__file__).resolve(),
                    Path(frozen.__file__).resolve(), BASE / "protocol_v2.json",
                    BASE / "results/g1r_task5_calibration_20261115_r01/frozen_thresholds.json",
                    BASE / "results/g1r_task5_calibration_20261115_r01/calibration_manifest.json"]
    source_hashes = {p.relative_to(ROOT).as_posix(): sha(p) for p in source_paths}
    for relative, digest in calibration_manifest["source_sha256"].items():
        if sha(ROOT / relative) != digest:
            raise AssertionError(f"frozen calibration source changed: {relative}")
    config = {
        "run_id": out.name, "date_utc": datetime.now(timezone.utc).isoformat(),
        "baseline_commit": "490e5b8f1212004407a0cdbfde224bf90a691da4",
        "scope": "cached Debug adapter equivalence only; no RNG or new trajectories",
        "source_debug_cache_path": str(debug_cache.resolve()),
        "source_debug_cache_sha256": cache_sha,
        "expected_debug_cache_sha256": expected_sha,
        "copied_cache_file": "cached_debug_features.npz",
        "copied_cache_sha256": sha(cached_copy),
        "methods": protocol["methods"],
        "frozen_thresholds": frozen_thresholds["thresholds"],
        "calibration_manifest_sha256": sha(
            BASE / "results/g1r_task5_calibration_20261115_r01/calibration_manifest.json"),
        "comparisons": len(rows),
        "fieldwise_exact_matches": eq_counts,
        "proposal_status_counts": status_counts,
        "new_random_trajectories": 0, "E2": False, "E3": False,
        "source_sha256": source_hashes,
        "calibration_sources_match": True,
        "elapsed_seconds": time.perf_counter() - start,
    }
    (out / "equivalence_manifest.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n")
    print(json.dumps({"run_id": out.name, "records": len(rows),
                      "fieldwise_exact_matches": eq_counts,
                      "proposal_status_counts": status_counts,
                      "new_random_trajectories": 0}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--debug-cache", type=Path, default=DEFAULT_CACHE)
    args = parser.parse_args()
    main(args.out if args.out.is_absolute() else ROOT / args.out, args.debug_cache)
