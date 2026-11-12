"""Independent audit for the rank-one sensing pressure probe."""
from __future__ import annotations
import argparse, csv, hashlib, json
from pathlib import Path
import numpy as np


def read_rows(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def close(a, b, tol=1e-10):
    return bool(np.allclose(a, b, rtol=tol, atol=tol, equal_nan=True))


def main(run_path):
    out = Path(run_path)
    plan = json.loads((out / "plan.json").read_text(encoding="utf-8"))
    registration = json.loads((out / "registration.json").read_text(encoding="utf-8"))
    rows = read_rows(out / "per_seed_metrics.csv")
    index = {(r["schedule"], r["edge_label"], r["method"], r["scenario"], int(r["seed"])): r for r in rows}
    expected_rows = len(plan["schedules"]) * len(plan["attack_edges"]) * len(plan["methods"]) * len(plan["scenarios"]) * plan["splits"]["test"]["count"]
    assert len(rows) == expected_rows, (len(rows), expected_rows)
    assert len(index) == len(rows), "duplicate per-seed key"

    max_errors = {"mse_all": 0.0, "mse_attack_window": 0.0,
                  "receiver_attack_mse": 0.0, "receiver_clean_window_mse": 0.0}
    schedule_mismatch = 0
    illegal_packets = 0
    invalid_weights = 0
    files_checked = 0
    for schedule_name in plan["schedules"]:
        folder = out / schedule_name
        cfg = json.loads((folder / "config.json").read_text(encoding="utf-8"))
        inputs = np.load(folder / "test_inputs.npz")
        x = inputs["x"]
        schedule = inputs["schedule"]
        seeds = inputs["seeds"]
        assert len(seeds) == plan["splits"]["test"]["count"]
        for edge_label, edge_pair in plan["attack_edges"].items():
            edge_dir = folder / edge_label
            attack = json.loads((edge_dir / "attack.json").read_text(encoding="utf-8"))
            receiver = int(edge_pair[1])
            sender = int(edge_pair[0])
            for method in plan["methods"]:
                for scenario in plan["scenarios"]:
                    file = edge_dir / (method + "__" + scenario + ".npz")
                    with np.load(file) as data:
                        estimates = data["estimates"]
                        weights = data["weights"]
                        sends = data["sends"]
                        injected = data["injected"]
                    files_checked += 1
                    assert np.isfinite(estimates).all()
                    if not np.isfinite(weights).all() or np.any(weights < 0) or np.any(weights > 1):
                        invalid_weights += 1
                    if method != "local" and not np.array_equal(sends, schedule):
                        schedule_mismatch += 1
                    if scenario == "clean" and np.any(injected):
                        illegal_packets += 1
                    for s, seed in enumerate(seeds):
                        row = index[schedule_name, edge_label, method, scenario, int(seed)]
                        sq = np.sum((estimates[s] - x[s, :, None, :]) ** 2, axis=-1)
                        start = int(attack["start"]) + 1
                        end = int(attack["end_inclusive"]) + 2
                        values = {
                            "mse_all": float(sq[cfg["warmup"] + 1:].mean()),
                            "mse_attack_window": float(sq[start:end].mean()),
                            "receiver_attack_mse": float(sq[start:end, receiver].mean()),
                            "receiver_clean_window_mse": float(sq[cfg["warmup"] + 1:, receiver].mean())
                        }
                        for key, value in values.items():
                            reported = float(row[key])
                            max_errors[key] = max(max_errors[key], abs(value - reported))
                        times = np.flatnonzero(injected[s])
                        if scenario != "clean":
                            if np.any(times < int(attack["start"])) or np.any(times > int(attack["end_inclusive"])):
                                illegal_packets += 1
                            if np.any(~sends[s, times, sender]):
                                illegal_packets += 1

    expected_hashes = registration["source_sha256"]
    hash_ok = True
    for name, expected in expected_hashes.items():
        actual = hashlib.sha256((out / "sources" / name).read_bytes()).hexdigest()
        hash_ok &= actual == expected
    assert hash_ok
    assert schedule_mismatch == 0
    assert illegal_packets == 0
    assert invalid_weights == 0
    assert max(max_errors.values()) < 1e-10, max_errors
    result = {
        "passed": True,
        "rows": len(rows),
        "files_checked": files_checked,
        "max_mse_recompute_error": max(max_errors.values()),
        "mse_errors": max_errors,
        "schedule_mismatch": schedule_mismatch,
        "illegal_packet_cases": illegal_packets,
        "invalid_weight_files": invalid_weights,
        "source_hashes_match": bool(hash_ok),
        "new_simulations": False
    }
    (out / "output_audit.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    main(parser.parse_args().run)
