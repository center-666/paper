"""Replay the same Stage 6 final traces with cached adjoint projections."""
from __future__ import annotations
from concurrent.futures import ProcessPoolExecutor, as_completed
import json, time
from pathlib import Path

import replay_stage6 as base
from direction_cache import CachedIntervalEnvelope

HERE = Path(__file__).resolve().parent


def run_cached(stage, bi, index, protocol, model):
    # The worker installs the cached implementation before calling the frozen
    # replay logic. This process-local patch leaves the original source intact.
    base.IntervalFixedAmplitudeEnvelope = CachedIntervalEnvelope
    return base.run_episode(stage, bi, index, protocol, model)


def main():
    protocol = base.load_protocol()
    model = json.loads((base.STAGE6 / "model.json").read_text(encoding="utf8"))
    outdir = HERE / "results" / "replay_cached"
    outdir.mkdir(parents=True, exist_ok=True)
    jobs = [("final", bi, i, protocol, model)
            for bi, b in enumerate(protocol["attack_strengths"])
            for i in range(protocol["final_episodes_per_case"])
            if not (outdir / f"b{b:g}_episode{i:03d}.json").exists()]
    started = time.perf_counter()
    with ProcessPoolExecutor(max_workers=int(json.loads(
            (HERE / "stage7_protocol.json").read_text(encoding="utf8"))["workers"])) as pool:
        futures = [pool.submit(run_cached, *job) for job in jobs]
        for future in as_completed(futures):
            row = future.result()
            b, i = row["b"], row["episode"]
            (outdir / f"b{b:g}_episode{i:03d}.json").write_text(
                json.dumps(row, indent=2) + "\n", encoding="utf8", newline="\n")
            print("cached replay", f"b={b:g}", i,
                  "support_seconds", round(row["timing"]["support_search"], 5),
                  "episode_seconds", round(row["replay_seconds"], 2), flush=True)
    rows = [json.loads(p.read_text(encoding="utf8")) for p in sorted(outdir.glob("b*_episode*.json"))]
    failures = [(r["b"], r["episode"]) for r in rows if
                r["coverage_violations"] or r["old_support_violations"] or r["bound_monotonicity_violations"]]
    result = {"status": "PASS_REPRODUCED" if len(rows) == 36 and not failures else "CHECK_FAILURES",
              "episodes": len(rows), "failures": failures,
              "runtime_seconds": time.perf_counter()-started,
              "stage7_freeze_sha256": base.sha(HERE / "stage7_freeze.json"),
              "cache_check_sha256": base.sha(HERE / "direction_cache_checks.json"),
              "certificate_decisions": "same archived Stage 6 successful/failed queries",
              "no_new_random_samples": True}
    (HERE / "results" / "cached_replay_completion.json").write_text(
        json.dumps(result, indent=2)+"\n", encoding="utf8", newline="\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
