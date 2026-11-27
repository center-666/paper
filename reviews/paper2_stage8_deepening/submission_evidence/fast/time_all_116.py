"""Time M3-Fast on every frozen two-tank trajectory without rerunning M3-Exact."""
from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import hashlib
import json
import os
import platform
import statistics
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
STAGE = HERE.parents[1]
CONFIRM = STAGE / "results" / "confirmation"
TRANSITION = STAGE / "supplement" / "results" / "transition"
sys.path.insert(0, str(HERE))
from method import Fast, np as method_numpy


def replay(path):
    row = json.loads(path.read_text(encoding="utf8"))
    # Same eight-frame warm-up convention as the paired prototype benchmark.
    warm = Fast()
    for frame in row["public"][:8]:
        warm.step(frame)

    clock_start = time.perf_counter()
    cpu_start = time.process_time()
    online = Fast()
    outputs = np.empty((len(row["public"]), 4), dtype=np.float64)
    query_times = []
    query_levels = []
    for frame in row["public"]:
        (m2, m3), query, _, _ = online.step(frame)
        outputs[frame[0]] = (*m2[0], *m3[0])
        if query is not None:
            query_times.append(float(query[2]))
            query_levels.append(len(query[1]))
    cpu_seconds = time.process_time() - cpu_start
    wall_seconds = time.perf_counter() - clock_start

    digest = hashlib.sha256(outputs.astype(">f8", copy=False).tobytes()).hexdigest()
    return {
        "id": row["id"],
        "group": row["group"],
        "wall_seconds_per_608_steps": wall_seconds,
        "cpu_seconds_per_608_steps": cpu_seconds,
        "query_seconds": query_times,
        "levels_attempted": query_levels,
        "action_sha256_m2_m3": digest,
    }


def summarize(records):
    wall = [r["wall_seconds_per_608_steps"] for r in records]
    cpu = [r["cpu_seconds_per_608_steps"] for r in records]
    queries = [q for r in records for q in r["query_seconds"]]
    return {
        "trajectory_n": len(records),
        "trajectory_wall_seconds": {
            "mean": statistics.mean(wall),
            "median": statistics.median(wall),
            "p95_linear": float(np.percentile(wall, 95, method="linear")),
            "max": max(wall),
        },
        "trajectory_cpu_seconds": {
            "mean": statistics.mean(cpu),
            "median": statistics.median(cpu),
            "p95_linear": float(np.percentile(cpu, 95, method="linear")),
            "max": max(cpu),
        },
        "query_n": len(queries),
        "query_seconds": {
            "mean": statistics.mean(queries),
            "median": statistics.median(queries),
            "p95_linear": float(np.percentile(queries, 95, method="linear")),
            "max": max(queries),
        },
    }


def main():
    files = sorted(CONFIRM.glob("*.json")) + sorted(TRANSITION.glob("*.json"))
    if len(files) != 116:
        raise RuntimeError(f"Expected the frozen 92+24 two-tank trajectories, found {len(files)}")
    with ProcessPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(replay, files))
    expected = {p.stem for folder in (CONFIRM, TRANSITION) for p in folder.glob("*.json")}
    observed = {r["id"] for r in records}
    if expected != observed or any(len(r["query_seconds"]) != 4 for r in records):
        raise RuntimeError("A trajectory or planned query is missing")
    result = {
        "protocol": "M3-Fast only, all frozen two-tank trajectories",
        "platform": platform.platform(),
        "python": sys.version,
        "numpy": np.__version__,
        "workers": 4,
        "warmup_frames": 8,
        "timed_steps": 608,
        "timing_unit": "one independent public trajectory; four query times within a trajectory are dependent",
        "percentile": "NumPy 2.5.5 percentile method linear",
        "summary_all": summarize(records),
        "summary_by_group": {
            group: summarize([r for r in records if r["group"] == group])
            for group in sorted({r["group"] for r in records})
        },
        "records": records,
    }
    output = HERE / "timing_all_116.json"
    temp = output.with_suffix(".tmp")
    temp.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False)+"\n", encoding="utf8")
    temp.replace(output)
    print(json.dumps({
        "trajectory_summary": result["summary_all"]["trajectory_wall_seconds"],
        "cpu_summary": result["summary_all"]["trajectory_cpu_seconds"],
        "query_summary": result["summary_all"]["query_seconds"],
        "output": str(output),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
