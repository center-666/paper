"""Read-only enumeration of historical Replay candidates and one-step trigger tests.

This reads a byte-verified existing Yang clean archive and Task 0.5 CSV/JSON.
It does not import or call the simulator, use truth/measurements, or generate data.
Run from the repository root:
  python -B reviews/g1_task1_1_history_replay_boundary/code/analyze_historical_candidate_sets.py
  python -B reviews/g1_task1_1_history_replay_boundary/code/analyze_historical_candidate_sets.py --verify
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import io
import json
from collections import Counter
from pathlib import Path

import numpy as np

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[1]
TASK05 = ROOT / "reviews/g1_communication_behavior/task0_5"
ARCHIVE = TASK / "evidence/yang__clean.npz"
EXPECTED_ARCHIVE_SHA256 = "82f52b118a9a948c72771b39a636b63180114aef9449d67b03617234237bc16c"
THETA = 0.12
EPSILON = 0.08
A_SCALE = 1.01
ATOL = 2e-12


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def csv_text(rows: list[dict]) -> str:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def json_text(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def hist(values) -> dict[str, int]:
    return {str(key): int(value) for key, value in sorted(Counter(values).items())}


def compute() -> dict[str, str]:
    require(sha(ARCHIVE) == EXPECTED_ARCHIVE_SHA256, "Archived Yang clean NPZ SHA256 mismatch")
    gain_path = TASK / "evidence/nominal_gains.npz"
    require(sha(gain_path) == "7c636e9372461091c149818ab45a87b12920cccaff98669bf04b8388afbc0f33",
            "Archived gains hash mismatch")
    with np.load(gain_path, allow_pickle=False) as saved:
        gains = saved["gains"]
    require(gains.shape == (400, 5, 2, 2), "Archived gain shape")
    singular_values = np.linalg.svd(gains, compute_uv=False)
    require(np.isfinite(gains).all() and singular_values.min() > 0, "Singular gain in finite archive")
    task05_manifest = (TASK05 / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines()
    protected = {}
    for line in task05_manifest:
        expected, relative = line.split("  ", 1)
        path = TASK05 / relative
        protected[relative] = expected
        require(sha(path) == expected, f"Task 0.5 artifact hash mismatch: {relative}")

    seed_rows = {int(row["seed"]): row for row in csv_rows(TASK05 / "03_seed_level_metrics.csv")}
    margin_rows = {
        (int(row["seed"]), int(row["time"]), int(row["node"])): row
        for row in csv_rows(TASK05 / "05_trigger_margin_analysis.csv")
    }
    integrity = json.loads((TASK05 / "01_data_integrity_audit.json").read_text(encoding="utf-8-sig"))
    first_replays = {int(row["seed"]): row for row in integrity["summary"]["first_replay"]["all_rows"]}
    require(set(seed_rows) == set(range(40000, 40032)), "Unexpected historical Seed set")
    require(set(first_replays) == set(seed_rows), "First-Replay rows do not cover the same Seeds")

    with np.load(ARCHIVE, allow_pickle=False) as data:
        estimates = data["estimates"]
        sends = data["sends"]
    require(estimates.shape == (32, 401, 5, 2), "Unexpected estimate array shape")
    require(sends.shape == (32, 400, 5), "Unexpected send array shape")
    require(np.isfinite(estimates).all(), "Non-finite saved estimate")

    candidate_rows: list[dict] = []
    summary_rows: list[dict] = []
    age_norms: dict[str, list[float]] = {"1-10": [], "11-25": [], "26-50": [], "51-100": [], "101+": []}
    ordered_pairs = norm_inversions = 0
    first_step_flips = early_seed_count = suppress_seed_count = actual_flips = 0
    candidate_transition_counts = Counter()

    for index, seed in enumerate(range(40000, 40032)):
        seed_record = seed_rows[seed]
        attack_record = first_replays[seed]
        r = int(seed_record["first_replay_time"])
        source = int(attack_record["source"])
        require(int(attack_record["r"]) == r and source < r, f"Replay time/source mismatch for Seed {seed}")
        require(bool(sends[index, r, 0]), f"First Replay is not on a real sender-0 broadcast: Seed {seed}")
        require(bool(sends[index, source, 0]), f"Historical source was not a real sender-0 broadcast: Seed {seed}")
        require(int(seed_record["first_replay_source"]) == source, f"Archived source metadata mismatch: Seed {seed}")

        # A node broadcast is the same sent estimate on each outgoing edge.
        # All candidates are strict pre-r broadcasts from sender 0 on link 0->1.
        source_ticks = np.flatnonzero(sends[index, :r, 0])
        deltas = estimates[index, source_ticks, 0, :] - estimates[index, r, 0, :]
        ages = r - source_ticks
        norms = np.linalg.norm(deltas, axis=1)
        require(len(source_ticks) > 0 and np.unique(source_ticks).size == len(source_ticks), "Invalid candidate ticks")
        # Duplicate payloads are legal. Preserve packet times even if vector values coincide.

        # Reconstruct the healthy trigger state at the first post-injection decision,
        # using the last genuine node-1 broadcast at or before r.
        k = r + 1
        node1_sends = np.flatnonzero(sends[index, :k, 1])
        require(len(node1_sends) > 0, f"No prior node-1 reference: Seed {seed}")
        last_node1_send = int(node1_sends[-1])
        reference = estimates[index, last_node1_send, 1, :]
        e0 = estimates[index, k, 1, :] - reference
        g0 = float(e0 @ e0 - THETA)
        timeout = (k - last_node1_send) >= 10
        saved_margin = margin_rows[(seed, k, 1)]
        require(np.isclose(g0, float(saved_margin["clean_g"]), atol=ATOL, rtol=0),
                f"Reconstructed healthy margin mismatch: Seed {seed}")
        require(last_node1_send == int(saved_margin["clean_last_send_before"]),
                f"Reconstructed reference time mismatch: Seed {seed}")
        require(timeout == (saved_margin["clean_timeout"] == "True"),
                f"Reconstructed timeout mismatch: Seed {seed}")

        early_count = suppress_count = 0
        for source_tick, age, delta, norm in zip(source_ticks, ages, deltas, norms):
            v = EPSILON * A_SCALE * delta
            delta_g = float(2 * e0 @ v + v @ v)
            ga = g0 + delta_g
            threshold_flip = (g0 > 0) != (ga > 0)
            if g0 <= 0 < ga:
                transition = "early_send"
                early_count += 1
            elif g0 > 0 and ga <= 0:
                transition = "suppressed_send"
                suppress_count += 1
            else:
                transition = "none"
            send_flip = bool(threshold_flip and not timeout)
            candidate_rows.append({
                "seed": seed, "replay_time_r": r, "source_time_s": int(source_tick),
                "age_r_minus_s": int(age), "delta_x": format(float(delta[0]), ".17g"),
                "delta_y": format(float(delta[1]), ".17g"), "delta_norm": format(float(norm), ".17g"),
                "healthy_trigger_margin_g0": format(g0, ".17g"),
                "delta_trigger_margin": format(delta_g, ".17g"),
                "threshold_flag_flip": int(threshold_flip), "timeout_at_decision": int(timeout),
                "send_event_flip_at_r_plus_1": int(send_flip), "transition": transition,
                "is_archived_lag8_source": int(int(source_tick) == source),
            })
            age_bin = "1-10" if age <= 10 else "11-25" if age <= 25 else "26-50" if age <= 50 else "51-100" if age <= 100 else "101+"
            age_norms[age_bin].append(float(norm))

        for older in range(len(ages)):
            for younger in range(len(ages)):
                if ages[older] > ages[younger]:
                    ordered_pairs += 1
                    if norms[older] < norms[younger]:
                        norm_inversions += 1

        actual_delta = deltas[np.flatnonzero(source_ticks == source)[0]]
        actual_v = EPSILON * A_SCALE * actual_delta
        actual_delta_g = float(2 * e0 @ actual_v + actual_v @ actual_v)
        actual_g = g0 + actual_delta_g
        actual_flip = (g0 > 0) != (actual_g > 0)
        actual_class = "early_send" if g0 <= 0 < actual_g else "suppressed_send" if g0 > 0 and actual_g <= 0 else "none"
        require(bool(seed_record["first_step_event_changed"] == "True") == bool(actual_flip and not timeout),
                f"Archived first-step event mismatch: Seed {seed}")
        require(np.allclose(actual_delta, np.asarray(attack_record["delta"], dtype=float), atol=ATOL, rtol=0),
                f"Archived actual Replay delta mismatch: Seed {seed}")

        early_seed_count += early_count > 0
        suppress_seed_count += suppress_count > 0
        first_step_flips += (early_count + suppress_count)
        actual_flips += actual_flip
        candidate_transition_counts["early_send"] += early_count
        candidate_transition_counts["suppressed_send"] += suppress_count
        candidate_transition_counts["none"] += len(source_ticks) - early_count - suppress_count
        summary_rows.append({
            "seed": seed, "r": r, "candidate_broadcast_count": len(source_ticks),
            "distinct_delta_count": len({tuple(delta) for delta in deltas}),
            "candidate_age_min": int(ages.min()), "candidate_age_max": int(ages.max()),
            "delta_norm_min": format(float(norms.min()), ".17g"),
            "delta_norm_median": format(float(np.median(norms)), ".17g"),
            "delta_norm_max": format(float(norms.max()), ".17g"),
            "healthy_g0_at_r_plus_1": format(g0, ".17g"), "timeout_at_r_plus_1": int(timeout),
            "early_send_candidate_count": early_count, "suppressed_send_candidate_count": suppress_count,
            "archived_source_s": source, "archived_replay_age": r - source,
            "archived_delta_norm": format(float(np.linalg.norm(actual_delta)), ".17g"),
            "archived_one_step_transition": actual_class,
        })

    age_bin_rows = []
    for age_bin, values in age_norms.items():
        if values:
            age_bin_rows.append({"age_bin": age_bin, "candidate_count": len(values),
                                 "delta_norm_min": format(min(values), ".17g"),
                                 "delta_norm_median": format(float(np.median(values)), ".17g"),
                                 "delta_norm_max": format(max(values), ".17g")})

    require(len(candidate_rows) == 1543, "Unexpected total number of historical candidate packets")
    require(sum(row["timeout_at_r_plus_1"] for row in summary_rows) == 0,
            "Expected common timeout to be inactive at all 32 first post-Replay decisions")
    result_summary = {
        "status": "PASS", "scope": "saved-data finite candidate enumeration plus exact first-post-injection trigger arithmetic; no simulator or random data",
        "archive_sha256": sha(ARCHIVE), "candidate_count": len(candidate_rows), "seed_count": len(summary_rows),
        "candidate_count_per_seed_min_median_max": [min(int(x["candidate_broadcast_count"]) for x in summary_rows),
                                                       float(np.median([int(x["candidate_broadcast_count"]) for x in summary_rows])),
                                                       max(int(x["candidate_broadcast_count"]) for x in summary_rows)],
        "distinct_delta_count_per_seed_min_median_max": [min(int(x["distinct_delta_count"]) for x in summary_rows),
                                                            float(np.median([int(x["distinct_delta_count"]) for x in summary_rows])),
                                                            max(int(x["distinct_delta_count"]) for x in summary_rows)],
        "candidate_age_min_median_max": [min(int(x["age_r_minus_s"]) for x in candidate_rows),
                                          float(np.median([int(x["age_r_minus_s"]) for x in candidate_rows])),
                                          max(int(x["age_r_minus_s"]) for x in candidate_rows)],
        "candidate_norm_min_median_max": [min(float(x["delta_norm"]) for x in candidate_rows),
                                            float(np.median([float(x["delta_norm"]) for x in candidate_rows])),
                                            max(float(x["delta_norm"]) for x in candidate_rows)],
        "older_younger_candidate_pairs": ordered_pairs,
        "older_norm_smaller_than_younger_pairs": norm_inversions,
        "older_norm_smaller_fraction_descriptive_only": norm_inversions / ordered_pairs,
        "age_bin_summaries": age_bin_rows,
        "candidate_transition_occurrences": dict(candidate_transition_counts),
        "seeds_with_any_early_send_candidate": int(early_seed_count),
        "seeds_with_any_suppressed_send_candidate": int(suppress_seed_count),
        "seeds_with_any_one_step_threshold_crossing_candidate": sum(bool(x["early_send_candidate_count"] or x["suppressed_send_candidate_count"]) for x in summary_rows),
        "archived_lag8_one_step_send_event_flips": int(actual_flips),
        "task05_manifest_entries_verified": len(protected),
        "archived_gain_sha256": sha(gain_path),
        "archived_gain_min_singular_value": float(singular_values.min()),
        "archived_gain_max_singular_value": float(singular_values.max()),
        "gain_nonsingularity_scope": "saved k=0..399, five nodes only; no infinite-horizon theorem",
        "no_trajectory_generation_or_simulator_calls": True,
    }
    return {
        "historical_candidate_vectors.csv": csv_text(candidate_rows),
        "historical_candidate_seed_summary.csv": csv_text(summary_rows),
        "historical_candidate_age_bins.csv": csv_text(age_bin_rows),
        "historical_candidate_summary.json": json_text(result_summary),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    forbidden = {"simulate", "generate_data", "default_rng", "random", "rand", "randn", "standard_normal"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else ""
            require(name not in forbidden, f"Disallowed simulator/RNG call in audit script: {name}")
    outputs = compute()
    target = TASK / "data"
    if args.verify:
        for name, content in outputs.items():
            require((target / name).read_bytes() == content.encode("utf-8"), f"Output mismatch: {name}")
        print("PASS: all historical candidate tables and summary exactly reproduce")
    else:
        target.mkdir(parents=True, exist_ok=True)
        for name, content in outputs.items():
            (target / name).write_bytes(content.encode("utf-8"))
        print(json.dumps({"status": "PASS", "output_files": list(outputs), "candidate_count": 1543, "seed_count": 32}, indent=2))


if __name__ == "__main__":
    main()
