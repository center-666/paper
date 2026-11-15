"""Diagnose archived normal and five fixed debug Set zero-score cases."""
from __future__ import annotations
import argparse
import csv
import itertools
import json
from pathlib import Path
import sys

import numpy as np
from scipy.spatial import ConvexHull, QhullError

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "reviews/g1r_risk_constrained_recovery"
sys.path.insert(0, str(BASE / "code"))
import v2_estimators as est


def hull_contains_origin(ellipses):
    points = []
    eye = np.eye(2)
    for ellipse in ellipses:
        points.append(ellipse.center)
        for axis in eye:
            points.append(est._support(ellipse, axis))
            points.append(est._support(ellipse, -axis))
    try:
        hull = ConvexHull(np.asarray(points))
        offsets = hull.equations[:, 2]
        return bool(np.all(offsets <= 256.0 * est.EPS)), offsets.tolist()
    except QhullError:
        return False, []


def smallest_support_subset(ellipses):
    for size in range(1, len(ellipses) + 1):
        for indices in itertools.combinations(range(len(ellipses)), size):
            subset = [ellipses[i] for i in indices]
            contains, offsets = hull_contains_origin(subset)
            if contains:
                return {"event_indices": list(indices),
                        "events": [list(e.event) for e in subset],
                        "support_hull_offsets": offsets}
    return None


def ellipse_origin_table(z, chol, public, ellipses):
    rows = []
    for event, ellipse in zip(public["events"], ellipses):
        fit = est._event_gls(z, chol, event)
        shape = ellipse.shape
        coords, *_ = np.linalg.lstsq(shape, -ellipse.center, rcond=1e-12)
        residual = float(np.linalg.norm(shape @ coords + ellipse.center))
        radius2 = float(coords @ coords)
        inside = (residual <= 1e-10 * max(1.0, np.linalg.norm(ellipse.center))
                  and radius2 <= 1.0 + 1e-10)
        rows.append({"event": list(ellipse.event),
                     "compatibility_residual": fit["residual"],
                     "residual_threshold": public["t_r"],
                     "effect_center": ellipse.center.tolist(),
                     "effect_shape": ellipse.shape.tolist(),
                     "origin_mahalanobis_radius_squared": radius2,
                     "origin_reconstruction_residual": residual,
                     "origin_in_this_ellipse": inside})
    return rows


def main(out: Path):
    if out.exists():
        raise FileExistsError(f"Preserve prior zero-score diagnosis: {out}")
    protocol = json.loads((BASE / "protocol_v2.json").read_text(encoding="utf-8"))
    cal_path = BASE / "results/g1r_task5_calibration_20261115_r01/calibration_scores.csv"
    with cal_path.open(encoding="utf-8-sig", newline="") as stream:
        cal_rows = [row for row in csv.DictReader(stream)
                    if row["method"] == "set_constrained_chebyshev"]
    per_seed = []
    for row in cal_rows:
        assert float(row["score"]) == 0.0
        assert float(row["score_lower"]) == 0.0 and float(row["score_upper"]) == 0.0
        assert int(row["coverage_candidates"]) == 8 and row["status"] == "VALID"
        per_seed.append({"seed": int(row["seed"]),
                         "classification": "VALID_ZERO_OR_UNRESOLVED_NUMERIC_SEPARATION",
                         "score_interval": [0.0, 0.0], "compatible_event_count": 8,
                         "solver_reject": False,
                         "per_event_geometry_saved": False})

    npz = BASE / "results/g1r_replay_joint_20261114_r01/replay_joint_matrices.npz"
    public = est.public_model_from_npz(npz, protocol)
    debug_npz = BASE / "results/g1r_task5_diagnosis_20261115_r01/debug_features.npz"
    debug_rows = []
    with np.load(debug_npz, allow_pickle=False) as data:
        for key in data.files:
            z = data[key]
            chol = np.linalg.cholesky(public["Sigma_eta"])
            ellipses, rejected, boundary = est._build_set_ellipses(z, chol, public)
            proposal = est.propose_set(z, public)
            contains, offsets = hull_contains_origin(ellipses) if ellipses else (False, [])
            debug_rows.append({
                "feature_key": key, "scenario": key.split("_")[0],
                "seed": int(key.split("_")[-1]),
                "proposal_status": proposal.status, "proposal_score": proposal.score,
                "proposal_certificate": proposal.certificate,
                "compatible_event_count": len(ellipses),
                "rejected_events": rejected, "boundary_retained": boundary,
                "initial_support_hull_contains_zero_with_qhull_tolerance": contains,
                "initial_support_hull_offsets": offsets,
                "per_event_origin_membership": ellipse_origin_table(z, chol, public, ellipses),
                "smallest_support_subset_containing_zero": smallest_support_subset(ellipses) if ellipses else None,
            })
    record = {
        "scope": "Read-only recomputation from archived calibration scores and five-seed z cache; no RNG or trajectory generation",
        "calibration": {
            "set_rows": len(per_seed), "all_scores_zero": True,
            "all_score_bounds_zero": True, "all_eight_candidates_compatible": True,
            "all_status_valid": True, "per_seed": per_seed,
            "cause_boundary": "Calibration files establish [0,0] score bounds, eight retained candidates and no solver reject. Calibration z and per-event supports were not persisted, so exact per-event normal geometry cannot be reconstructed without rerunning calibration. The implemented score path classifies the convex-hull distance as zero/unresolved, including the Qhull tolerance path; this is distinct from an empty set or solver error."},
        "debug": debug_rows,
        "zero_rule": "score lower bound <=1e-10 yields zero/unresolved proposal; strict gate is score > threshold"}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8", newline="\n")
    print(json.dumps({"calibration_zero_rows": len(per_seed),
                      "debug_rows_recomputed": len(debug_rows), "output": str(out)},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    main(args.out if args.out.is_absolute() else ROOT / args.out)
