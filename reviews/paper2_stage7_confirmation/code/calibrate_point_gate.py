"""Calibrate the point-compensation gate on independent healthy trajectories."""
from __future__ import annotations
import json, math, os, sys
from fractions import Fraction as F
from pathlib import Path
os.environ.update({"OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"})
import numpy as np
TASK = Path(__file__).resolve().parents[1]; REVIEWS = TASK.parent
STAGE6 = REVIEWS / "paper2_stage6_vector_correction_20261122"
sys.path.insert(0, str(STAGE6)); sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import load_json, source_hashes
from fast_point_state import FastPointState

EPISODE_DIR = TASK / "results" / "development_point_calibration_episodes"

def run_episode(episode, protocol, model, seed):
    path = EPISODE_DIR / f"health_{episode:04d}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf8"))
    phys, events, phase = [np.random.default_rng(s) for s in np.random.SeedSequence([seed, episode]).spawn(3)]
    A = np.array(model["A"], float); C = np.array(model["C"], float); Q = np.array(model["Q"], float)
    R, Z = float(model["R"]), float(model["Z"]); delta = float(model["quantization_half_width"])
    state = FastPointState(model, protocol["point_estimator_grid"])
    error = np.linalg.cholesky(np.array(model["P0_prior"], float)) @ phys.normal(size=2)
    observed = []
    for t in range(protocol["horizon"]):
        v = math.sqrt(R) * phys.normal(); w = np.linalg.cholesky(Q) @ phys.normal(size=2)
        r = 0.0 if t == 0 else delta * (2 * phase.random() - 1); y = float((C @ error).item() + v)
        sent = bool(events.random() > math.exp(-.5 * Z * (y-r)**2))
        K, _ = state.append(sent, repr(float(y)) if sent else None, repr(float(r)))
        post_error = error - K * y if sent else error - K * r
        if t in protocol["certification_times"]:
            _, _, _, score = state.proposal()
            observed.append({"time": t, "score": float(score)})
        error = A @ post_error + w
    row = {"episode": episode, "queries": observed, "max_score": max(x["score"] for x in observed)}
    EPISODE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(row, indent=2) + "\n", encoding="utf8")
    return row

def main():
    protocol = load_json(TASK / "config" / "confirmation_protocol.json")
    model = load_json(STAGE6 / "model.json")
    seed = protocol["threshold_calibration"]["development_seed"]
    rows = [run_episode(index, protocol, model, seed)
            for index in range(protocol["threshold_calibration"]["episodes"])]
    trajectory_maxima = [row["max_score"] for row in rows]
    scores_sorted = sorted(trajectory_maxima)
    thresholds = {}
    for q in protocol["threshold_calibration"]["quantiles"]:
        rank = max(0, min(len(scores_sorted)-1, math.ceil(q * len(scores_sorted)) - 1))
        thresholds[str(q)] = {"rank": rank, "n": len(scores_sorted), "value": scores_sorted[rank]}
    result = {"seed": seed, "episodes": len(rows), "trajectory_maxima": trajectory_maxima, "per_episode": rows,
              "thresholds": thresholds, "source_hashes": source_hashes()}
    out = TASK / "results" / "development_point_calibration.json"; out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf8")
    print(json.dumps(thresholds, indent=2))

if __name__ == "__main__": main()
