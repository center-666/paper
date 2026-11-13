"""Deterministic G4 counterexamples and algebra checks; no Monte Carlo."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="g4_theory_20261113_v1")
    args = parser.parse_args()
    if Path(args.run_id).name != args.run_id:
        raise ValueError("Run ID must be one directory name")
    out = Path(__file__).resolve().parents[1] / "results" / args.run_id
    out.mkdir(parents=True, exist_ok=False)

    # Exact one-step Yang special case: an authentic fresh sender can be worse
    # than the receiver's old cache, because the sender is still polluted.
    epsilon = .2
    passive_error, old_cache_error, sender_error, A = 0., 0., 1., 1.
    active_error = passive_error + epsilon*A*(sender_error-old_cache_error)
    increment = active_error**2-passive_error**2
    assert np.isclose(increment, .04)

    # Event consistency is necessary in this healthy-reference example but is
    # not sufficient for authenticity: an old -2 packet passes the same event.
    delta, last_auth, actual_now, replay = 1., 0., 2., -2.
    actual_event = (actual_now-last_auth)**2 > delta
    replay_passes_event_check = (replay-last_auth)**2 > delta
    assert actual_event and replay_passes_event_check

    # After one corrupted reference, an actual unmodified fresh packet can fail
    # an event check that incorrectly substitutes delivered for authentic ref.
    delta2, sender_ref, delivered_ref, next_actual = .09, 0., .3, .4
    genuine_event = (next_actual-sender_ref)**2 > delta2
    receiver_rejects = (next_actual-delivered_ref)**2 <= delta2
    assert genuine_event and receiver_rejects

    # Robust moment comparison: |tr(DP*(S-Shat))| <= ||DP||op ||S-Shat||*.
    P_passive = np.diag([2., 1.])
    P_active = np.diag([1., 1.5])
    S_hat = np.diag([2., .2])
    S_actual = np.array([[2.05, .02], [.02, .22]])
    radius = .1
    D = P_active-P_passive
    nuclear = float(np.linalg.svd(S_actual-S_hat, compute_uv=False).sum())
    upper = float(np.trace(D@S_hat)+radius*np.linalg.norm(D, 2))
    actual_difference = float(np.trace(D@S_actual))
    assert nuclear <= radius and actual_difference <= upper < 0

    # False-noise indistinguishability: two hypotheses have exactly the same
    # Gaussian law, not merely close Monte Carlo histograms.
    healthy_allowed_variance, privacy_variance, attack_variance = 3., 1., 2.
    assert healthy_allowed_variance == privacy_variance + attack_variance
    frequencies = np.array([0., .5, 1., 2.])
    healthy_cf = np.exp(-.5*healthy_allowed_variance*frequencies**2)
    attack_cf = (np.exp(-.5*privacy_variance*frequencies**2)
                 * np.exp(-.5*attack_variance*frequencies**2))
    assert np.max(np.abs(healthy_cf-attack_cf)) < 1e-15

    report = {
        "run_id": args.run_id,
        "scope": "Deterministic counterexamples and one trace-duality bound check; no trajectories, Monte Carlo or fitted algorithms",
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "fresh_polluted_sender": {
            "A": A, "epsilon": epsilon, "passive_error": passive_error,
            "old_cache_error": old_cache_error, "sender_error": sender_error,
            "active_error": active_error, "squared_error_increment": increment,
            "claim_disproved": "Extra authentic transmission universally improves recovery",
            "scope_limit": "A valid one-step augmented Yang error state; not a claim this exact state was reached in a specified G2 seed"
        },
        "trigger_evasion": {
            "delta_squared": delta, "last_authentic_reference": last_auth,
            "actual_current": actual_now, "historical_replay": replay,
            "actual_event": actual_event, "replay_passes_event_check": replay_passes_event_check,
            "claim_disproved": "Matching a Send-on-Delta event proves a payload authentic"
        },
        "trigger_reference_contamination": {
            "delta_squared": delta2, "sender_true_last_sent": sender_ref,
            "receiver_last_delivered": delivered_ref, "next_unmodified_packet": next_actual,
            "genuine_event": genuine_event, "receiver_rejects": receiver_rejects,
            "claim_disproved": "Substituting delivered payload for sender trigger reference is always valid after a Replay"
        },
        "robust_cost_comparison": {
            "P_passive": P_passive.tolist(), "P_active": P_active.tolist(),
            "estimated_second_moment": S_hat.tolist(), "actual_second_moment": S_actual.tolist(),
            "nuclear_radius": radius, "actual_nuclear_error": nuclear,
            "certified_upper_difference": upper, "actual_cost_difference": actual_difference,
            "status": "Algebraic illustration of a standard robust optimization certificate, not a deployed recovery guarantee"
        },
        "false_noise": {
            "healthy_allowed_variance": healthy_allowed_variance,
            "privacy_variance": privacy_variance, "attack_variance": attack_variance,
            "identical_law": "N(0,3) = law of independent N(0,1)+N(0,2)",
            "claim_disproved": "Unconstrained legitimate privacy-noise covariance permits universal separation of false-noise attacks"
        },
        "all_checks_passed": True
    }
    (out / "checks.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"run_id": args.run_id, "all_checks_passed": True,
                      "simulation_executed": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
