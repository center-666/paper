"""Compare direct and cached support propagation on identical frozen traces."""
import json, math
from pathlib import Path
import numpy as np
from scipy.stats import gmean

HERE = Path(__file__).resolve().parent


def main():
    direct_dir = HERE / "results" / "replay"
    cache_dir = HERE / "results" / "replay_cached_corrected"
    metrics = ("monitor", "old_cert", "new_directional", "old_gain",
               "new_directional_gain", "old_conditional_gain",
               "new_directional_conditional_gain", "old_action_square",
               "new_action_square", "old_current_action_norm",
               "new_current_action_norm", "old_current_bound", "new_current_bound")
    differences = {m: 0.0 for m in metrics}
    differing = {m: 0 for m in metrics}
    rows = []
    for p in sorted(direct_dir.glob("b*_episode*.json")):
        q = cache_dir / p.name
        d = json.loads(p.read_text(encoding="utf8"))
        c = json.loads(q.read_text(encoding="utf8"))
        if d["b"] != c["b"] or d["episode"] != c["episode"]:
            raise AssertionError("Episode identity mismatch")
        for H in d["snapshots"]:
            for m in metrics:
                delta = abs(d["snapshots"][H][m] - c["snapshots"][H][m])
                differences[m] = max(differences[m], delta)
                differing[m] += int(delta > 1e-12)
        if (c["coverage_violations"] or c["old_support_violations"] or
                c["bound_monotonicity_violations"]):
            raise AssertionError((p.name, "safety/reproduction counter nonzero"))
        rows.append({"b": c["b"], "episode": c["episode"],
                     "direct_seconds": d["replay_seconds"],
                     "cached_seconds": c["replay_seconds"],
                     "direct_support_seconds": d["timing"]["support_search"],
                     "cached_support_seconds": c["timing"]["support_search"]})
    by_b = {}
    for b in (0.0, 0.1, 0.25):
        subset = [r for r in rows if r["b"] == b]
        ds = np.asarray([r["direct_support_seconds"] for r in subset])
        cs = np.asarray([r["cached_support_seconds"] for r in subset])
        dt = np.asarray([r["direct_seconds"] for r in subset])
        ct = np.asarray([r["cached_seconds"] for r in subset])
        by_b[str(b)] = {
            "n": len(subset),
            "direct_support_mean_seconds": float(ds.mean()),
            "cached_support_mean_seconds": float(cs.mean()),
            "support_speedup_geomean": float(gmean(np.maximum(ds, 1e-12)/np.maximum(cs, 1e-12))),
            "direct_episode_mean_seconds": float(dt.mean()),
            "cached_episode_mean_seconds": float(ct.mean()),
        }
    result = {"status": "PASS" if len(rows) == 36 else "INCOMPLETE",
              "episodes": len(rows), "max_absolute_output_difference": differences,
              "metric_differences_over_1e-12": differing,
              "runtime_by_attack_strength": by_b,
              "interpretation": "Same trace/evidence outputs; cached q lower bounds are outward and may differ from direct interval multiplication only within numerical enclosure.",
              "claims_boundary": "No new random samples; no independent performance confirmation."}
    (HERE / "analysis" / "cache_equivalence.json").write_text(
        json.dumps(result, indent=2)+"\n", encoding="utf8", newline="\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
