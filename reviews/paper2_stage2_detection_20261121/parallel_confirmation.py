"""Schedule the frozen final cases in parallel; no change to batch or seeds."""
from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import os
from pathlib import Path
import time

# Avoid nested linear-algebra thread pools when multiple cases run concurrently.
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

from run_experiment import HERE, PROTOCOL, Moments, batch, check_frozen, sha, write


def case(job):
    model_id, bi, oi = job
    check_frozen()
    p = json.loads(PROTOCOL.read_text(encoding="utf8"))
    model, b, onset = p["models"][model_id], p["attack_strengths"][bi], p["onsets"][oi]
    path = HERE / "results" / "final" / f"{model['id']}_b{b:g}_onset{onset}.json"
    if path.exists():
        raise RuntimeError("Confirmation output already exists: " + str(path))
    summaries = {h: Moments() for h in p["horizons_after_onset"]}
    count = p["final_episodes_per_case"]
    runtime = []
    started = time.perf_counter()
    for batch_index, start in enumerate(range(0, count, p["batch_size"])):
        n = min(count - start, p["batch_size"])
        # Exactly the seed tuple and frozen batch call in run_experiment.main.
        seed = [p["final_seed"], model_id, bi, oi, batch_index]
        runtime.append(batch(model, b, onset, n, seed, p, summaries))
    result = {
        "stage": "final", "model": model, "strength": b, "onset": onset,
        "n": count, "seconds": time.perf_counter() - started,
        "statistics": {str(h): s.report() for h, s in summaries.items()},
        "runtime_checks": runtime, "frozen_hash": sha(HERE / "freeze.json"),
        "estimates_unchanged_by_detectors": True, "instantaneous_oracle_pre_MSE": 0.,
        "statistical_unit": "independent episode; correlated timesteps are not separate samples",
    }
    write(path, result)
    return path.name, result["seconds"]


def main():
    check_frozen()
    p = json.loads(PROTOCOL.read_text(encoding="utf8"))
    expected_screen = [
        HERE / "results" / "screen" / f"{m['id']}_b{b:g}_onset{k}.json"
        for m in p["models"] for b in p["attack_strengths"] for k in p["onsets"]]
    if not all(path.exists() for path in expected_screen):
        raise SystemExit("Complete all prespecified screen cases before confirmation")
    if (HERE / "parallel_confirmation_manifest.json").exists():
        raise SystemExit("Confirmation scheduler already started")
    jobs = [(mi, bi, oi) for mi in range(2) for bi in range(3) for oi in range(4)]
    write(HERE / "parallel_confirmation_manifest.json", {
        "stage": "RECORDED_BEFORE_FINAL_SAMPLING",
        "script_sha256": sha(Path(__file__)), "frozen_input_sha256": sha(HERE / "freeze.json"),
        "workers": 6, "jobs": jobs,
        "same_batch_function_and_seed_tuples_as_frozen_driver": True,
        "performance_inputs_changed": False,
        "screen_results_used_for_tuning_or_selection": False,
        "reason": "parallel scheduling only, using six of sixteen logical processors",
    })
    with ProcessPoolExecutor(max_workers=6) as executor:
        for future in as_completed([executor.submit(case, j) for j in jobs]):
            name, seconds = future.result()
            print("final", name, "done", round(seconds, 2), "s", flush=True)
    write(HERE / "results" / "final" / "completion.json", {
        "status": "COMPLETE", "cases": len(jobs), "episodes_each": p["final_episodes_per_case"],
        "frozen_input_sha256": sha(HERE / "freeze.json")})


if __name__ == "__main__":
    main()
