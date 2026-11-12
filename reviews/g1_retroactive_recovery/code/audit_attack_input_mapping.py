from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
SIM = ROOT / "simulation"
BRANCH = Path(__file__).resolve().parents[1]
RUN_ID = "g1r_deghat_mapping_audit_20261112_04"
OUT = BRANCH / "results" / RUN_ID
sys.path.insert(0, str(SIM))

from engine import simulate
from model import generate_data

from minimal_recovery_screen import ATTACK_BIAS, R, TARGET_EDGE_PAIR, build_model, common_schedule


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    OUT.mkdir(parents=True)
    started = time.perf_counter()
    model = build_model()
    seeds = np.arange(9900000, 9900048)
    x, y = generate_data(model, seeds)
    schedule = common_schedule(model, len(seeds))
    clean = simulate(model, x, y, seeds, "yang", schedule=schedule, collect=False)
    rows = []
    source_edge = int(np.flatnonzero(np.all(model.edges == TARGET_EDGE_PAIR, axis=1))[0])
    sender, receiver = TARGET_EDGE_PAIR
    q = R + 8
    for scenario in ("single_step", "replay_packet"):
        attacked = simulate(model, x, y, seeds, "yang", scenario=scenario,
                            schedule=schedule, collect=False)
        for trial, seed in enumerate(seeds):
            source = int(attacked.replay_source[trial, R]) if scenario == "replay_packet" else -1
            if scenario == "replay_packet":
                if not (source < R and schedule[trial, source, sender]):
                    raise AssertionError("Replay source must be a previously sent authentic sender packet")
                delta_payload = attacked.estimates[trial, source, sender] - clean.estimates[trial, R, sender]
            else:
                delta_payload = attacked.estimates[trial, R, sender] + ATTACK_BIAS - clean.estimates[trial, R, sender]
            direct_forcing = []
            estimate_delta = np.zeros((model.cfg["N"], model.cfg["n"]))
            cache_delta = np.zeros((len(model.edges), model.cfg["n"]))
            last_receive = np.full(len(model.edges), -1, dtype=int)
            recurrence_errors = []
            initial_direct_error = None
            src, dst = model.edges.T
            for t in range(R, q):
                fresh = schedule[trial, t, src]
                for e, (j, i) in enumerate(model.edges):
                    if fresh[e]:
                        if e == source_edge and t == R:
                            cache_delta[e] = delta_payload
                        else:
                            # A later unmodified sender transmits the difference
                            # predicted by this recursion, not the simulator's
                            # oracle attacked-clean estimate difference.
                            cache_delta[e] = estimate_delta[j]
                        last_receive[e] = t
                age = np.where(last_receive >= 0, t - last_receive, 0)
                aligned_delta = np.einsum("eij,ej->ei", model.powers[age], cache_delta)
                local_innovation_delta = -np.einsum("imn,in->im", model.H, estimate_delta)
                local_delta = (estimate_delta @ model.A.T
                               + np.einsum("imn,in->im", model.gains[t], local_innovation_delta))
                consensus_delta = np.zeros_like(estimate_delta)
                for e, i in enumerate(dst):
                    consensus_delta[i] += aligned_delta[e] - estimate_delta[i]
                next_delta = local_delta + model.cfg["epsilon"] * (consensus_delta @ model.A.T)
                observed_delta = attacked.estimates[trial, t+1] - clean.estimates[trial, t+1]
                recurrence_errors.append(float(np.max(np.abs(next_delta-observed_delta))))
                if t == R:
                    direct_at_r = model.cfg["epsilon"] * model.A @ delta_payload
                    initial_direct_error = float(np.max(np.abs(observed_delta[receiver]-direct_at_r)))
                direct = model.cfg["epsilon"] * model.A @ model.powers[t-R] @ delta_payload
                direct_forcing.append(float(np.linalg.norm(direct)))
                estimate_delta = next_delta

            sender_send_times = np.flatnonzero(schedule[trial, :, sender])
            later_sends = sender_send_times[sender_send_times >= q]
            sender_discrepancy = np.linalg.norm(attacked.estimates[trial, later_sends, sender] -
                                                clean.estimates[trial, later_sends, sender], axis=1)
            receiver_discrepancy = np.linalg.norm(attacked.estimates[trial, q:, receiver] -
                                                  clean.estimates[trial, q:, receiver], axis=1)
            network_discrepancy = np.linalg.norm(attacked.estimates[trial, q:] -
                                                 clean.estimates[trial, q:], axis=(1, 2))
            rows.append({"scenario": scenario, "seed": int(seed), "direct_replacement_count": int(attacked.injected[trial, R]),
                "replay_source_time": source, "replay_content_age": R-source if source >= 0 else 0,
                "cache_packet_replaced_at_q": bool(schedule[trial, q, sender]),
                "new_packet_itself_unmodified": True,
                "sender_estimate_may_be_network_contaminated": True,
                "later_sender_send_count_q_to_T": len(later_sends),
                "later_sender_contaminated_send_count": int(np.sum(sender_discrepancy > 1e-10)),
                "max_later_sender_estimate_difference": float(sender_discrepancy.max(initial=0)),
                "receiver_estimate_difference_rms_q_to_T": float(np.sqrt(np.mean(receiver_discrepancy**2))),
                "network_estimate_difference_rms_q_to_T": float(np.sqrt(np.mean(network_discrepancy**2))),
                "direct_consensus_input_l2_over_residency": float(np.linalg.norm(direct_forcing)),
                "first_update_direct_formula_error": initial_direct_error,
                "full_network_difference_recursion_max_abs_error": float(max(recurrence_errors)),
                "mapping_scope": "direct term begins in estimate index r+1 (fusion iteration r, cache age zero); full-network recurrence includes later indirect sender feedback",
            })

    sources = [Path(__file__), BRANCH / "code/minimal_recovery_screen.py", SIM / "engine.py", SIM / "model.py"]
    write(OUT / "config.json", {"run_id": RUN_ID, "parent_run": "g1r_minimal_screen_20261112_02",
        "seeds": seeds.tolist(), "schedule": "same fixed exogenous gap8 schedule", "r": R, "q": q,
        "scenarios": ["single_step", "replay_packet"],
        "purpose": "separate direct one-packet input from indirect closed-loop sender-estimate propagation",
        "no_new_detector_or_parameter_tuning": True})
    write(OUT / "per_seed_propagation.csv", rows)
    summary = {}
    for scenario in ("single_step", "replay_packet"):
        subset = [r for r in rows if r["scenario"] == scenario]
        summary[scenario] = {
            "seeds": len(subset), "mean_later_contaminated_sender_sends": float(np.mean([r["later_sender_contaminated_send_count"] for r in subset])),
            "mean_max_later_sender_estimate_difference": float(np.mean([r["max_later_sender_estimate_difference"] for r in subset])),
            "mean_receiver_estimate_difference_rms_after_q": float(np.mean([r["receiver_estimate_difference_rms_q_to_T"] for r in subset])),
            "mean_network_estimate_difference_rms_after_q": float(np.mean([r["network_estimate_difference_rms_q_to_T"] for r in subset])),
            "all_next_packets_unmodified": bool(all(r["new_packet_itself_unmodified"] for r in subset)),
            "mean_direct_cache_consensus_input_norm": float(np.mean([r["direct_consensus_input_l2_over_residency"] for r in subset])),
            "first_update_direct_formula_max_abs_error": float(max(r["first_update_direct_formula_error"] for r in subset)),
            "full_network_difference_recursion_max_abs_error": float(max(r["full_network_difference_recursion_max_abs_error"] for r in subset)),
        }
    write(OUT / "summary.json", {"run_id": RUN_ID, "results": summary,
        "elapsed_seconds": time.perf_counter()-started, "paired_seed_unit": "seed",
        "interpretation": "independent recursive check: only the attacked payload difference at r is injected; every later unmodified transmission uses the recursion's predicted sender estimate difference. At fusion iteration r the age-zero payload is consumed immediately, so the extra update epsilon*A*delta enters estimate index r+1. Later indirect feedback is predicted by the full network error/cache recursion.",
        "source_hashes": {p.name: digest(p) for p in sources}})
    print(json.dumps(json.loads((OUT/"summary.json").read_text(encoding="utf-8")), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
