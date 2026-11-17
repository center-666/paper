"""Task 0.5: deterministic read-only analysis of TWO archived NPZ files.

Run from any directory with the existing research Python:
    python -B .../task0_5/code/analyze_closed_loop_events.py
    python -B .../task0_5/code/analyze_closed_loop_events.py --verify

The default writes only the named derived deliverables in task0_5. --verify
recomputes the text/CSV/JSON in memory, compares exact bytes, and checks the
delivery SHA manifest (including figures). No simulator, model builder, random
generator, original runner or other NPZ is imported, called or read.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parents[1]
ROOT = OUT.parents[2]
MAIN = ROOT.parent / "mypaper"
HIST = MAIN / "simulation/runs/2026-11-10_five_node_v2"
TASK0 = OUT.parent / "task0"
NAMES = {"clean": "yang__clean.npz", "replay": "yang__replay_packet.npz"}
CLASSES = ["Initial", "Threshold-only", "Timeout-only", "Both", "No-send", "Mismatch"]
ATOL, RTOL = 1e-12, 1e-10
# Diagnostic resolution, NOT a change to the literal historical trigger > theta.
MARGIN_RESOLUTION = 1e-12
OUTPUTS = ["00_task0_5_final_report.md", "01_data_integrity_audit.json",
           "02_seed_pairing_audit.md", "03_seed_level_metrics.csv",
           "04_event_reconstruction.csv", "05_trigger_margin_analysis.csv",
           "06_first_replay_consistency.md"]
FIGURES = ["01_node1_event_comparison.png", "02_node1_trigger_margin.png",
           "03_first_divergence_distribution.png", "04_seed_send_count_difference.png",
           "05_network_event_summary.png"]


class Hold(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise Hold(message)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def native(x):
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, np.generic):
        return x.item()
    raise TypeError(type(x).__name__)


def json_text(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2, default=native, allow_nan=False) + "\n"


def csv_text(rows):
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def git_state(root):
    def get(*args):
        return subprocess.check_output(["git", "-C", str(root), *args],
                                       stderr=subprocess.DEVNULL)
    return {"head": get("rev-parse", "HEAD").decode().strip(),
            "branch": get("branch", "--show-current").decode().strip(),
            "tracked_diff_sha256": hashlib.sha256(get("diff", "--binary")).hexdigest(),
            "staged_diff_sha256": hashlib.sha256(get("diff", "--cached", "--binary")).hexdigest()}


def source_line(rel, needle):
    lines = (HIST / rel).read_text(encoding="utf-8-sig").splitlines()
    return [i for i, s in enumerate(lines, 1) if needle in s]


def describe(a):
    return {"shape": list(a.shape), "dtype": str(a.dtype), "size": int(a.size),
            "min": a.min().item(), "max": a.max().item(),
            "nan_count": int(np.isnan(a).sum()),
            "inf_count": int(np.isinf(a).sum()),
            "finite": bool(np.isfinite(a).all())}


def stats(values):
    x = np.asarray([v for v in values if v is not None], dtype=float)
    if not len(x):
        return {"n": 0}
    return {"n": len(x), "min": float(x.min()), "q1": float(np.quantile(x, .25)),
            "median": float(np.median(x)), "q3": float(np.quantile(x, .75)),
            "max": float(x.max()), "mean": float(x.mean())}


def rate(k, n):
    z = 1.959963984540054  # fixed normal 0.975 quantile, no random resampling
    if not n:
        return {"k": k, "n": n, "proportion": None, "wilson95": None}
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return {"k": int(k), "n": int(n), "proportion": p,
            "wilson95": [max(0., c - h), min(1., c + h)]}


def first(mask):
    a = np.flatnonzero(mask)
    return int(a[0]) if len(a) else None


def histogram(values):
    return {str(k): int(v) for k, v in sorted(Counter(v for v in values if v is not None).items())}


def reconstruct(data, cfg):
    h, stored = data["estimates"], data["sends"]
    S, T, N = stored.shape
    n = h.shape[-1]
    limit, theta = cfg["max_interval"], cfg["send_delta_squared"]
    ref = np.zeros((S, N, n))
    last = np.full((S, N), -limit, dtype=int)
    result = {
        "reference_before": np.zeros((S, T, N, n)),
        "last_send_before": np.zeros((S, T, N), dtype=int),
        "distance_squared": np.zeros((S, T, N)),
        "margin": np.zeros((S, T, N)),
        "threshold": np.zeros((S, T, N), dtype=bool),
        "timeout": np.zeros((S, T, N), dtype=bool),
        "send": np.zeros((S, T, N), dtype=bool),
        "category": np.zeros((S, T, N), dtype=np.int8)}
    for t in range(T):
        result["reference_before"][:, t] = ref
        result["last_send_before"][:, t] = last
        dist = np.sum((h[:, t] - ref) ** 2, axis=-1)
        threshold = dist > theta
        timeout = t - last >= limit
        send = threshold | timeout
        category = np.where(threshold & timeout, 3,
                            np.where(threshold, 1, np.where(timeout, 2, 4)))
        if t == 0:
            send[:] = True
            category[:] = 0
        for key, value in [("distance_squared", dist), ("margin", dist - theta),
                           ("threshold", threshold), ("timeout", timeout),
                           ("send", send), ("category", category)]:
            result[key][:, t] = value
        # Never force the saved sends into the recursion to conceal a mismatch.
        ref = np.where(send[..., None], h[:, t], ref)
        last = np.where(send, t, last)
    result["mismatch"] = result["send"] != stored
    result["category"][result["mismatch"]] = 5
    return result


def audit_inputs(audit):
    manifest = read_json(TASK0 / "02_parameter_manifest.json")
    cfg = read_json(HIST / "config.json")
    env = read_json(HIST / "environment.json")
    task0_hashes = {Path(v["main_original"]).name: v["main_sha256"]
                    for v in manifest["historical_asset_availability"]}
    for name, expected in manifest["delivery_markdown_sha256"].items():
        require(digest(TASK0 / name) == expected, "Task0 Markdown hash mismatch: " + name)
    source_hashes = {}
    for name in ["engine.py", "model.py", "run_study.py"]:
        p = HIST / "sources" / name
        actual = digest(p)
        source_hashes[name] = {"actual": actual, "environment_recorded": env["source_sha256"][name],
                               "matches": actual == env["source_sha256"][name]}
        require(source_hashes[name]["matches"], "Historical source hash mismatch: " + name)
    profile = next(p for p in manifest["model_profiles"] if p["profile_id"] == "early_five_node_v2")
    task0_copy = ROOT / profile["source"]["path"]
    # Task0 hashed the LF Git checkout, whereas the original run config uses
    # CRLF. Verify both original bytes and exact line-ending-only equivalence;
    # never silently accept a semantic or parameter difference.
    require(digest(task0_copy) == profile["source"]["sha256"], "Task0 config copy changed")
    original_bytes = (HIST / "config.json").read_bytes()
    copy_bytes = task0_copy.read_bytes()
    require(original_bytes.replace(b"\r\n", b"\n") == copy_bytes.replace(b"\r\n", b"\n")
            and cfg == read_json(task0_copy), "Historical config differs beyond line endings")
    audit["config_Task0_comparison"] = {
        "Task0_copy": str(task0_copy), "Task0_copy_sha256": digest(task0_copy),
        "original_config_sha256": digest(HIST / "config.json"),
        "raw_bytes_equal": original_bytes == copy_bytes,
        "line_endings_only_equal": True, "JSON_parameters_equal": True,
        "initial_implementation_pause": "Initial script compared the original CRLF config directly against Task0's LF-copy hash and wrote HOLD. Inspection proved exactly 155 CRLF-vs-LF differences and no other change. This source-check correction is recorded here; no input was modified."}
    require(read_json(HIST / "completion.json")["completed"], "Historical run incomplete")
    audit["historical_source_hash_verification"] = source_hashes
    audit["config"] = cfg
    audit["source_locations"] = {
        "shared_testseed_and_noise_generation": {"file": "sources/run_study.py", "lines": [131, 132, 144, 149, 152, 153]},
        "closed_loop_schedule_none": {"file": "sources/run_study.py", "lines": source_line("sources/run_study.py", "schedule=testref.sends")},
        "ordered_seed_range": {"file": "sources/model.py", "lines": [81, 82, 83]},
        "independent_rng_per_seed": {"file": "sources/model.py", "lines": [93, 94, 95, 96, 97]},
        "trigger_and_reference": {"file": "sources/engine.py", "lines": list(range(59, 75))},
        "replay_source": {"file": "sources/engine.py", "lines": list(range(76, 93))},
        "cache_update_and_yang": {"file": "sources/engine.py", "lines": list(range(108, 128))}}
    S, T, N, n = cfg["test_seeds"]["count"], cfg["T"], cfg["N"], cfg["n"]
    E = len(cfg["edges_sender_receiver"])
    expected_shapes = {"estimates": (S, T+1, N, n), "sends": (S, T, N),
                       "weights": (S, T, E), "cache_bad": (S, T, E),
                       "injected": (S, T), "replay_source": (S, T), "clipped": (S, T, E)}
    expected_dtypes = {"estimates": "float64", "sends": "bool", "weights": "float32",
                       "cache_bad": "bool", "injected": "bool", "replay_source": "int64",
                       "clipped": "bool"}
    data = {}
    audit["npz"] = {}
    for arm, name in NAMES.items():
        p = HIST / "closed_loop" / name
        actual = digest(p)
        audit["npz"][arm] = {"path": str(p), "sha256": actual,
                            "Task0_sha256": task0_hashes[name],
                            "Task0_match": actual == task0_hashes[name]}
        require(actual == task0_hashes[name], "STOP: input NPZ differs from Task0: " + name)
        # Only the two named NPZ files are read anywhere in this script.
        with np.load(p, allow_pickle=False) as z:
            data[arm] = {k: z[k].copy() for k in z.files}
        audit["npz"][arm]["field_order"] = list(data[arm])
        audit["npz"][arm]["arrays"] = {k: describe(v) for k, v in data[arm].items()}
        require(set(data[arm]) == set(expected_shapes), "Unexpected/missing NPZ fields")
        for k, v in data[arm].items():
            require(v.shape == expected_shapes[k] and str(v.dtype) == expected_dtypes[k],
                    f"Unexpected shape/dtype: {arm}/{k}")
            require(np.isfinite(v).all(), f"Nonfinite data: {arm}/{k}")
        require(np.all(data[arm]["weights"] == 1) and not data[arm]["clipped"].any(),
                "Yang arm contains gating/clipping")
        require(np.all(data[arm]["estimates"][:, 0] == 0), "Nonzero initial estimates")
    require(not data["clean"]["injected"].any()
            and np.all(data["clean"]["replay_source"] == -1)
            and not data["clean"]["cache_bad"].any(), "Clean arm contains attack metadata")
    # per_seed_metrics.csv is read ONLY as metadata, not as another trajectory.
    with (HIST / "per_seed_metrics.csv").open(encoding="utf-8-sig", newline="") as f:
        metadata = list(csv.DictReader(f))
    seeds = list(range(cfg["test_seeds"]["start"], cfg["test_seeds"]["start"] + S))
    pair_checks = {}
    src = np.asarray(cfg["edges_sender_receiver"])[:, 0]
    for arm, scenario in [("clean", "clean"), ("replay", "replay_packet")]:
        rows = [r for r in metadata if r["protocol"] == "closed_loop"
                and r["method"] == "yang" and r["scenario"] == scenario]
        require([int(r["seed"]) for r in rows] == seeds, "Seed order/provenance mismatch")
        z = data[arm]
        for s, row in enumerate(rows):
            values = {"node_broadcasts": int(z["sends"][s].sum()),
                      "edge_messages": int(z["sends"][s, :, src].sum()),
                      "injected_packets": int(z["injected"][s].sum()), "clip_fraction": 0}
            for field, val in values.items():
                require(float(row[field]) == val, f"NPZ row differs from Seed metadata: {arm}/{s}/{field}")
        pair_checks[arm] = {"ordered_seeds": [int(r["seed"]) for r in rows],
                             "rows": len(rows), "row_count_and_traffic_metadata_match": True}
    audit["pairing"] = {
        "status": "VERIFIED_BY_ARCHIVED_PROVENANCE_AND_EXACT_PREFIX",
        "metadata": pair_checks, "same_x_y_object_in_archived_runner": True,
        "independent_raw_noise_reverification": False,
        "limitation": "NPZ has no embedded Seed/x/y; ordered Seed IDs follow hash-verified runner + config + per-Seed CSV. test_inputs.npz is NOT read; no raw noise regenerated.",
        "closed_loop_verified": True}
    injection_checks = []
    a, c = data["replay"], data["clean"]
    sender, receiver = cfg["attack"]["sender"], cfg["attack"]["receiver"]
    edge = cfg["edges_sender_receiver"].index([sender, receiver])
    start, end, lag = (cfg["attack"][k] for k in ("start", "end_inclusive", "replay_packet_lag"))
    for s, seed in enumerate(seeds):
        for t in range(T):
            history = np.flatnonzero(a["sends"][s, :t, sender])
            expected = start <= t <= end and a["sends"][s, t, sender] and len(history) >= lag
            require(bool(a["injected"][s, t]) == bool(expected),
                    f"Replay opportunity/mask mismatch at {seed}/{t}")
            source = int(a["replay_source"][s, t])
            if expected:
                require(source == int(history[-lag]) and 0 <= source < t
                        and a["sends"][s, source, sender], "Illegal historical Replay source")
                injection_checks.append({"seed": seed, "replay_time": t, "source_time": source,
                                         "actual_age": t-source})
            else:
                require(source == -1, "Source stored without injection")
    bad = np.zeros((S, E), dtype=bool)
    for t in range(T):
        fresh = a["sends"][:, t, src]
        current = np.zeros((S, E), dtype=bool)
        current[:, edge] = a["injected"][:, t]
        bad = np.where(fresh, current, bad)
        require(np.array_equal(bad, a["cache_bad"][:, t]), "cache_bad semantics mismatch")
    prefixes = []
    for s, seed in enumerate(seeds):
        r = first(a["injected"][s])
        k = r if r is not None else T-1
        states_equal = np.array_equal(a["estimates"][s, :k+1], c["estimates"][s, :k+1])
        sends_equal = np.array_equal(a["sends"][s, :k+1], c["sends"][s, :k+1])
        prefixes.append({"seed": seed, "first_replay": r,
                         "estimates_equal_through_r": states_equal, "sends_equal_through_r": sends_equal,
                         "max_abs_state_difference_through_r": float(np.max(np.abs(a["estimates"][s, :k+1] - c["estimates"][s, :k+1])))})
        require(states_equal and sends_equal, f"Pre-attack difference at Seed {seed}")
    audit["pairing"]["per_seed_prefix_checks"] = prefixes
    audit["replay_source_validation"] = {"count": len(injection_checks), "invalid": 0,
                                        "checks": injection_checks, "cache_bad_mismatch": 0}
    rec = {arm: reconstruct(z, cfg) for arm, z in data.items()}
    audit["trigger_reconstruction"] = {}
    for arm, r in rec.items():
        errors = np.argwhere(r["mismatch"])
        audit["trigger_reconstruction"][arm] = {
            "comparisons": S*T*N, "mismatches": len(errors),
            "first_mismatch_coordinates": errors[:20].tolist(),
            "category_counts": {CLASSES[i]: int((r["category"] == i).sum()) for i in range(6)},
            "threshold_literal": "distance_squared > config.send_delta_squared",
            "reference_updates_from": "reconstructed sends, NOT saved sends"}
        require(not len(errors), "STOP: reconstructed sends do not match saved events")
    return cfg, seeds, data, rec


def classify(cross0, cross1, time0, time1, d):
    dc, dt = cross0 != cross1, time0 != time1
    if not d:
        return "No-event-difference"
    if dc and dt:
        return "Both-flags-changed"
    if dc:
        return "Threshold-flag-only"
    if dt:
        return "Timeout-flag-only"
    raise Hold("Event differs without Boolean condition difference")


def compute(cfg, seeds, data, rec):
    c, a = data["clean"], data["replay"]
    cR, aR = rec["clean"], rec["replay"]
    S, T, N = c["sends"].shape
    sender, receiver = cfg["attack"]["sender"], cfg["attack"]["receiver"]
    require((sender, receiver) == (0, 1), "This audit targets historical 0->1")
    D = a["sends"].astype(np.int8) - c["sends"].astype(np.int8)
    g0, ga = cR["margin"][:, :, 1], aR["margin"][:, :, 1]
    dg = ga - g0
    scale_tol = MARGIN_RESOLUTION * (1 + np.maximum(np.abs(g0), np.abs(ga)))
    changed = np.abs(dg) > scale_tol
    closer = np.abs(ga) < np.abs(g0) - scale_tol
    dh = a["estimates"][:, :T, 1] - c["estimates"][:, :T, 1]
    dm = aR["reference_before"][:, :, 1] - cR["reference_before"][:, :, 1]
    shift = dh - dm
    base = c["estimates"][:, :T, 1] - cR["reference_before"][:, :, 1]
    algebra = 2*np.sum(base*shift, axis=-1) + np.sum(shift*shift, axis=-1)
    seed_rows, event_rows, margin_rows, consistency = [], [], [], []
    cause_counts = Counter()
    cause_seed = {key: set() for key in ["Threshold-flag-only", "Timeout-flag-only", "Both-flags-changed"]}
    first_causes = Counter()
    for s, seed in enumerate(seeds):
        inj = np.flatnonzero(a["injected"][s])
        r = int(inj[0]) if len(inj) else None
        second = int(inj[1]) if len(inj) > 1 else None
        k = first(D[s, :, 1] != 0)
        require(k is None or (r is not None and k > r), "Noncausal first node 1 divergence")
        for node in range(N):
            nk = first(D[s, :, node] != 0)
            require(nk is None or (r is not None and nk > r), "Noncausal network divergence")
        row = {"seed": seed, "array_row": s, "valid_injection": r is not None,
               "replay_injection_count": len(inj), "first_replay_time": r,
               "second_replay_time": second, "last_replay_time": int(inj[-1]) if len(inj) else None,
               "first_node1_divergence_time": k,
               "first_node1_divergence_delay": None if k is None else k-r,
               "first_node1_event_before_second_replay_update": k is not None and (second is None or k <= second),
               "node1_divergence_censored": k is None,
               "observation_last_send_tick": T-1,
               "node1_added_sends": int((D[s, :, 1] == 1).sum()),
               "node1_missing_sends": int((D[s, :, 1] == -1).sum()),
               "node1_different_event_ticks": int((D[s, :, 1] != 0).sum())}
        for arm, z in data.items():
            times = np.flatnonzero(z["sends"][s, :, 1])
            gaps = np.diff(times)
            row[f"node1_{arm}_send_count"] = len(times)
            row[f"node1_{arm}_complete_gap_count"] = len(gaps)
            row[f"node1_{arm}_mean_interval"] = float(gaps.mean()) if len(gaps) else None
            row[f"node1_{arm}_median_interval"] = float(np.median(gaps)) if len(gaps) else None
            row[f"node1_{arm}_q1_interval"] = float(np.quantile(gaps, .25)) if len(gaps) else None
            row[f"node1_{arm}_q3_interval"] = float(np.quantile(gaps, .75)) if len(gaps) else None
            row[f"node1_{arm}_terminal_silence_censored_length"] = T-1-int(times[-1])
            for ci, label in enumerate(CLASSES):
                row[f"node1_{arm}_{label}_count"] = int((rec[arm]["category"][s, :, 1] == ci).sum())
        row["node1_send_count_difference"] = row["node1_replay_send_count"] - row["node1_clean_send_count"]
        row["node1_mean_interval_difference"] = row["node1_replay_mean_interval"] - row["node1_clean_mean_interval"]
        row["node1_median_interval_difference"] = row["node1_replay_median_interval"] - row["node1_clean_median_interval"]
        row["node1_margin_changed_ticks"] = int(changed[s].sum())
        row["node1_margin_changed_same_event_ticks"] = int((changed[s] & (D[s, :, 1] == 0)).sum())
        row["node1_margin_positive_change_ticks"] = int((dg[s] > scale_tol[s]).sum())
        row["node1_margin_negative_change_ticks"] = int((dg[s] < -scale_tol[s]).sum())
        row["node1_closer_to_threshold_ticks"] = int(closer[s].sum())
        row["node1_mean_delta_g"] = float(dg[s].mean())
        row["node1_max_abs_delta_g"] = float(np.max(np.abs(dg[s])))
        stop = k if k is not None else T
        row["node1_changed_margin_before_first_event_ticks"] = int(changed[s, :stop].sum())
        row["first_event_direction"] = None if k is None else ("Replay-earlier" if D[s, k, 1] == 1 else "Replay-later")
        for arm, z in data.items():
            next_tick = None if k is None else first(z["sends"][s, k:, 1])
            row[f"node1_{arm}_next_send_from_first_divergence"] = None if next_tick is None else k+next_tick
        ct = row["node1_clean_next_send_from_first_divergence"]
        at = row["node1_replay_next_send_from_first_divergence"]
        row["next_send_shift_from_common_history"] = None if ct is None or at is None else at-ct
        row["next_send_pair_censored"] = k is not None and (ct is None or at is None)
        network_count = 0
        for node in range(N):
            nk = first(D[s, :, node] != 0)
            row[f"node{node}_first_divergence"] = nk
            row[f"node{node}_count_difference"] = int(D[s, :, node].sum())
            row[f"node{node}_different_ticks"] = int((D[s, :, node] != 0).sum())
            network_count += nk is not None
        row["network_divergence_nodes"] = network_count
        row["first_node1_cause"] = None
        for t in range(T):
            for node in range(N):
                cth, ath = bool(cR["threshold"][s, t, node]), bool(aR["threshold"][s, t, node])
                cto, ato = bool(cR["timeout"][s, t, node]), bool(aR["timeout"][s, t, node])
                d = int(D[s, t, node])
                cause = classify(cth, ath, cto, ato, d)
                if node == 1 and d:
                    cause_counts[cause] += 1
                    cause_seed[cause].add(seed)
                    if t == k:
                        first_causes[cause] += 1
                        row["first_node1_cause"] = cause
                        require(cto == ato and cth != ath, "First own event divergence must have common timeout state")
                event_rows.append({
                    "seed": seed, "time": t, "node": node,
                    "clean_send": int(c["sends"][s, t, node]), "replay_send": int(a["sends"][s, t, node]),
                    "event_difference": d, "clean_reconstructed": int(cR["send"][s, t, node]),
                    "replay_reconstructed": int(aR["send"][s, t, node]),
                    "clean_mismatch": bool(cR["mismatch"][s, t, node]), "replay_mismatch": bool(aR["mismatch"][s, t, node]),
                    "clean_category": CLASSES[cR["category"][s, t, node]],
                    "replay_category": CLASSES[aR["category"][s, t, node]],
                    "clean_threshold": cth, "replay_threshold": ath, "clean_timeout": cto, "replay_timeout": ato,
                    "threshold_flag_changed": cth != ath, "timeout_flag_changed": cto != ato,
                    "clean_last_send_before": int(cR["last_send_before"][s, t, node]),
                    "replay_last_send_before": int(aR["last_send_before"][s, t, node]),
                    "clean_distance_squared": float(cR["distance_squared"][s, t, node]),
                    "replay_distance_squared": float(aR["distance_squared"][s, t, node]),
                    "difference_cause_flags": cause,
                    "threshold_change_alone_changes_OR": (ath or cto) != (cth or cto),
                    "timeout_change_alone_changes_OR": (cth or ato) != (cth or cto),
                    "before_or_at_first_replay": r is None or t <= r})
            mr = {"seed": seed, "time": t, "node": 1, "first_replay_time": r,
                  "clean_g": float(g0[s, t]), "replay_g": float(ga[s, t]), "delta_g": float(dg[s, t]),
                  "diagnostic_resolution": float(scale_tol[s, t]), "margin_changed": bool(changed[s, t]),
                  "closer_to_boundary": bool(closer[s, t]), "event_difference": int(D[s, t, 1]),
                  "changed_margin_same_send": bool(changed[s, t] and not D[s, t, 1]),
                  "before_first_event_divergence": k is None or t < k,
                  "clean_last_send_before": int(cR["last_send_before"][s, t, 1]),
                  "replay_last_send_before": int(aR["last_send_before"][s, t, 1]),
                  "clean_threshold": bool(cR["threshold"][s, t, 1]), "replay_threshold": bool(aR["threshold"][s, t, 1]),
                  "clean_timeout": bool(cR["timeout"][s, t, 1]), "replay_timeout": bool(aR["timeout"][s, t, 1]),
                  "state_pollution_norm": float(np.linalg.norm(dh[s, t])),
                  "sender_reference_difference_norm": float(np.linalg.norm(dm[s, t])),
                  "trigger_vector_difference_norm": float(np.linalg.norm(shift[s, t])),
                  "algebraic_margin_difference_from_saved_states": float(algebra[s, t]),
                  "algebraic_identity_abs_error": float(abs(algebra[s, t] - dg[s, t]))}
            for j in range(2):
                mr[f"clean_reference_{j}"] = float(cR["reference_before"][s, t, 1, j])
                mr[f"replay_reference_{j}"] = float(aR["reference_before"][s, t, 1, j])
                mr[f"clean_hat_{j}"] = float(c["estimates"][s, t, 1, j])
                mr[f"replay_hat_{j}"] = float(a["estimates"][s, t, 1, j])
            margin_rows.append(mr)
        if r is not None and r+1 < T:
            old = int(a["replay_source"][s, r])
            delta = a["estimates"][s, old, sender] - a["estimates"][s, r, sender]
            predicted = float(cfg["epsilon"]) * np.asarray(cfg["A"]) @ delta
            observed = a["estimates"][s, r+1, 1] - c["estimates"][s, r+1, 1]
            ref = cR["reference_before"][s, r+1, 1]
            require(np.array_equal(ref, aR["reference_before"][s, r+1, 1]),
                    "First margin comparison uses unequal prior references")
            e0 = c["estimates"][s, r+1, 1] - ref
            dg_predict = float(2*e0@predicted + predicted@predicted)
            dg_observed = float(dg[s, r+1])
            state_error = float(np.max(np.abs(observed-predicted)))
            margin_error = abs(dg_observed-dg_predict)
            other = [j for j in range(N) if j != 1]
            other_error = float(np.max(np.abs(a["estimates"][s, r+1, other]-c["estimates"][s, r+1, other])))
            passed = bool(np.allclose(observed, predicted, atol=ATOL, rtol=RTOL)
                          and np.isclose(dg_observed, dg_predict, atol=ATOL, rtol=RTOL))
            consistency.append({"seed": seed, "r": r, "source": old, "actual_age": r-old,
                                "delta": delta.tolist(), "m_after_r": ref.tolist(),
                                "e0_trigger_difference": e0.tolist(), "state_prediction": predicted.tolist(),
                                "state_observed": observed.tolist(), "state_abs_error": state_error,
                                "margin_prediction": dg_predict, "margin_observed": dg_observed,
                                "margin_abs_error": margin_error, "other_nodes_state_abs_error": other_error,
                                "first_step_event_difference": int(D[s, r+1, 1]), "passed": passed})
            row.update({"first_replay_source": old, "first_replay_actual_age": r-old,
                        "first_replay_delta_norm": float(np.linalg.norm(delta)),
                        "first_state_pollution_norm": float(np.linalg.norm(observed)),
                        "first_step_delta_g": dg_observed,
                        "first_step_margin_changed": bool(changed[s, r+1]),
                        "first_step_closer_to_boundary": bool(closer[s, r+1]),
                        "first_step_event_changed": bool(D[s, r+1, 1]),
                        "first_step_changed_margin_same_send": bool(changed[s, r+1] and not D[s, r+1, 1]),
                        "first_state_formula_abs_error": state_error, "first_margin_formula_abs_error": margin_error,
                        "first_replay_formula_pass": passed})
        seed_rows.append(row)
    valid = [r for r in seed_rows if r["valid_injection"]]
    v = len(valid)
    summary = {
        "statistical_unit": "Seed; time counts descriptive only; complete gaps summarized within each Seed first",
        "all_seeds": S, "valid_injected": rate(v, S),
        "node1_any_divergence": rate(sum(r["first_node1_divergence_time"] is not None for r in valid), v),
        "first_step_event_divergence": rate(sum(r["first_step_event_changed"] for r in valid), v),
        "first_step_margin_changed_same_event": rate(sum(r["first_step_changed_margin_same_send"] for r in valid), v),
        "first_divergence_before_second_replay_update": rate(sum(r["first_node1_event_before_second_replay_update"] for r in valid), v),
        "send_count_increased": rate(sum(r["node1_send_count_difference"] > 0 for r in valid), v),
        "send_count_decreased": rate(sum(r["node1_send_count_difference"] < 0 for r in valid), v),
        "send_count_unchanged": rate(sum(r["node1_send_count_difference"] == 0 for r in valid), v),
        "first_margin_positive": rate(sum(r["first_step_delta_g"] > MARGIN_RESOLUTION for r in valid), v),
        "first_margin_negative": rate(sum(r["first_step_delta_g"] < -MARGIN_RESOLUTION for r in valid), v),
        "first_margin_closer_boundary": rate(sum(r["first_step_closer_to_boundary"] for r in valid), v),
        "changed_margin_before_first_event": rate(sum(r["node1_changed_margin_before_first_event_ticks"] > 0 for r in valid), v),
        "earlier_from_last_common_send": rate(sum(r["first_event_direction"] == "Replay-earlier" for r in valid), v),
        "later_from_last_common_send": rate(sum(r["first_event_direction"] == "Replay-later" for r in valid), v),
        "node1_first_causes": dict(first_causes),
        "node1_all_cause_tick_counts": dict(cause_counts),
        "node1_cause_seed_incidence": {k: rate(len(x), v) for k, x in cause_seed.items()},
        "delay_histogram": histogram(r["first_node1_divergence_delay"] for r in valid),
        "count_difference_histogram": histogram(r["node1_send_count_difference"] for r in valid),
        "per_seed_summary": {key: stats(r.get(key) for r in valid) for key in [
            "first_replay_time", "first_replay_actual_age", "replay_injection_count",
            "first_node1_divergence_time", "first_node1_divergence_delay", "node1_send_count_difference",
            "node1_clean_mean_interval", "node1_replay_mean_interval", "node1_mean_interval_difference",
            "node1_median_interval_difference", "next_send_shift_from_common_history",
            "network_divergence_nodes", "first_step_delta_g", "node1_mean_delta_g", "node1_max_abs_delta_g"]},
        "node1_category_counts": {arm: {CLASSES[ci]: {
            "tick_count": int((rec[arm]["category"][:, :, 1] == ci).sum()),
            "seeds_with_category": rate(int(np.any(rec[arm]["category"][:, :, 1] == ci, axis=1).sum()), S),
            "per_seed_count": stats(np.sum(rec[arm]["category"][:, :, 1] == ci, axis=1))}
            for ci in range(6)} for arm in NAMES},
        "network": [{"node": node, "seeds_with_divergence": rate(int(np.any(D[:, :, node] != 0, axis=1).sum()), S),
                     "different_ticks": int((D[:, :, node] != 0).sum()),
                     "added_ticks": int((D[:, :, node] == 1).sum()),
                     "missing_ticks": int((D[:, :, node] == -1).sum()),
                     "per_seed_count_difference": stats(D[:, :, node].sum(axis=1))} for node in range(N)],
        "first_replay": {"atol": ATOL, "rtol": RTOL,
                         "max_state_abs_error": max(x["state_abs_error"] for x in consistency),
                         "max_margin_abs_error": max(x["margin_abs_error"] for x in consistency),
                         "max_other_nodes_error_at_rplus1": max(x["other_nodes_state_abs_error"] for x in consistency),
                         "failures": [x for x in consistency if not x["passed"]], "all_rows": consistency},
        "margin_resolution_rule": "1e-12 * (1+max(abs(g_clean),abs(g_replay))); diagnostic only, trigger remains strict >theta",
        "wilson_scope": "Descriptive Seed-level intervals conditional on this fixed model; no multiplicity adjustment, no new confirmatory hypothesis test",
        "recommendation": "GO" if not any(not x["passed"] for x in consistency) and
                          sum(r["first_node1_event_before_second_replay_update"] for r in valid) else "CONDITIONAL GO"}
    return seed_rows, event_rows, margin_rows, summary


def pct(r):
    if r["proportion"] is None:
        return "不可估计"
    lo, hi = r["wilson95"]
    return f'{r["k"]}/{r["n"]}（{100*r["proportion"]:.2f}%；Wilson95% [{100*lo:.2f}%, {100*hi:.2f}%]）'


def format_stats(d):
    return f'{d["median"]:.6g} [{d["q1"]:.6g}, {d["q3"]:.6g}]；范围{d["min"]:.6g}–{d["max"]:.6g}'


def reports(audit, summary, rows):
    st, fo = summary["per_seed_summary"], summary["first_replay"]
    rec = audit["trigger_reconstruction"]
    paired = f"""# Task 0.5.1：历史文件完整性及Seed配对审计

**FACT。** 审计对象严格限两份指定NPZ；未读取test_inputs.npz、nominal_gains.npz或其他轨迹文件。本轮另读取config、环境、完成记录、版本说明、报告、历史源码和per_seed_metrics.csv元数据以核验来源。完整字段顺序、shape、dtype、min/max、NaN/Inf见01_data_integrity_audit.json的npz对象；两臂均7字段、全部有限，weights全1、clipped全False。

| 文件 | SHA256 | Task0匹配 |
|---|---|---|
| yang__clean.npz | {audit['npz']['clean']['sha256']} | 是 |
| yang__replay_packet.npz | {audit['npz']['replay']['sha256']} | 是 |

## 配对证据链

**FACT。** 历史config.json的test_seeds为start=40000、count=32。sources/model.py:81–83以有序range展开；93–100为各Seed单独default_rng、生成初态及过程/量测噪声。只阅读该源码，未执行数据生成。

**FACT。** 哈希核验过的sources/run_study.py:131–153只生成一次testseeds和x/y，然后两种通信protocol、每方法每场景共用这些对象。同一次simulator返回的第s行和同索引Seed同步写入NPZ及per_seed_metrics.csv。两目标arm的CSV行Seed顺序均为40000–40031，逐行网络广播数、边消息数、注入次数和裁剪率与NPZ重算完全一致。

**FACT。** 历史run_study.py:136–144明确closed_loop传schedule=None；engine.py:59–74按当前估计、上次发送参考、timeout计算事件。clean/Replay共用同一模型及名义增益，攻击分支仅替换链路载荷，不改x/y。weights=1、无裁剪与原Yang方法一致。历史engine/model/run_study的实际SHA逐项等于environment.json记录，详情见01。

**FACT（配置副本差异已解释）。** Task0记录的配置是隔离worktree的LF副本，主工作区原件为CRLF；初次脚本直接比较这两个不同字节来源而暂停，随后证实只有155处换行差异，规范化换行后字节完全相同，JSON参数逐项一致。01保留两个原始摘要及暂停说明，没有改写原件或降低NPZ摘要校验。

**FACT。** 全32Seed首次注入之前及注入r当拍，全节点估计与发送数组逐元素完全相等，最大状态差0；不能只凭“都是32行”作配对推断。本轮通过源码来源链、Seed元数据和数值前缀一致性确认配对。

**边界。** 两目标NPZ本身未嵌入Seed/x/y，故原始噪声不在这两个文件内；本轮没有额外读取或重生噪声逐元素比对。配对结论是可审计的历史生成来源和数值一致性结论，不是外部数字签名认证。

## 注入语义和原件保护

**FACT。** 共{audit['replay_source_validation']['count']}次注入，逐次核验目标sender确有发送，来源严格早于r且为该受攻臂sender此前第8个真实发送包，非注入处source=-1。cache_bad表示“当前缓存仍为直接替换载荷”，按fresh覆盖规则重构零不匹配；它不是当前估计污染标签。

**FACT。** 每Seed注入次数{format_stats(st['replay_injection_count'])}，首次注入时刻{format_stats(st['first_replay_time'])}。这是窗口内多次Replay；单包局部公式只核验首次注入后的下一拍。

**FACT。** 保护清单记录输入和核心文件前后摘要，Git HEAD/已跟踪差异不变。本轮未调用simulator、generate_data、旧runner或任何随机数生成器。未修改NPZ、配置、原结果；没有commit/push。
"""
    consistency_header = """# Task 0.5.5：首次Replay状态与触发裕度一致性

**DERIVED（仅首次注入局部关系）。** 在r当拍接收前两臂估计、缓存、发送参考和发送事件相同，目标0→1的raw历史载荷替换产生delta=hat_x_0(s)−hat_x_0(r)。原Yang、无门控/裁剪、同x/y时，本地项相消，只有该边一致性项改变，故

    d_1(r+1) = epsilon A delta.

令m为r当拍发送决定完成后节点1的参考值，它就是重构的reference_before[r+1]；两臂此值严格相同。e=hat_x_1^0(r+1)−m，因此

    Delta g_1(r+1) = 2 e^T(epsilon A delta) + ||epsilon A delta||².

平方范数交叉项可以为负，故裕度变化不必为正。这里e是“估计相对发送参考”的差，不是真实状态估计误差。

**FACT。** 采用历史config中的epsilon=.08、A=1.01I、theta=.12；来源s来自经合法性核验的replay_source，仅用于离线审计，不是检测器输入。未读取真状态、本地量测、健康噪声或生成新数据。原初始状态相同和噪声配对由02来源链确认。

"""
    consistency_header += f"""**FACT。** 32个Seed均可检查，状态公式最大绝对误差{fo['max_state_abs_error']:.17g}，裕度公式最大绝对误差{fo['max_margin_abs_error']:.17g}；其他节点r+1状态差最大值{fo['max_other_nodes_error_at_rplus1']:.17g}。工程一致性判据atol={ATOL:g}、rtol={RTOL:g}，失败{len(fo['failures'])}个；此容差不是严格浮点误差证明，也不是检测阈值。

| Seed | r | s | 真实年龄 | Δg观测 | Δg公式 | 状态最大绝对误差 | 裕度绝对误差 | r+1发送差 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
"""
    for x in fo["all_rows"]:
        consistency_header += f'| {x["seed"]} | {x["r"]} | {x["source"]} | {x["actual_age"]} | {x["margin_observed"]:.12g} | {x["margin_prediction"]:.12g} | {x["state_abs_error"]:.4e} | {x["margin_abs_error"]:.4e} | {x["first_step_event_difference"]} |\n'
    consistency_header += f"""
**FACT。** 首拍裕度正变化{summary['first_margin_positive']['k']}个、负变化{summary['first_margin_negative']['k']}个；首拍改变裕度但发送不变{summary['first_step_margin_changed_same_event']['k']}个；首拍离阈值零边界更近{summary['first_margin_closer_boundary']['k']}个。

**DERIVED。** 任意后续时刻仍可用保存的两臂状态核对纯代数恒等式：设h=hat_a−hat_0、b=m_a−m_0、e0=hat_0−m_0，则Delta g=2 e0^T(h−b)+||h−b||²。05CSV保存此项及误差，仅用于说明发送参考也会分叉；这不是预测h的闭环污染传播公式。本轮没有把epsilon A delta反复推广到多次Replay之后。

**FACT/边界。** 第一发送分叉不晚于第二次注入当拍的Seed为{summary['first_divergence_before_second_replay_update']['k']}/32；因为当拍发送先于载荷替换，所以此段发送差可归于首次注入的反馈。其余Seed不能将首次事件分叉唯一归因于第一包。全时域统计均是多次Replay结果，不伪装为独立单包实验。
"""
    main = f"""# Task 0.5：历史闭环SoD通信行为回溯审计

日期：2026-11-17。基准分支：{audit['git_before']['isolated']['branch']}；HEAD：{audit['git_before']['isolated']['head']}。仅分析指定两份历史NPZ。FACT为源码/保存数据事实；DERIVED为显式条件下的推导；OPEN为未验证问题。

## 结论A：通信行为是否受攻击影响

**FACT：是，在这批历史模型和攻击策略下已观察到。** 节点1事件分叉为{pct(summary['node1_any_divergence'])}。首次分叉时延中位数/IQR及范围：{format_stats(st['first_node1_divergence_delay'])}拍；绝对时刻：{format_stats(st['first_node1_divergence_time'])}。最早可在r+1发生，实际首拍分叉{pct(summary['first_step_event_divergence'])}。

**FACT。** 总发送次数增加{summary['send_count_increased']['k']}Seed、减少{summary['send_count_decreased']['k']}Seed、不变{summary['send_count_unchanged']['k']}Seed。节点1净次数差中位数[IQR]及范围：{format_stats(st['node1_send_count_difference'])}。同一次数不等于同一发送时序；不能把总体净差掩盖成“没有影响”，也不能预设Replay增加流量。

## 结论B：裕度机制是否可解释

**FACT/DERIVED：首次注入的局部关系通过。** 32Seed在r及以前估计/发送严格一致；下一拍状态污染公式最大绝对误差{fo['max_state_abs_error']:.4e}，触发裕度公式最大绝对误差{fo['max_margin_abs_error']:.4e}；详见[06首次Replay一致性](06_first_replay_consistency.md)。裕度增减取决于污染方向与健康触发向量的交叉项，不是只看污染范数。

**FACT。** 全32Seed首拍裕度均有超过诊断分辨率的变化，其中正{summary['first_margin_positive']['k']}、负{summary['first_margin_negative']['k']}；首拍发送未变而裕度已变{pct(summary['first_step_margin_changed_same_event'])}。首拍绝对裕度更接近0者{summary['first_margin_closer_boundary']['k']}/32；更大g并不总意味着更接近边界。

**FACT。** 节点1首次事件分叉全部由阈值布尔条件变化造成，两个臂此前自己的发送历史相同，因此timeout状态相同。整个400拍的节点1事件差异中，阈值标志单独变化{summary['node1_all_cause_tick_counts'].get('Threshold-flag-only',0)}次、timeout标志单独变化{summary['node1_all_cause_tick_counts'].get('Timeout-flag-only',0)}次、两标志均变化{summary['node1_all_cause_tick_counts'].get('Both-flags-changed',0)}次。后者不强行归入某一个原因；04另存更换单个OR条件是否足以改变结果。计数是依赖时间点的机制描述，非独立样本数。

## 结论C：是否值得进入下一阶段

**建议：{summary['recommendation']}，仅指值得继续建立闭环分叉理论。** 依据不是更换检测器或挑选好Seed，而是32Seed一致的可重构数据、明确双向裕度变化、首次公式及事件差异。在首次事件分叉时，仍未受到第二次Replay更新影响的Seed有{pct(summary['first_divergence_before_second_replay_update'])}；这给首次注入反馈提供了局部证据。

**OPEN。** 若要研究单次Replay后的完整持续时间、传播范围或辅助检测收益，仍有必要由负责人另行批准单次Replay的有限验证；本批每Seed多次替换，不能作完整单包因果确认。GO不是论文创新性结论、不是正式实验授权，本轮不进入Task1、不生成数据。

## 1. 数据可靠性与配对

- **FACT。** 两个原NPZ摘要与Task0相同；全部7字段shape/dtype、min/max、NaN/Inf已逐项复核，见[01完整性JSON](01_data_integrity_audit.json)。
- **FACT。** Seed为40000–40031，cfg、哈希核验过的历史runner、per_seed_metrics.csv同序记录及前缀完全相等共同支持配对；详见[02配对审计](02_seed_pairing_audit.md)。不是因为两文件都有32行就假定配对。
- **FACT。** 历史run_study.py:131–153共用x/y/testseeds，closed_loop传schedule=None。历史engine/model/runner字节摘要与原environment.json完全一致；不以当前engine替代历史源码。
- **FACT。** Task0配置副本与原件只差CRLF/LF，参数一致；首轮脚本的配置来源比较暂停及修正理由记录在01的config_Task0_comparison，不修改输入或绕过NPZ校验。
- **FACT。** 603次注入（完整计数见01），全部来源为同sender此前第8个实际发送包；clean无注入，权重全1、无裁剪，cache_bad按真实fresh重置可精确重构。
- **边界。** 未读取第三份NPZ来重新核对原始噪声；两份NPZ不含Seed/x/y，配对依赖已核验的生成来源链与数值一致性，不宣称外部签名保证。

## 2. 冻结模型与完整观察域

**FACT。** 历史config为N=5、n=2、T=400，A=1.01I、Q=.02I、P0=I、H_i=(1,.8,1.2,.9,1.1)_i I、R_i=.05I、epsilon=.08，五节点双向环。发送平方阈值theta=.12、timeout10、t0强制；不是后期上三角A/异质H模型。攻击边0→1，机会窗口200–249；每Seed注入次数{format_stats(st['replay_injection_count'])}，首次注入{format_stats(st['first_replay_time'])}。第8前序包不是固定64拍，首次实际年龄{format_stats(st['first_replay_actual_age'])}。

**FACT。** 统一使用全部32Seed与t=0…399共400个发送决定；estimates第400个末端状态没有对应发送决定，不补造t400事件。完整发送间隔为相邻两个已观察发送之间的diff；末端未完成静默单独记录为删失，不冒充完整间隔。不事后挑时间窗或Seed；首拍r+1是任务规定的理论核验点。

## 3. 精确事件重构与分类

**FACT。** 每臂从零发送参考及last_time=−10开始，以保存的pre-update估计计算距离，先判断严格>theta及timeout，再t0强制；仅由重构发送更新参考与时钟，未用保存sends强行纠正。每臂检查{rec['clean']['comparisons']}个节点事件，均0 mismatch。04CSV含64000行配对节点时刻，即128000个臂事件判断。

| 节点1类别 | clean时刻数 | Replay时刻数 | clean涉及Seed | Replay涉及Seed |
|---|---:|---:|---:|---:|
"""
    for label in CLASSES:
        cc, aa = [summary["node1_category_counts"][arm][label] for arm in NAMES]
        main += f'| {label} | {cc["tick_count"]} | {aa["tick_count"]} | {cc["seeds_with_category"]["k"]}/32 | {aa["seeds_with_category"]["k"]}/32 |\n'
    main += """
**FACT/解释。** Both表示两个条件同时满足。历史reason字段阈值优先、不会把Both单列；本轮按两布尔值恢复分类。初始强发单列Initial，不能当一般timeout证据。No-send与Mismatch分别保留。

## 4. Seed级通信与裕度统计

| 指标 | 结果 |
|---|---|
"""
    for label, key in [("有效注入Seed", "valid_injected"), ("节点1任意事件分叉", "node1_any_divergence"),
                       ("首次分叉相对共同历史提前", "earlier_from_last_common_send"),
                       ("首次分叉相对共同历史延迟", "later_from_last_common_send"),
                       ("发送次数增加", "send_count_increased"), ("发送次数减少", "send_count_decreased"),
                       ("发送次数不变", "send_count_unchanged"), ("首次事件前裕度已变", "changed_margin_before_first_event")]:
        main += f'| {label} | {pct(summary[key])} |\n'
    main += f"""
**FACT。** 全Seed首先各自计算完整间隔均值，再汇总：clean均值间隔的Seed中位数[IQR]/范围为{format_stats(st['node1_clean_mean_interval'])}；Replay为{format_stats(st['node1_replay_mean_interval'])}；配对均值间隔差为{format_stats(st['node1_mean_interval_difference'])}。没有把所有间隔合并成独立样本。

**定义。** “提前/延迟”以首次事件分叉前共同的自身发送历史为锚点，比较两臂从分叉时刻起的下一次发送。不是给每个新插入/消失包强行配对身份，也不是网络传输延迟。完整对应时刻和删失标志见03。

首次节点1事件分叉时延分布（拍: Seed数）：{json.dumps(summary['delay_histogram'],ensure_ascii=False)}。不存在发送事件分叉的Seed保留删失标志；本批32个均观察到。

**FACT。** 全时域节点1每Seed平均Delta g的中位数[IQR]/范围为{format_stats(st['node1_mean_delta_g'])}；首拍Delta g为{format_stats(st['first_step_delta_g'])}。05CSV有全部12800个配对节点1时刻的g0、ga、Delta g、两个参考、估计污染范数、阈值/timeout、接近边界与事件标志。诊断“数值改变”使用1e−12*(1+max|g|)分辨率，触发器仍原样使用严格距离>0.12，无任何阈值修改。

## 5. 全网传播描述

| 节点 | 出现事件分叉的Seed及Wilson区间 | 不同事件时刻 | Replay额外发送 | Replay缺失发送 |
|---:|---|---:|---:|---:|
"""
    for n in summary["network"]:
        main += f'| {n["node"]} | {pct(n["seeds_with_divergence"])} | {n["different_ticks"]} | {n["added_ticks"]} | {n["missing_ticks"]} |\n'
    main += f"""
**FACT。** 每Seed有事件分叉的节点数：{format_stats(st['network_divergence_nodes'])}。这是污染和后续发送/缓存反馈的描述，不是只凭链路最短路径证明每拍传播能力。全网统计仍每Seed一组，节点广播的两个出边不重复计独立证据。

## 6. 数学与研究边界

**DERIVED。** 发送标志是完整自身估计历史、发送参考及触发规则的确定性函数。它可能是有限残差摘要没有保留的信息，但不是相对于全部合法本地历史的独立新增信息；本任务未开发或检验联合检测器、虚警率或检测增益。

**FACT。** 继承G7的NO-GO：不能将SoD条件统计、阈值条件化或普通选择效应重新称创新。本轮只检验真实历史通信行为与首次局部恒等式，没有修改研究成功标准，没有把恢复E2/E3的覆盖、动作或MSE用作检测证据。

**OPEN。** 后续多次Replay与发送参考分叉混合影响，不能将32/32全窗差异归于一个孤立包；不能推断任意模型、任意Replay都改变通信，更不能推断检测必有优势。Wilson区间是固定模型下Seed级描述，不是全体节点/多指标联合保证，无bootstrap或新随机计算。

## 7. 图表、复核和停止

五张图使用全部32Seed保存数据：图01全时域双臂事件栅格；图02全时域裕度中位数/IQR及每Seed首拍Delta g；图03首次分叉延迟；图04逐Seed发送次数差；图05全网Seed事件分叉比例。未挑选示例Seed或有利子窗。

复算入口（现有Python，脚本不导入仿真模块）：

    python -B reviews/g1_communication_behavior/task0_5/code/analyze_closed_loop_events.py
    python -B reviews/g1_communication_behavior/task0_5/code/analyze_closed_loop_events.py --verify

默认只重建本目录同名派生结果，--verify只在内存复算并核对已有文本/CSV/JSON字节及完整SHA清单。全部产物SHA见SHA256SUMS.txt（不包含自身）。原始输入及核心文件前后哈希、两工作区HEAD/已跟踪差异核验见01。只读已有数据；没有新Seed/轨迹、没有Run、没有校准或检测器、没有commit/push。完成后停止，等待负责人审核；不执行Task1。
"""
    return main, paired, consistency_header


def plot_outputs(cfg, seeds, data, rec, summary, rows):
    os.environ["MPLCONFIGDIR"] = str(OUT / "figures" / ".mplconfig")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
    (OUT / "figures").mkdir(exist_ok=True)
    c, a = data["clean"], data["replay"]
    S, T, _ = c["sends"].shape
    start, end = cfg["attack"]["start"], cfg["attack"]["end_inclusive"]

    def save(fig, name):
        fig.savefig(OUT / "figures" / name, dpi=160)
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(13, 10), layout="constrained")
    for s, seed in enumerate(seeds):
        for arm, z, shift, color in [("Clean", c, -.14, "#255f85"), ("Replay", a, .14, "#d56635")]:
            times = np.flatnonzero(z["sends"][s, :, 1])
            ax.scatter(times, np.full(len(times), s+shift), marker="|", s=20, color=color, linewidths=.6)
        r = rows[s]["first_replay_time"]
        if r is not None:
            ax.scatter([r], [s], s=10, c="black", zorder=4)
    ax.axvspan(start, end, color="#c6c6c6", alpha=.25)
    ax.set(yticks=range(S), yticklabels=[str(s) for s in seeds], xlim=(0, T-1),
           ylim=(-1, S), xlabel="Decision time k (0-based)", ylabel="Paired Seed",
           title="Node 1: archived send events, all Seeds and all 400 decisions")
    ax.legend(handles=[Line2D([0], [0], color="#255f85", label="Clean (lower tick)"),
                       Line2D([0], [0], color="#d56635", label="Replay (upper tick)"),
                       Line2D([0], [0], marker="o", color="black", linewidth=0, label="First injection")],
              loc="upper left", ncol=3)
    ax.tick_params(axis="y", labelsize=8)
    save(fig, FIGURES[0])

    fig, axes = plt.subplots(2, 1, figsize=(12, 8), layout="constrained")
    for arm, label, color in [("clean", "Clean", "#255f85"), ("replay", "Replay", "#d56635")]:
        g = rec[arm]["margin"][:, :, 1]
        q = np.quantile(g, [.25, .5, .75], axis=0)
        axes[0].plot(range(T), q[1], color=color, label=label)
        axes[0].fill_between(range(T), q[0], q[2], color=color, alpha=.16)
    axes[0].set_yscale("symlog", linthresh=cfg["send_delta_squared"])
    axes[0].axhline(0, color="black", linewidth=.6)
    axes[0].axvspan(start, end, color="gray", alpha=.15)
    axes[0].set(title="Node 1 trigger margin: median and IQR over 32 Seeds",
                xlabel="Decision time k", ylabel="g(k); symmetric-log scale")
    axes[0].legend()
    vals = [r["first_step_delta_g"] for r in rows]
    pred = [r["margin_prediction"] for r in summary["first_replay"]["all_rows"]]
    axes[1].bar(range(S), vals, color=["#d56635" if v > 0 else "#255f85" for v in vals], label="Saved-data difference")
    axes[1].scatter(range(S), pred, color="black", marker="x", s=20, label="First-Replay identity")
    axes[1].axhline(0, color="black", linewidth=.6)
    axes[1].set(xticks=range(S), xticklabels=[str(s) for s in seeds], ylabel="Delta g(r+1)",
                xlabel="Seed", title="First post-injection decision (pre-specified local check)")
    axes[1].tick_params(axis="x", rotation=90, labelsize=8)
    axes[1].legend()
    save(fig, FIGURES[1])

    hist = summary["delay_histogram"]
    fig, ax = plt.subplots(figsize=(10, 4.5), layout="constrained")
    x = np.arange(len(hist))
    bars = ax.bar(x, list(hist.values()), color="#255f85")
    ax.bar_label(bars)
    ax.set(xticks=x, xticklabels=list(hist), xlabel="First node 1 event divergence: k - r (steps)",
           ylabel="Seed count", title="Observed delays, all 32 paired Seeds")
    ax.set_ylim(0, max(hist.values())+2)
    save(fig, FIGURES[2])

    fig, ax = plt.subplots(figsize=(12, 4.5), layout="constrained")
    vals = [r["node1_send_count_difference"] for r in rows]
    ax.bar(range(S), vals, color=["#d56635" if v > 0 else "#255f85" for v in vals])
    ax.axhline(0, color="black", linewidth=.6)
    ax.set(xticks=range(S), xticklabels=[str(s) for s in seeds], xlabel="Seed",
           ylabel="Replay sends - clean sends",
           title="Node 1 count difference: all 400 decisions; same count need not mean same timing")
    ax.tick_params(axis="x", rotation=90, labelsize=8)
    ax.set_yticks(range(min(vals)-1, max(vals)+2))
    save(fig, FIGURES[3])

    fig, ax = plt.subplots(figsize=(9, 5), layout="constrained")
    vals = [v["seeds_with_divergence"]["proportion"] for v in summary["network"]]
    bounds = np.array([v["seeds_with_divergence"]["wilson95"] for v in summary["network"]])
    bars = ax.bar(range(len(vals)), vals, color="#255f85",
                  yerr=np.maximum(0, np.array([vals-bounds[:, 0], bounds[:, 1]-vals])), capsize=5)
    for j, bar in enumerate(bars):
        ax.text(j, vals[j]+.02, f'{summary["network"][j]["seeds_with_divergence"]["k"]}/32', ha="center")
    ax.set(xticks=range(len(vals)), ylim=(0, 1.12), xlabel="Node",
           ylabel="Fraction of Seeds with at least one event difference",
           title="Network event divergence; descriptive Seed-level Wilson 95% intervals")
    save(fig, FIGURES[4])
    # Only remove the tool-created font cache; never touch historical data.
    cache = OUT / "figures" / ".mplconfig"
    if cache.exists():
        for p in cache.glob("fontlist-*.json"):
            p.unlink()
        if not any(cache.iterdir()):
            cache.rmdir()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    require(ROOT.name == "mypaper_g1r_e2_status_contract", "Use the isolated worktree only")
    OUT.mkdir(parents=True, exist_ok=True)
    inputs = [HIST/"closed_loop"/n for n in NAMES.values()]
    inputs += [HIST/p for p in ["config.json", "environment.json", "completion.json", "REPORT.md",
                                "VERSION_NOTES.md", "per_seed_metrics.csv",
                                "sources/engine.py", "sources/model.py", "sources/run_study.py"]]
    inputs += list(TASK0.glob("*.md")) + [TASK0/"02_parameter_manifest.json"]
    inputs += [ROOT/"simulation/runs/2026-11-10_five_node_v2/config.json"]
    inputs += [p/"simulation"/name for p in [ROOT, MAIN]
               for name in ["engine.py", "model.py", "config.json", "cache_monitor.py", "sequential_cache.py"]]
    original_hashes = {str(p): digest(p) for p in inputs}
    state = {"isolated": git_state(ROOT), "main": git_state(MAIN)}
    audit = {"classification": "FACT", "task": "Task 0.5", "date": "2026-11-17",
             "input_scope": "Exactly two named trajectory NPZ; other files metadata/source/report only",
             "analysis_script_sha256": digest(__file__), "git_before": state,
             "input_sha256_before": original_hashes,
             "runtime": {"python": sys.version.split()[0], "numpy": np.__version__}}
    try:
        cfg, seeds, data, rec = audit_inputs(audit)
        rows, events, margins, summary = compute(cfg, seeds, data, rec)
        audit["summary"] = summary
        require(not summary["first_replay"]["failures"], "First-Replay formula consistency failure")
        for name, expected in original_hashes.items():
            require(digest(name) == expected, "Input changed during audit: " + name)
        require(state == {"isolated": git_state(ROOT), "main": git_state(MAIN)}, "Tracked state changed")
        audit["protection"] = {"all_input_hashes_unchanged": True, "protected_file_count": len(original_hashes),
                               "HEAD_and_tracked_diffs_unchanged": True,
                               "simulate_calls": 0, "generate_data_calls": 0, "new_seed_trajectories": 0,
                               "other_npz_reads": 0, "old_runner_calls": 0, "calibration_calls": 0,
                               "git_commit_calls": 0, "git_push_calls": 0}
        audit["status"] = "PASS"
        audit["output_rows"] = {"03_seed_level_metrics.csv": len(rows),
                                "04_event_reconstruction.csv": len(events),
                                "05_trigger_margin_analysis.csv": len(margins)}
        main_md, pair_md, consistency_md = reports(audit, summary, rows)
        content = {OUTPUTS[0]: main_md, OUTPUTS[1]: json_text(audit), OUTPUTS[2]: pair_md,
                   OUTPUTS[3]: csv_text(rows), OUTPUTS[4]: csv_text(events),
                   OUTPUTS[5]: csv_text(margins), OUTPUTS[6]: consistency_md}
        if args.verify:
            for name, value in content.items():
                require((OUT/name).read_bytes() == value.encode("utf-8"), "Recomputation differs: " + name)
            sums = (OUT/"SHA256SUMS.txt").read_text(encoding="utf-8").splitlines()
            for line in sums:
                expected, relative = line.split("  ", 1)
                require(digest(OUT/relative) == expected, "Delivery SHA mismatch: " + relative)
            require(len(sums) == 13, "Manifest must contain 7 reports/data + 5 figures + script")
            print("VERIFY PASS: deterministic recomputation, all 13 artifact hashes, protected inputs")
        else:
            for name, value in content.items():
                (OUT/name).write_bytes(value.encode("utf-8"))
            plot_outputs(cfg, seeds, data, rec, summary, rows)
            listed = [OUT/name for name in OUTPUTS] + [OUT/"figures"/name for name in FIGURES] + [Path(__file__)]
            (OUT/"SHA256SUMS.txt").write_bytes("".join(
                f"{digest(p)}  {p.relative_to(OUT).as_posix()}\n" for p in sorted(listed)).encode("utf-8"))
            print(json_text({"status": "PASS", "out": str(OUT), "rows": audit["output_rows"],
                             "summary": {key: summary[key] for key in [
                                 "node1_any_divergence", "first_step_event_divergence",
                                 "first_divergence_before_second_replay_update", "node1_all_cause_tick_counts",
                                 "delay_histogram", "recommendation"]}}))
    except Hold as e:
        audit["status"] = "HOLD"
        audit["reason"] = str(e)
        if not args.verify:
            (OUT/OUTPUTS[1]).write_bytes(json_text(audit).encode("utf-8"))
            (OUT/OUTPUTS[0]).write_text("# Task 0.5：HOLD\n\n停止对应分析：" + str(e) +
                                      "\n\n未生成新轨迹、未修改原件；不绕过停止条件。\n", encoding="utf-8")
        raise


if __name__ == "__main__":
    main()
