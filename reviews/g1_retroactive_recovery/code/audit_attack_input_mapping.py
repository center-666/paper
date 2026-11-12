from __future__ import annotations

import hashlib
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
SIM = ROOT / "simulation"
BRANCH = Path(__file__).resolve().parents[1]
RUN_ID = "g1r_deghat_mapping_audit_20261112_08"
OUT = BRANCH / "results" / RUN_ID
sys.path.insert(0, str(SIM))

from engine import simulate
from model import generate_data

from minimal_recovery_screen import ATTACK_BIAS, R, TARGET_EDGE_PAIR, build_model, common_schedule


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path, rows):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    OUT.mkdir(parents=True)
    started = time.perf_counter()
    roundoff_tolerance = 1e-10
    model = build_model()
    write(OUT / "preregistration.json", {
        "run_id": RUN_ID,
        "registered_before_simulation": True,
        "float_dtype": "float64",
        "full_horizon_iterations": model.cfg["T"]-R,
        "state_dimension": model.cfg["N"]*model.cfg["n"],
        "edge_count": len(model.edges),
        "absolute_tolerance": roundoff_tolerance,
        "tolerance_basis": "Conservative accumulation bound for a 280-step, 10-state, 10-edge linear recursion in float64; fixed before generating or comparing this Run ID.",
        "pass_rule": "Every state-component, cache-payload-component, and A^age-aligned cache-component recursion error over all seeds and times must be <= absolute_tolerance.",
    })
    seeds = np.arange(9900000, 9900048)
    x, y = generate_data(model, seeds)
    schedule = common_schedule(model, len(seeds))
    clean = simulate(model, x, y, seeds, "yang", schedule=schedule, collect=False)
    rows = []
    source_edge = int(np.flatnonzero(np.all(model.edges == TARGET_EDGE_PAIR, axis=1))[0])
    sender, receiver = TARGET_EDGE_PAIR
    q = R + 8
    T = model.cfg["T"]
    time_rows = []
    cache_rows = []
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
            actual_cache_delta = np.zeros((len(model.edges), model.cfg["n"]))
            last_receive = np.full(len(model.edges), -1, dtype=int)
            recurrence_errors = []
            initial_direct_error = None
            max_est_error = 0.0
            max_cache_error = 0.0
            max_aligned_cache_error = 0.0
            cache_replace_pre_errors = []
            cache_replace_post_errors = []
            src, dst = model.edges.T
            for t in range(R, T):
                fresh = schedule[trial, t, src]
                if t == q:
                    cache_replace_pre_errors = np.abs(
                        cache_delta[source_edge]-actual_cache_delta[source_edge]).tolist()
                for e, (j, i) in enumerate(model.edges):
                    if fresh[e]:
                        if e == source_edge and t == R:
                            recursive_packet_delta = delta_payload.copy()
                            if scenario == "replay_packet":
                                actual_source = int(attacked.replay_source[trial, t])
                                actual_packet_delta = (attacked.estimates[trial, actual_source, j]
                                                      - clean.estimates[trial, t, j])
                            else:
                                actual_source = -1
                                actual_packet_delta = ATTACK_BIAS.copy()
                        else:
                            # The recursive filter uses only its own predicted
                            # sender-estimate difference. Simulator trajectories
                            # are read below only for offline comparison.
                            recursive_packet_delta = estimate_delta[j].copy()
                            actual_source = -1
                            actual_packet_delta = (attacked.estimates[trial, t, j]
                                                   - clean.estimates[trial, t, j])
                        cache_delta[e] = recursive_packet_delta
                        actual_cache_delta[e] = actual_packet_delta
                        last_receive[e] = t
                age = np.where(last_receive >= 0, t - last_receive, 0)
                aligned_delta = np.einsum("eij,ej->ei", model.powers[age], cache_delta)
                actual_aligned_delta = np.einsum("eij,ej->ei", model.powers[age], actual_cache_delta)
                local_innovation_delta = -np.einsum("imn,in->im", model.H, estimate_delta)
                local_delta = (estimate_delta @ model.A.T
                               + np.einsum("imn,in->im", model.gains[t], local_innovation_delta))
                consensus_delta = np.zeros_like(estimate_delta)
                for e, i in enumerate(dst):
                    consensus_delta[i] += aligned_delta[e] - estimate_delta[i]
                next_delta = local_delta + model.cfg["epsilon"] * (consensus_delta @ model.A.T)
                observed_delta = attacked.estimates[trial, t+1] - clean.estimates[trial, t+1]
                node_error = np.abs(next_delta-observed_delta)
                max_step_est_error = float(node_error.max())
                recurrence_errors.append(max_step_est_error)
                max_est_error = max(max_est_error, max_step_est_error)
                payload_error = np.abs(cache_delta-actual_cache_delta)
                aligned_error = np.abs(aligned_delta-actual_aligned_delta)
                max_cache_error = max(max_cache_error, float(payload_error.max()))
                max_aligned_cache_error = max(max_aligned_cache_error, float(aligned_error.max()))
                if t == q and fresh[source_edge]:
                    cache_replace_post_errors = payload_error[source_edge].tolist()
                if t == R:
                    direct_at_r = model.cfg["epsilon"] * model.A @ delta_payload
                    initial_direct_error = float(np.max(np.abs(observed_delta[receiver]-direct_at_r)))
                direct = model.cfg["epsilon"] * model.A @ model.powers[t-R] @ delta_payload
                if t < q:
                    direct_forcing.append(float(np.linalg.norm(direct)))

                target_actual_source = int(attacked.replay_source[trial, t]) if scenario == "replay_packet" and attacked.replay_source[trial, t] >= 0 else -1
                time_row = {
                    "scenario": scenario, "seed": int(seed), "fusion_iteration": t,
                    "updated_state_index": t+1, "target_send_opportunity": bool(schedule[trial, t, sender]),
                    "target_new_packet_unmodified": bool(fresh[source_edge] and t != R),
                    "target_replay_source": target_actual_source,
                    "target_cache_age": int(age[source_edge]),
                    "target_recursive_cache_delta_norm": float(np.linalg.norm(cache_delta[source_edge])),
                    "target_actual_cache_delta_norm_offline": float(np.linalg.norm(actual_cache_delta[source_edge])),
                    "target_cache_delta_recursion_error": float(payload_error[source_edge].max()),
                    "target_aligned_cache_recursion_error": float(aligned_error[source_edge].max()),
                    "network_max_estimate_recursion_error": max_step_est_error,
                    "max_node0_error": float(node_error[0].max()),
                    "max_node1_error": float(node_error[1].max()),
                    "max_node2_error": float(node_error[2].max()),
                    "max_node3_error": float(node_error[3].max()),
                    "max_node4_error": float(node_error[4].max()),
                }
                for node in range(model.cfg["N"]):
                    for component in range(model.cfg["n"]):
                        time_row[f"predicted_node{node}_component{component}"] = float(next_delta[node, component])
                        time_row[f"observed_node{node}_component{component}_offline"] = float(observed_delta[node, component])
                        time_row[f"node{node}_component{component}_absolute_recursion_error"] = float(node_error[node, component])
                time_rows.append(time_row)
                for e, (j, i) in enumerate(model.edges):
                    cache_row = {
                        "scenario": scenario, "seed": int(seed), "fusion_iteration": t,
                        "edge_index": int(e), "sender": int(j), "receiver": int(i),
                        "packet_received_this_iteration": bool(fresh[e]),
                        "last_receive_iteration": int(last_receive[e]),
                        "cache_age": int(age[e]),
                        "recursive_payload_delta_norm": float(np.linalg.norm(cache_delta[e])),
                        "actual_payload_delta_norm_offline": float(np.linalg.norm(actual_cache_delta[e])),
                        "payload_delta_recursion_error": float(payload_error[e].max()),
                        "aligned_delta_recursion_error": float(aligned_error[e].max()),
                    }
                    for component in range(model.cfg["n"]):
                        cache_row[f"recursive_payload_delta_component{component}"] = float(cache_delta[e, component])
                        cache_row[f"actual_payload_delta_component{component}_offline"] = float(actual_cache_delta[e, component])
                        cache_row[f"payload_component{component}_recursion_error"] = float(payload_error[e, component])
                        cache_row[f"recursive_aligned_delta_component{component}"] = float(aligned_delta[e, component])
                        cache_row[f"actual_aligned_delta_component{component}_offline"] = float(actual_aligned_delta[e, component])
                        cache_row[f"aligned_component{component}_recursion_error"] = float(aligned_error[e, component])
                    cache_rows.append(cache_row)
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
                "full_network_difference_recursion_max_abs_error": max_est_error,
                "all_link_payload_recursion_max_abs_error": max_cache_error,
                "all_link_aligned_cache_recursion_max_abs_error": max_aligned_cache_error,
                "target_cache_replacement_pre_error_components": cache_replace_pre_errors,
                "target_cache_replacement_post_error_components": cache_replace_post_errors,
                "verified_iterations": T-R,
                "mapping_scope": "direct term begins in estimate index r+1 (fusion iteration r, cache age zero); full-network recurrence includes later indirect sender feedback",
            })

    sources = [Path(__file__), BRANCH / "code/minimal_recovery_screen.py", SIM / "engine.py", SIM / "model.py"]
    max_state_error = max(r["full_network_difference_recursion_max_abs_error"] for r in rows)
    max_payload_error = max(r["all_link_payload_recursion_max_abs_error"] for r in rows)
    max_aligned_error = max(r["all_link_aligned_cache_recursion_max_abs_error"] for r in rows)
    acceptance = {
        "absolute_tolerance": roundoff_tolerance,
        "max_network_state_error": max_state_error,
        "max_all_link_payload_error": max_payload_error,
        "max_all_link_aligned_cache_error": max_aligned_error,
        "passed": max(max_state_error,max_payload_error,max_aligned_error) <= roundoff_tolerance,
    }
    write(OUT / "config.json", {"run_id": RUN_ID, "parent_run": "g1r_minimal_screen_20261112_02",
        "seeds": seeds.tolist(), "schedule": "same fixed exogenous gap8 schedule", "r": R, "q": q,
        "scenarios": ["single_step", "replay_packet"],
        "full_horizon_end_state_index": T,
        "recursion_rule": "only inject one attack payload difference at r; all subsequent unmodified sender transmissions use the independently predicted sender estimate difference",
        "predeclared_numerical_acceptance": acceptance,
        "purpose": "separate direct one-packet input from indirect closed-loop sender-estimate propagation",
        "no_new_detector_or_parameter_tuning": True})
    write_csv(OUT / "per_seed_propagation.csv", rows)
    write_csv(OUT / "per_time_network_errors.csv", time_rows)
    write_csv(OUT / "per_time_link_cache_errors.csv", cache_rows)
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
            "all_link_payload_recursion_max_abs_error": float(max(r["all_link_payload_recursion_max_abs_error"] for r in subset)),
            "all_link_aligned_cache_recursion_max_abs_error": float(max(r["all_link_aligned_cache_recursion_max_abs_error"] for r in subset)),
            "max_error_before_q": float(max(float(v["network_max_estimate_recursion_error"]) for v in time_rows if v["scenario"] == scenario and int(v["fusion_iteration"]) < q)),
            "max_error_at_and_after_q": float(max(float(v["network_max_estimate_recursion_error"]) for v in time_rows if v["scenario"] == scenario and int(v["fusion_iteration"]) >= q)),
        }
    write(OUT / "summary.json", {"run_id": RUN_ID, "results": summary,
        "elapsed_seconds": time.perf_counter()-started, "paired_seed_unit": "seed",
        "interpretation": "independent recursive check: only the attacked payload difference at r is injected; every later unmodified transmission uses the recursion's predicted sender estimate difference. At fusion iteration r the age-zero payload is consumed immediately, so the extra update epsilon*A*delta enters estimate index r+1. Later indirect feedback is predicted by the full network error/cache recursion.",
        "source_hashes": {p.name: digest(p) for p in sources}})
    if not acceptance["passed"]:
        write(OUT / "acceptance_failure.json", acceptance)
        raise ArithmeticError(f"Full-horizon recursion exceeded preregistered tolerance: {acceptance}")
    print(json.dumps(json.loads((OUT/"summary.json").read_text(encoding="utf-8")), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
