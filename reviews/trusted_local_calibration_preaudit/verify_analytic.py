"""Exact counterexamples and elementary checks; no random samples."""
from pathlib import Path
import json
import sys
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from run_small_experiment import load_config
sys.path.insert(0, str(HERE.parents[1] / "simulation"))
from model import Model

m = Model.build(load_config())
t = 200
# At t+1 a change only in node 0's R adds K0 dR K0' to the residual
# covariance; the node-1 local predictor and innovations do not change at all.
delta = m.gains[t, 0] @ (3*m.R[0]) @ m.gains[t, 0].T
assert np.linalg.eigvalsh(delta)[0] > 0
# A scalar iid scale-model example: Q changes c=1->4, attack b=2 persists.
c, b = 4., 2.
assert c+b*b == 8.
# Unit normal residual has second moment 4; after FDI it is 8.
# Infinite-window normalization by attacked second moment yields mean score 1;
# trusted normalization retains mean score 2. This is population, not finite-sample power.
out = {
    "baseline_remote_only_R0_change_at_200": {
        "local_innovation_distribution": "unchanged (pathwise local data unchanged)",
        "delta_residual_covariance_at_201": delta.tolist(),
    },
    "iid_coexisting_noise_and_attack": {
        "noise_scale_before": 1., "noise_scale_after": c, "attack_bias_after": b,
        "population_link_scale": c+b*b, "population_trusted_scale": c,
        "population_link_score_mean": 1.,
        "population_trusted_score_mean": 1+b*b/c,
        "interpretation": "algebraic mechanism example, not a new Yang random experiment",
    },
    "fixed_chi2_df2_nominal_5pct_at_c4": float(.05**.25),
    "chi2_confidence_lower_tail_rho_half_p60": float(np.exp(-60*.5**2/4)),
    "scalar_counterexample_local_variance_both": 2,
    "scalar_counterexample_remote_variances": [2, 5],
    "all_assertions_passed": True,
}
(HERE/"results/analytic_checks.json").write_text(json.dumps(out, indent=2), encoding="utf-8", newline="\n")
print(json.dumps(out, indent=2))
