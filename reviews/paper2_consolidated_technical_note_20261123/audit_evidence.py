"""Reconcile the technical note with published proofs, traces, and manifests."""
from __future__ import annotations

import csv
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys

import numpy as np
from scipy.stats import t as student_t

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
REVIEWS = HERE.parent
BASE = "7a2bca78e572f7a8e603da0f0ed237a6be6bda0c"
STAGE6 = REVIEWS / "paper2_stage6_vector_correction_20261122"
STAGE7 = REVIEWS / "paper2_stage7_fixed_amplitude_20261122"
STAGE9 = REVIEWS / "paper2_stage9_cumulative_evidence_20261123"
sys.path.insert(0, str(STAGE6))
sys.path.insert(0, str(STAGE9))

from exact_linear import (
    add, det2, encode, identity, inverse, matmul, matrix,
    psd2, scale, spd2, sub, transpose, update,
)
from paired_recovery import inputs, summarize
from validate_stage9 import verify


def read(path):
    return path.read_text(encoding="utf8")


def read_json(path):
    return json.loads(read(path))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def paired_moment(values):
    array = np.asarray(values, dtype=float)
    mean = float(array.mean())
    radius = float(student_t.ppf(.975, len(array) - 1) *
                   array.std(ddof=1) / math.sqrt(len(array)))
    return {"n": len(array), "mean": mean, "t95": [mean - radius, mean + radius]}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def covariance_and_risk():
    model = read_json(STAGE6 / "model.json")
    A, C, Q, P0 = (matrix(model[name]) for name in ("A", "C", "Q", "P0_prior"))
    R, Z = F(model["R"]), F(model["Z"])
    eye = identity(2)
    upper = matrix([[".9", ".1"], [".1", ".9"]])
    posterior, _, _ = update(upper, C, R + 1 / Z)
    slack = sub(upper, add(matmul(matmul(A, posterior), transpose(A)), Q))
    lower = inverse(add(inverse(Q), scale(matmul(transpose(C), C), 1 / R)))
    checks = {
        "observable": det2([C[0], matmul(C, A)[0]]) == F(1, 10),
        "initial_above_process_covariance": psd2(sub(P0, Q)),
        "initial_below_supersolution": psd2(sub(upper, P0)),
        "supersolution_slack_positive": spd2(slack),
        "prior_upper_le_identity": psd2(sub(eye, upper)),
        "process_covariance": Q == scale(eye, F(1, 20)),
        "posterior_lower": lower == matrix([[".04", "0"], ["0", ".05"]]),
        "posterior_upper_le_identity": psd2(sub(eye, posterior)),
    }
    require(all(checks.values()), "Covariance contract failed")
    archived = read_json(STAGE6 / "covariance_certificate.json")
    require(encode(slack) == archived["supersolution_minus_all_silent_riccati"],
            "Covariance slack differs from archive")
    require(det2(slack) == F(archived["slack_determinant"]), "Slack determinant differs")
    # Rational relaxations keep the displayed risk budget auditable.
    require(F(19, 20) < F(39, 40) ** 2, "Contraction relaxation failed")
    require(F(11, 25) ** 2 < R, "Noise relaxation failed")
    theta_radius = F(model["attack_amplitude_cap"]) / (F(11, 25) * F(1, 40))
    action_radius, epsilon, horizon = F(1), F(1, 1000), 512
    penalty = 2 * epsilon * horizon * (
        theta_radius * action_radius + action_radius ** 2)
    require(penalty == F(33408, 1375), "Expectation penalty differs")
    return {"checks": checks, "exact_slack": encode(slack),
            "slack_determinant": str(det2(slack)), "M": "5", "rho_squared": "19/20",
            "conservative_theta_radius": str(theta_radius),
            "expectation_penalty_512": str(penalty),
            "expectation_penalty_display": float(penalty)}


def scalar_time_contract():
    directory = REVIEWS / "paper2_stage5_certification_acceleration_20261122"
    rows = read_json(directory / "new_time_bounds.json")["rows"]
    leaves = []
    for path in sorted((directory / "fourier_certificates").glob("*_verification.json")):
        verification = read_json(path)
        certificate_path = path.with_name(path.name.replace("_verification.json", ".json"))
        require(verification["status"] == "PASS" and verification["root_domain_covered"],
                "Archived affinity verification failed")
        require(F(verification["minimum_gap_lower"]) >= F(1, 10000), "Gap is too small")
        require(sha(certificate_path) == verification["certificate_sha256"],
                "Affinity certificate hash differs")
        leaves.append({"model": verification["model"], "gap": verification["amplitude_gap"],
                       "leaves": verification["verified_leaves"]})
    require(len(leaves) == 6 and sum(x["leaves"] for x in leaves) == 27568,
            "Archived affinity tree count differs")
    ages = {row["model"]: row["new_sufficient_age"] for row in rows}
    require(ages == {"S1": 255199, "U1": 252346}, "Scalar time contract differs")
    return {"archived_leaf_verifications": leaves, "leaf_count": 27568,
            "sufficient_ages": ages, "amplitude_dictionary": rows[0]["dictionary"],
            "current_run_scope": "archived verification and raw certificate hashes"}


def detection_contract():
    path = REVIEWS / "paper2_stage3_joint_detection_20261121/analysis/final_metrics.csv"
    with path.open(encoding="utf8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    selected = [row for row in rows if row["stage"] == "final" and
                F(row["b"]) == F(1, 4) and row["onset"] == "200" and row["H"] == "512"
                and (row["method"].startswith("J1_") or row["method"].startswith("P1_"))]
    require(len(selected) == 4, "Detection comparator selection differs")
    joint_rows = [{key: row[key] for key in ("model", "method", "detected", "eligible_n",
                                             "power", "CP_lower95", "restricted_delay")}
                  for row in selected]
    event_path = REVIEWS / "paper2_stage2_detection_20261121/analysis/information_power_bounds.json"
    event_rows = [row for row in read_json(event_path) if row["horizon"] == 2048 and
                  row["onset"] == 200 and row["attack_strength"] == .25]
    expected_upper = {"S1": .0535, "U1": .3106}
    require(len(event_rows) == 2, "Event information selection differs")
    for row in event_rows:
        require(abs(row["binary_data_processing_detection_probability_upper"] -
                    expected_upper[row["model"]]) < .00005,
                "Event information upper bound differs")
    return {"joint_detection": joint_rows, "phase_averaged_event_information": event_rows}


def stage7_contract():
    paths = sorted((STAGE7 / "results/fresh_confirmation").glob("b0.25_episode*.json"))
    require(len(paths) == 12, "Stage 7 strong group count differs")
    rows = [read_json(path) for path in paths]
    difference = [row["snapshots"]["512"]["new_gain"] -
                  row["snapshots"]["512"]["old_gain"] for row in rows]
    moment = paired_moment(difference)
    require(abs(moment["mean"] - 2.0869) < .00005, "Stage 7 paired gain differs")
    require(moment["t95"][0] > 0, "Stage 7 descriptive interval changed")
    return {"strong_episodes": 12, "paired_gain_fixed_parameters_vs_halfspace": moment,
            "total_confirmation_episodes": len(list(
                (STAGE7 / "results/fresh_confirmation").glob("*.json")))}


def stage9_contract():
    protocol = read_json(STAGE9 / "stage9_protocol.json")
    deterministic = read_json(STAGE9 / "stage9_checks.json")
    require(deterministic["status"] == "PASS" and
            deterministic["source_sha256"] == sha(STAGE9 / "cumulative_envelope.py"),
            "Deterministic record source differs")
    require(len(deterministic["checks"]) == deterministic["check_count"] == 1712 and
            all(item["pass"] for item in deterministic["checks"]),
            "Deterministic record differs")
    verified = {}
    replay_prefixes = verify("replay", protocol, verified)
    fresh_prefixes = verify("fresh", protocol, verified)
    require(replay_prefixes.isdisjoint(fresh_prefixes), "Replay and fresh histories overlap")
    result = {"archived_deterministic_checks": 1712, "verified_trace_contracts": verified}
    for mode in ("replay", "fresh"):
        rows = [read_json(path) for path in sorted((STAGE9 / f"{mode}_episodes").glob("*.json"))]
        rows.sort(key=lambda row: (row["case"], row["episode"]))
        summary = read_json(STAGE9 / f"{mode}_summary.json")
        computed = summarize(rows, mode, sha(STAGE9 / f"{mode}_freeze.json"))
        require(computed == summary, "Stage 9 aggregate differs")
        common = [query for row in rows for query in row["queries"]
                  if "8" in query and "9" in query]
        times = summary["time_totals"]
        result[mode] = {
            "episodes": len(rows), "common_queries": len(common),
            "joint_successes": summary["joint_successes"],
            "different_decisions": summary["different_decisions"],
            "query_seconds": {key: times[key]["query"] for key in ("8", "9")},
            "end_to_end_seconds": {key: times[key]["end_to_end"] for key in ("8", "9")},
            "query_reduction_percent": 100 * (1 - times["9"]["query"] / times["8"]["query"]),
            "end_to_end_reduction_percent": 100 * (
                1 - times["9"]["end_to_end"] / times["8"]["end_to_end"]),
            "mean_query_seconds": {key: times[key]["query"] / len(common) for key in ("8", "9")},
            "maximum_query_seconds": {key: max(query[key]["seconds"] for query in common)
                                      for key in ("8", "9")},
            "cases": summary["cases"],
        }
        if mode == "fresh":
            result[mode]["healthy_total_steps"] = sum(
                row["steps"] for row in rows if row["case"] == 0)
        for case, archived in summary["cases"].items():
            group = [row for row in rows if str(row["case"]) == case]
            recomputed = paired_moment([row["metrics"]["8"]["loss"] -
                                         row["metrics"]["9"]["loss"] for row in group])
            require(recomputed["t95"] == archived["stage9_gain_vs_stage8"]["t95"],
                    "Independent paired interval differs")
    return result


def source_manifest():
    note = read(HERE / "technical_note.md")
    targets = re.findall(r"\]\(([^)]+)\)", note + read(HERE / "README.md"))
    paths = {HERE / "technical_note.md", HERE / "README.md", Path(__file__)}
    for target in targets:
        if target.startswith(("http:", "https:")) or target == "evidence_audit.json":
            continue
        path = (HERE / target.split("#")[0]).resolve()
        require(path.is_file() and path.is_relative_to(REPO), "Missing local source " + target)
        paths.add(path)
    # Include all original frozen inputs and the records used in this audit.
    protocol = read_json(STAGE9 / "stage9_protocol.json")
    paths.update(REVIEWS / relative for relative in inputs(protocol))
    for directory in ("replay_episodes", "fresh_episodes"):
        paths.update((STAGE9 / directory).glob("*.json"))
    paths.update((STAGE7 / "results/fresh_confirmation").glob("*.json"))
    paths.update((REVIEWS / "paper2_stage5_certification_acceleration_20261122" /
                  "fourier_certificates").glob("*.json"))
    paths.add(STAGE6 / "covariance_certificate.json")
    paths.add(STAGE9 / "validate_stage9.py")
    paths.add(STAGE9 / "stage9_checks.json")
    for mode in ("replay", "fresh"):
        paths.add(STAGE9 / f"{mode}_freeze.json")
        paths.add(STAGE9 / f"{mode}_summary.json")
    paths.add(REVIEWS / "paper2_stage5_certification_acceleration_20261122/new_time_bounds.json")
    paths.add(REVIEWS / "paper2_stage3_joint_detection_20261121/analysis/final_metrics.csv")
    paths.add(REVIEWS / "paper2_stage2_detection_20261121/analysis/information_power_bounds.json")
    return {path.relative_to(REPO).as_posix(): sha(path) for path in sorted(paths)}


def main():
    subprocess.run(["git", "cat-file", "-e", BASE + "^{commit}"], cwd=REPO, check=True)
    result = {
        "status": "PASS",
        "research_base_commit": BASE,
        "audit_scope": "proof-dependency review, exact covariance recomputation, archived evidence reconciliation",
        "covariance_and_risk": covariance_and_risk(),
        "scalar_time_contract": scalar_time_contract(),
        "scalar_detection_evidence": detection_contract(),
        "stage7": stage7_contract(),
        "stage9": stage9_contract(),
        "open_guarantees": [
            "positive unconditional expected recovery gain for current implementation",
            "short-window startup for weak amplitudes and late onsets",
            "full monitor recursion rounding enclosure",
            "finite-word feedback and uplink observation kernels",
            "formula-level comparison with the named identification-compensation neighbor",
        ],
        "source_sha256": source_manifest(),
        "new_performance_samples": 0,
    }
    target = HERE / "evidence_audit.json"
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                      encoding="utf8", newline="\n")
    print(json.dumps({"status": result["status"], "sources": len(result["source_sha256"]),
                      "covariance_checks": len(result["covariance_and_risk"]["checks"]),
                      "stage9_contracts": result["stage9"]["verified_trace_contracts"],
                      "new_performance_samples": 0}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
