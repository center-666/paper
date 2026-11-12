from __future__ import annotations

import csv
import hashlib
import json
import platform
import sys
from pathlib import Path

import numpy as np
from scipy import stats


ROOT = Path(__file__).resolve().parents[3]
SIM = ROOT / "simulation"
RUN = Path(__file__).resolve().parents[1] / "results" / "g1r_minimal_screen_20261112_02"


def csv_rows(path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def ci(values):
    x = np.asarray(values, float)
    if len(x) < 2:
        return {"n": len(x), "mean": float(x.mean()) if len(x) else None, "ci95": None}
    half = stats.t.ppf(0.975, len(x)-1) * x.std(ddof=1) / np.sqrt(len(x))
    return {"n": len(x), "mean": float(x.mean()), "ci95": [float(x.mean()-half), float(x.mean()+half)]}


def main():
    rows = csv_rows(RUN / "per_seed_methods.csv")
    by = {(r["scenario"], r["method"], int(r["seed"])): r for r in rows}
    comparisons = []
    pairs = [
        ("replay_packet", "candidate_gls_receiver_only", "attack_no_defense", "receiver_excess_mse"),
        ("replay_packet", "candidate_gls_receiver_only", "receiver_drop_and_replay", "receiver_excess_mse"),
        ("replay_packet", "candidate_gls_receiver_only", "receiver_local_filter_from_checkpoint", "receiver_excess_mse"),
        ("replay_packet", "receiver_drop_and_replay", "attack_no_defense", "receiver_excess_mse"),
        ("replay_packet", "receiver_local_filter_from_checkpoint", "attack_no_defense", "receiver_excess_mse"),
        ("single_step", "candidate_gls_receiver_only", "attack_no_defense", "receiver_excess_mse"),
        ("replay_packet", "candidate_gls_global_with_correction_broadcast", "attack_no_defense", "network_excess_mse"),
    ]
    for scenario, candidate, baseline, field in pairs:
        keys = sorted(k[2] for k in by if k[0] == scenario and k[1] == baseline)
        diffs = [float(by[scenario, candidate, s][field]) - float(by[scenario, baseline, s][field]) for s in keys]
        comparisons.append({"scenario": scenario, "candidate": candidate, "baseline": baseline,
                            "metric": field, "candidate_minus_baseline": ci(diffs),
                            "negative_favors_candidate": True, "descriptive_only": True})

    per_attack = csv_rows(RUN / "per_seed_attacks.csv")
    packet = csv_rows(RUN / "packet_audit.csv")
    normal = csv_rows(RUN / "normal_correction_audit.csv")
    cfg = json.loads((RUN / "config.json").read_text(encoding="utf-8"))
    T, n, N = cfg["model"]["T"], cfg["model"]["n"], cfg["model"]["N"]
    # Each node sends once every eight ticks at its phase; t=0 is forced for all.
    times = np.arange(T)
    opportunities = [int(np.count_nonzero(((times % 8) == node) | (times == 0))) for node in range(N)]
    broadcasts = sum(opportunities)
    edges = np.asarray(cfg["model"]["edges_sender_receiver"])
    directed_messages = int(sum(opportunities[node] * int(np.count_nonzero(edges[:, 0] == node)) for node in range(N)))
    summary = {
        "run_id": RUN.name,
        "primary_effects": comparisons,
        "candidate_detection_trigger_rate": {
            scenario: float(np.mean([r["correction_triggered"] == "True" for r in per_attack if r["scenario"] == scenario]))
            for scenario in ("single_step", "replay_packet")
        },
        "normal_test_false_correction_rate": float(np.mean([r["correction_triggered"] == "True" for r in normal])),
        "normal_test_receiver_mse_change": ci([float(r["receiver_corrected_mse"])-float(r["receiver_normal_mse"]) for r in normal]),
        "packet_replacement_counts": {s: int(sum(int(r["replacement_count"]) for r in packet if r["scenario"] == s)) for s in ("single_step", "replay_packet")},
        "mean_replacement_count_per_seed": {s: float(np.mean([int(r["replacement_count"]) for r in packet if r["scenario"] == s])) for s in ("single_step", "replay_packet")},
        "mean_replay_content_age": float(np.mean([int(r["content_age"]) for r in packet if r["scenario"] == "replay_packet"])),
        "communication": {"common_schedule": "gap8 exogenous", "broadcasts_per_seed": broadcasts,
            "directed_edge_packets_per_seed": directed_messages,
            "estimate_payload_bytes_per_seed": int(directed_messages*n*8),
            "correction_message": "not implemented or charged; at least one event ID/time plus 2D estimate-influence vector and routing/authentication overhead"},
        "environment": {"python": sys.version, "numpy": np.__version__, "scipy": __import__("scipy").__version__, "platform": platform.platform()},
        "source_hashes": json.loads((RUN / "source_hashes.json").read_text(encoding="utf-8")),
        "note": "Run 01 had a reporting-index bug for the receiver component of the global oracle row; Run 02 is the corrected same-seed rerun, not an independent replication."
    }
    (RUN / "audit_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
