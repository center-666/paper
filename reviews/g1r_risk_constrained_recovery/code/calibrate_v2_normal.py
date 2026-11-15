"""Independent 199-trajectory normal calibration for the frozen v2 scores."""
from __future__ import annotations

import argparse
import contextlib
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import platform
import sys
import time

import numpy as np
import scipy

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "reviews/g1r_risk_constrained_recovery"
SIM = ROOT / "simulation"
OLD_CODE = ROOT / "reviews/g1_retroactive_recovery/code"
sys.path.insert(0, str(SIM))
sys.path.insert(0, str(OLD_CODE))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from engine import simulate
from model import generate_data
from minimal_recovery_screen import build_model, common_schedule
import v2_estimators


SEEDS = np.arange(141410000, 141410199, dtype=np.int64)
METHODS = ("hard_gls_capped", "correct_joint_soft_impact_capped",
           "set_constrained_chebyshev")
TIMES = np.arange(211, 217, dtype=int)
RECEIVER = 1
ORDER_RANK = 190


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8", newline="\n")


def main(out: Path):
    if out.exists():
        raise FileExistsError(f"Preserve existing calibration: {out}")
    out.mkdir(parents=True)
    started = time.perf_counter()
    protocol = json.loads((BASE / "protocol_v2.json").read_text(encoding="utf-8"))
    if len(SEEDS) != protocol["normal_calibration"]["count"]:
        raise AssertionError("calibration seed count differs from frozen protocol")
    model = build_model()
    matrix_path = ROOT / protocol["joint_statistics_npz"]
    public = v2_estimators.public_model_from_npz(matrix_path, protocol)
    x, y = generate_data(model, SEEDS)
    schedule = common_schedule(model, len(SEEDS))
    run = simulate(model, x, y, SEEDS, "yang", scenario="clean",
                   schedule=schedule, collect=False)

    rows = []
    score_columns = {method: [] for method in METHODS}
    status_counts = {method: {} for method in METHODS}
    for trial, seed in enumerate(SEEDS):
        own = run.estimates[trial, TIMES, RECEIVER]
        measurements = y[trial, TIMES, RECEIVER]
        z = (measurements - np.einsum("ab,tb->ta", model.H[RECEIVER], own)).reshape(-1)
        if z.shape != (12,) or not np.all(np.isfinite(z)):
            raise AssertionError((int(seed), "invalid receiver-only innovation"))
        for method in METHODS:
            proposal = v2_estimators.propose(z, public, method)
            if not np.isfinite(proposal.score) or not np.all(np.isfinite(proposal.action)):
                raise AssertionError((int(seed), method, proposal.status))
            norm = float(np.linalg.norm(proposal.action))
            if norm > protocol["U_common"] + 1e-14:
                raise AssertionError((int(seed), method, norm))
            score = max(0.0, float(proposal.score))
            score_columns[method].append(score)
            status_counts[method][proposal.status] = status_counts[method].get(proposal.status, 0) + 1
            cert = proposal.certificate or {}
            rows.append({"seed": int(seed), "method": method,
                         "status": proposal.status, "score": score,
                         "action_norm_before_gate": norm,
                         "solver_stage": cert.get("stage", ""),
                         "solver_reason": cert.get("reason", ""),
                         "coverage_candidates": cert.get("coverage_candidates", ""),
                         "score_lower": cert.get("score_lower", ""),
                         "score_upper": cert.get("score_upper", ""),
                         "center_gap_squared": cert.get("gap_squared", "")})

    thresholds, tie_audit = {}, {}
    for method, scores_list in score_columns.items():
        scores = np.sort(np.asarray(scores_list, dtype=np.float64))
        threshold = float(scores[ORDER_RANK - 1])
        thresholds[method] = threshold
        tie_audit[method] = {
            "rank_1based": ORDER_RANK,
            "threshold": threshold,
            "greater_count_on_calibration_not_test_fpr": int(np.sum(scores > threshold)),
            "equal_count": int(np.sum(scores == threshold)),
            "strict_comparison": ">",
            "status_counts": status_counts[method],
        }

    with (out / "calibration_scores.csv").open("w", encoding="utf-8-sig",
                                                newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    source_paths = [Path(__file__).resolve(), Path(v2_estimators.__file__).resolve(),
                    BASE / "protocol_v2.json", BASE / "code/test_v2_estimators.py",
                    BASE / "code/run_v2_debug.py", SIM / "model.py", SIM / "engine.py",
                    OLD_CODE / "minimal_recovery_screen.py", matrix_path,
                    BASE / "11_v2_solver_and_information_contract.md",
                    BASE / "sources/task5_v2_20261114_r06/seed_collision_scan.json",
                    BASE / "results/g1r_task5_debug_20261115_r04/config.json",
                    BASE / "results/g1r_task5_debug_20261115_r04/summary.json"]
    blas = io.StringIO()
    with contextlib.redirect_stdout(blas):
        np.show_config()
    config = {
        "run_id": out.name,
        "date_utc": datetime.now(timezone.utc).isoformat(),
        "baseline_commit": "07b9625e9062aeb9c2daccaf31fd86cef49adddc",
        "scope": "Frozen v2 normal calibration only; no E2/E3 evaluation",
        "seed_start": int(SEEDS[0]), "seed_count": len(SEEDS),
        "seeds": [int(s) for s in SEEDS],
        "trajectory_type": "independent clean normal Yang-form trajectories",
        "same_normal_trajectories_for_all_methods": True,
        "feature": "receiver 1 own innovation y-H*own estimate at times 211..216",
        "method_order_statistics_1based": ORDER_RANK,
        "strict_threshold_comparison": ">",
        "thresholds": thresholds,
        "threshold_order_statistic": {"sample_count": len(SEEDS),
                                      "rank_1based": ORDER_RANK,
                                      "rule": "sorted_scores[189]",
                                      "comparison": "strictly greater"},
        "tie_audit": tie_audit,
        "score_statuses_included": "all; solver rejects are score zero",
        "normal_risk_guarantee": "marginal over independent calibration set and future normal test sample; not conditional on this realized threshold",
        "no_test_or_attack_trajectory_used": True,
        "no_parameter_or_structure_selection": True,
        "E2": False, "E3": False,
        "new_communication_bytes": 0,
        "source_sha256": {p.relative_to(ROOT).as_posix(): sha(p) for p in source_paths},
        "python": platform.python_version(), "numpy": np.__version__,
        "scipy": scipy.__version__, "blas_configuration": blas.getvalue(),
    }
    write_json(out / "calibration_manifest.json", config)
    threshold_manifest = {
        "run_id": out.name,
        "thresholds": thresholds,
        "status_counts": status_counts,
        "seed_sha256": hashlib.sha256(SEEDS.astype("<i8").tobytes()).hexdigest(),
        "source_sha256": config["source_sha256"],
        "trajectory_file_sha256": sha(out / "calibration_scores.csv"),
        "status": "FROZEN_FOR_E2_ONLY_NOT_E2_RESULT",
        "strict_comparison": ">",
        "normal_risk_guarantee": config["normal_risk_guarantee"],
    }
    write_json(out / "frozen_thresholds.json", threshold_manifest)
    summary = {"run_id": out.name, "result": "CALIBRATION_COMPLETE_NOT_E2",
               "seed_count": len(SEEDS), "thresholds": thresholds,
               "status_counts": status_counts,
               "all_actions_within_U": True, "all_scores_finite": True,
               "new_trajectories": len(SEEDS),
               "seeds_used": [int(s) for s in SEEDS],
               "E2": False, "E3": False,
               "normal_thresholds_frozen": True,
               "performance_claim": "NONE",
               "elapsed_seconds": time.perf_counter() - started}
    write_json(out / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    main(args.out if args.out.is_absolute() else ROOT / args.out)
