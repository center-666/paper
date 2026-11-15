"""Task 5 interface debug only: at most five reserved seeds.

This runner validates the receiver-only feature construction, public-model
matrix loading, three proposal interfaces, fixed gap-8 timing, and fail-closed
status codes. It does not fit thresholds, use truth in a proposal, compute
MSE, run E2/E3, or alter any shared simulator file.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys
import time

import numpy as np

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


SEEDS = np.arange(141400000, 141400005, dtype=np.int64)
TIMES = np.arange(211, 217, dtype=int)
RECEIVER = 1


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8", newline="\n")


def build_z(model, run, y, trial: int) -> np.ndarray:
    # This is exactly the declared receiver-local post-cache innovation. The
    # proposal receives only this vector, never the run object or scenario.
    own = run.estimates[trial, TIMES, RECEIVER]
    measurements = y[trial, TIMES, RECEIVER]
    innovations = measurements - np.einsum("ab,tb->ta", model.H[RECEIVER], own)
    return innovations.reshape(-1).astype(np.float64, copy=False)


def public_model(protocol):
    matrix_path = ROOT / "reviews/g1r_risk_constrained_recovery/results/g1r_replay_joint_20261114_r01/replay_joint_matrices.npz"
    return v2_estimators.public_model_from_npz(matrix_path, protocol), matrix_path


def main(out: Path):
    if out.exists():
        raise FileExistsError(f"Preserve existing debug run: {out}")
    out.mkdir(parents=True)
    started = time.perf_counter()
    run_id = out.name
    protocol = json.loads((BASE / "protocol_v2.json").read_text(encoding="utf-8"))
    model = build_model()
    public, matrix_path = public_model(protocol)
    x, y = generate_data(model, SEEDS)
    schedule = common_schedule(model, len(SEEDS))
    expected = np.zeros_like(schedule)
    ticks = np.arange(model.cfg["T"])
    for node in range(model.cfg["N"]):
        expected[:, :, node] = (ticks % 8) == node
    expected[:, 0, :] = True
    if not np.array_equal(schedule, expected):
        raise AssertionError("debug schedule is not the frozen gap-8 schedule")

    source_paths = [Path(__file__).resolve(), Path(v2_estimators.__file__).resolve(),
                    SIM / "model.py", SIM / "engine.py",
                    OLD_CODE / "minimal_recovery_screen.py",
                    BASE / "protocol_v2.json", matrix_path]
    config = {
        "run_id": run_id, "date_utc": datetime.now(timezone.utc).isoformat(),
        "baseline_commit": "07b9625e9062aeb9c2daccaf31fd86cef49adddc",
        "scope": "Task 5.4 interface and numerical debug only",
        "seeds": [int(s) for s in SEEDS], "seed_count": len(SEEDS),
        "scenarios": ["clean", "replay_packet"],
        "innovation_times": TIMES.tolist(), "receiver": RECEIVER,
        "schedule": "fixed exogenous gap8, t=0 all nodes send",
        "methods": protocol["methods"], "U_common": protocol["U_common"],
        "normal_calibration": False, "thresholds": None,
        "E2": False, "E3": False, "mse_evaluation": False,
        "proposal_input_whitelist": ["z", "frozen_public_model"],
        "forbidden_proposal_inputs": protocol["online_information"]["forbidden"],
        "new_communication_bytes": 0, "new_training_samples": 0,
        "source_sha256": {str(p.relative_to(ROOT)).replace("\\", "/"): sha(p)
                           for p in source_paths},
        "python": platform.python_version(), "platform": platform.platform(),
        "numpy": np.__version__,
    }
    save_json(out / "config.json", config)

    rows = []
    status_counts = {method: {} for method in protocol["methods"]}
    for scenario in ("clean", "replay_packet"):
        run = simulate(model, x, y, SEEDS, "yang", scenario=scenario,
                       schedule=schedule, collect=False)
        for trial, seed in enumerate(SEEDS):
            z = build_z(model, run, y, trial)
            if z.shape != (12,) or not np.all(np.isfinite(z)):
                raise AssertionError("invalid receiver-only z")
            for method in protocol["methods"]:
                begin = time.perf_counter()
                proposal = v2_estimators.propose(z, public, method)
                elapsed = time.perf_counter() - begin
                norm = float(np.linalg.norm(proposal.action))
                if not np.all(np.isfinite(proposal.action)) or not np.isfinite(proposal.score):
                    raise AssertionError((scenario, int(seed), method, proposal.status))
                if norm > float(protocol["U_common"]) + 1e-14:
                    raise AssertionError((scenario, int(seed), method, norm))
                status_counts[method][proposal.status] = status_counts[method].get(proposal.status, 0) + 1
                certificate = proposal.certificate or {}
                rows.append({
                    "scenario": scenario, "seed": int(seed), "method": method,
                    "status": proposal.status, "score": proposal.score,
                    "action_norm": norm, "elapsed_seconds": elapsed,
                    "event": "" if proposal.event is None else str(proposal.event),
                    "coverage_candidates": certificate.get("coverage_candidates", ""),
                    "score_lower": certificate.get("score_lower", ""),
                    "score_upper": certificate.get("score_upper", ""),
                    "solver_gap_squared": certificate.get("gap_squared", ""),
                    "solver_stage": certificate.get("stage", ""),
                    "solver_reason": certificate.get("reason", ""),
                })

    with (out / "proposal_debug.csv").open("w", encoding="utf-8-sig",
                                             newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "run_id": run_id, "result": "PASS_INTERFACE_DEBUG_ONLY",
        "seed_count": len(SEEDS), "scenarios": 2,
        "proposal_rows": len(rows), "status_counts": status_counts,
        "receiver_only_feature_shape": [12], "schedule_verified": True,
        "all_actions_within_common_U": True,
        "normal_calibration": False, "thresholds_frozen": False,
        "new_trajectories": len(SEEDS) * 2,
        "seeds_used": [int(s) for s in SEEDS], "E2": False, "E3": False,
        "performance_claim": "NONE",
        "elapsed_seconds": time.perf_counter() - started,
    }
    save_json(out / "summary.json", summary)
    save_json(out / "failure_policy.json", {
        "solver_reject_is_retained": True,
        "invalid_or_rejected_proposals_are_zero_actions": True,
        "no_rows_deleted_for_status": True,
        "debug_results_must_not_change_protocol": True,
    })
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    main(args.out if args.out.is_absolute() else ROOT / args.out)
