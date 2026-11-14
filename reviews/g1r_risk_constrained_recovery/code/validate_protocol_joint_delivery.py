"""Verify task-1/task-2 artifacts without generating any statistical sample."""
from __future__ import annotations

import ast
import csv
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
from scipy.stats import chi2

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parents[1]
RUN = HERE / "results/g1r_replay_joint_20261114_r01"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def seed_values(value):
    """Known explicit seed lists/ranges in JSON; do not instantiate an RNG."""
    result = set()
    if isinstance(value, dict):
        if isinstance(value.get("start"), int) and isinstance(value.get("count"), int):
            result.update(range(value["start"], value["start"]+value["count"]))
        for v in value.values():
            result.update(seed_values(v))
    elif isinstance(value, list):
        for v in value:
            result.update(seed_values(v))
    elif isinstance(value, int) and not isinstance(value, bool):
        result.add(value)
    return result


def seed_fields(value):
    result = set()
    if isinstance(value, dict):
        for key, v in value.items():
            if "seed" in key.lower():
                result.update(seed_values(v))
            else:
                result.update(seed_fields(v))
    elif isinstance(value, list):
        for v in value:
            result.update(seed_fields(v))
    return result


def main():
    protocol = json.loads((HERE/"protocol_v1.json").read_text(encoding="utf-8"))
    freeze = json.loads((RUN/"frozen_plan.json").read_text(encoding="utf-8"))
    summary = json.loads((RUN/"summary.json").read_text(encoding="utf-8"))
    for p, digest in freeze["source_sha256"].items():
        assert sha(ROOT/p) == digest, p
    assert sha(RUN/"replay_joint_matrices.npz") == summary["matrix_file_sha256"]
    assert summary["new_trajectories"] == 0 and summary["seeds_used"] == []
    assert freeze["protocol"] == protocol
    assert summary["pre_E2_budget_decision"] == "BUDGET_INFEASIBLE_STOP"
    with (RUN/"joint_cases.csv").open(encoding="utf-8", newline="") as f:
        cases = list(csv.DictReader(f))
    with (RUN/"budget_feasibility.csv").open(encoding="utf-8", newline="") as f:
        budgets = list(csv.DictReader(f))
    assert len(cases) == 24 and len(budgets) == 96
    max_cross_residual = 0.
    with np.load(RUN/"replay_joint_matrices.npz", allow_pickle=False) as data:
        eta, e0, Sigma_eta = data["eta_loading"], data["e0_loading"], data["Sigma_eta"]
        assert np.allclose(eta @ eta.T, Sigma_eta)
        for k, (edge, r, age) in enumerate(data["case_edge_r_age"]):
            theta = data["theta_loading"][k]
            O, G = data["O"][k], data["G"][k]
            Z = eta+O @ theta
            V, C = theta @ theta.T, theta @ eta.T
            Szz = data["Sigma_zz"][k]
            Ctz = data["Sigma_theta_z"][k]
            assert np.linalg.matrix_rank(O, tol=1e-10) == 2
            assert np.allclose(V @ O.T+C, Ctz, rtol=1e-8, atol=1e-10)
            assert np.allclose(Sigma_eta+O @ V @ O.T+O @ C+C.T @ O.T, Szz, rtol=1e-8, atol=1e-10)
            np.linalg.cholesky(Szz)
            B = data["B_theta_z"][k]
            posterior_residual = theta-B @ Z
            cross = posterior_residual @ Z.T
            scale = max(1.,np.linalg.norm(Ctz))
            max_cross_residual = max(max_cross_residual,float(np.linalg.norm(cross)/scale))
            assert np.linalg.norm(cross)/scale < 1e-8
            assert np.allclose(posterior_residual @ posterior_residual.T,
                               data["posterior_theta_covariance"][k], rtol=1e-8, atol=1e-9)
            s = r-age
            sender = 0 if edge == 0 else 2
            assert data["schedule"][s,sender] and data["schedule"][r,sender]
            Ea = e0+G @ theta
            assert np.allclose(Ea @ Ea.T, data["Sigma_ea"][k])
        assert np.isclose(np.sum(e0**2), summary["J0_actual_cached"])
    for row in budgets:
        U, R, J0, Ja = map(float, [row["U"],row["R"],summary["J0_actual_cached"],row["Ja"]])
        assert np.isclose(.05*U**2+2*U*np.sqrt(.05*J0), R, rtol=1e-12, atol=1e-15)
        gain = 1-max(1-U/np.sqrt(Ja),0.)**2
        assert np.isclose(gain,float(row["any_capped_action_relative_gain_upper"]),atol=1e-14)
    assert np.isclose(summary["chi_square_parameter_threshold"],chi2.ppf(1-.025/8,2))
    assert np.isclose(summary["chi_square_compatibility_threshold"],chi2.ppf(1-.025/8,10))

    protected_path = HERE/"sources/protocol_joint_20261114/protected_before.json"
    protected = json.loads(protected_path.read_text(encoding="utf-8"))
    allowed = {"reviews/g1r_risk_constrained_recovery/.gitattributes",
               "reviews/g1r_risk_constrained_recovery/EXECUTIVE_SUMMARY.md"}
    changed = [p for p,h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p) != h]
    assert set(changed) <= allowed, changed
    reserved = set()
    for key, item in protocol["seed_reservations"].items():
        block = set(range(item["start"], item["start"]+item["count"]))
        assert not (block & reserved), key
        reserved.update(block)
    prior_seed_values, numeric_hits = set(), []
    for p in protected:
        file = ROOT/p
        if file.suffix == ".json":
            try:
                prior_seed_values.update(seed_fields(json.loads(file.read_text(encoding="utf-8-sig"))))
            except (UnicodeError, json.JSONDecodeError):
                pass
        elif file.suffix == ".py":
            try:
                tree = ast.parse(file.read_text(encoding="utf-8-sig"))
                hits = {node.value for node in ast.walk(tree)
                        if isinstance(node, ast.Constant) and isinstance(node.value,int)
                        and node.value in reserved}
                if hits:
                    numeric_hits.append({"path":p,"values":sorted(hits)})
            except (UnicodeError, SyntaxError):
                pass
    assert not (reserved & prior_seed_values)
    assert not numeric_hits
    for p in [HERE/"code/replay_joint_statistics.py",Path(__file__)]:
        tree = ast.parse(p.read_text(encoding="utf-8"))
        calls = {node.func.id for node in ast.walk(tree)
                 if isinstance(node,ast.Call) and isinstance(node.func,ast.Name)}
        assert not (calls & {"simulate","generate_data","default_rng"})
    validation = {
        "result":"PASS", "scope":"task1/task2 only; no E2 data or new attack propagation validation",
        "validator_source_sha256":sha(__file__),
        "frozen_protocol_source_hashes_match":True,
        "stored_joint_formulas_and_posterior_orthogonality":True,
        "max_scaled_posterior_noise_observation_cross":max_cross_residual,
        "covariance_case_count":len(cases),"budget_row_count":len(budgets),
        "all_24_replay_sources_legitimate":True,"risk_bound_and_gain_ceiling_recomputed":True,
        "new_seed_reservations_disjoint_from_explicit_old_config_seeds_and_source_literals":True,
        "reserved_seed_count":len(reserved),"seeds_actually_used":[],
        "prior_tracked_files":len(protected),"explicit_old_report_updates":changed,
        "all_other_prior_files_unchanged":True,
        "decision":"BUDGET_INFEASIBLE_STOP; E2/E3 not run",
    }
    output = HERE/"sources/protocol_joint_20261114/verification.json"
    assert not output.exists()
    output.write_text(json.dumps(validation,indent=2)+"\n",encoding="utf-8",newline="\n")
    print(json.dumps(validation))


if __name__ == "__main__":
    main()
