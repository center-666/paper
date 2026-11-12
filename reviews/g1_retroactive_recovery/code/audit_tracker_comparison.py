from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[3]
RUN = Path(__file__).resolve().parents[1] / "results" / "g1r_attack_input_tracker_20261112_02"


def read_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def paired_summary(values):
    x = np.asarray(values, float)
    mean = float(x.mean())
    half = float(stats.t.ppf(.975, len(x)-1)*x.std(ddof=1)/np.sqrt(len(x)))
    return {"n_seed": len(x), "mean": mean, "ci95": [mean-half, mean+half]}


def main():
    rows = read_csv(RUN / "per_seed_comparison.csv")
    index = {(r["scenario"], r["method"], int(r["seed"])): r for r in rows}
    methods = ("causal_input_tracker_full_residual_200_to_216", "post_cache_GLS_209_to_216")
    outputs = []
    for scenario in ("single_step", "replay_packet"):
        ids = sorted(seed for sc, method, seed in index if sc == scenario and method == methods[0])
        for metric in ("receiver_recovery_excess_mse_after", "network_recovery_excess_mse_after"):
            if metric.startswith("network"):
                key0 = index[scenario, methods[0], ids[0]][metric]
                if key0 == "":
                    continue
            a = np.asarray([float(index[scenario, methods[0], seed][metric]) for seed in ids])
            b = np.asarray([float(index[scenario, methods[1], seed][metric]) for seed in ids])
            outputs.append({
                "scenario": scenario,
                "metric": metric,
                "causal_tracker_mean": float(a.mean()),
                "post_cache_gls_mean": float(b.mean()),
                "tracker_minus_gls_paired": paired_summary(a-b),
                "negative_favors_full_window_tracker": True,
                "known_event_edge_and_time": True,
            })
    diag = json.loads((RUN / "diagnostics.json").read_text(encoding="utf-8"))
    normal = read_csv(RUN / "normal_test_audit.csv")
    result = {
        "run_id": RUN.name,
        "paired_comparisons": outputs,
        "normal_false_correction_rates": diag["normal_test_false_correction_rate"],
        "batch_recursive_endpoint_abs_error": diag["max_recursive_batch_endpoint_abs_error"],
        "independent_unit": "seed",
        "claim_scope": "exploratory, oracle event localization, fixed exogenous communication schedule; not a Deghat implementation",
        "normal_seed_count": len({r["seed"] for r in normal}),
        "interpretation": "Recursive whitening plus information/score accumulation is numerically equivalent to batch GLS on the same full residual window. The post-cache GLS is a shorter-window subset of this standard attack-input estimate.",
    }
    (RUN / "tracker_audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
