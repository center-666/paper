"""Prepare a design and extract saved evidence. No random numbers or simulations.

Read the original frozen results, compute only deterministic scalar covariance
constants for k=4, and write separate integration artifacts.
"""
from pathlib import Path
import csv
import hashlib
import io
import json
import math

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = ROOT / "papers/latex_ecust_20261102"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def scalar_constants(A, P0=.8, Q=.05, R=.2, Z=2., k=4):
    priors = [P0]
    for _ in range(k):
        priors = [
            A*A*(P - P*P/(P + Ri)) + Q
            for P in priors for Ri in (R + 1/Z, R)
        ]
    gains = [P/(P+R) for P in priors]
    alpha_min, alpha_max = abs(A)*min(gains), abs(A)*max(gains)
    Smin = min(priors)+R
    pstar = min(1 - 1/math.sqrt(1+Z*(P+R)) for P in priors)
    Lstar = (math.sqrt(2/(math.pi*Smin))+math.sqrt(Z/math.e))/alpha_min
    dstar = pstar/Lstar
    cap = min(.1, dstar/2, alpha_max*.1/2)
    assert len(priors) == 2**k
    assert 0 < cap <= dstar and cap/(2*alpha_max) <= .1/4 + 1e-15
    return dict(
        P_min=min(priors), P_max=max(priors), K_min=min(gains),
        K_max=max(gains), alpha_min=alpha_min, alpha_max=alpha_max,
        p_star=pstar, L_star=Lstar, delta_star=dstar,
        delta_cap=cap, delta_grid=[cap*f for f in (.25,.5,1)],
        eta_grid=[cap*f/(2*alpha_max) for f in (.25,.5,1)]
    )


def main():
    original_results = OLD / "vector_data/results.json"
    original_rows = OLD / "vector_data/results.csv"
    saved = json.loads(original_results.read_text(encoding="utf-8"))
    evidence = []
    for name in ("S", "U"):
        c = saved["cases"][name]
        base = c["budget_base_row"]
        const = c["constants"]
        evidence.append({
            "model":name, "status":"SAVED_OLD_RESULT",
            "policy":base["policy"], "b":base["b"],
            "J":base["J"], "population_certificate":base["population_certificate"],
            "certificate_over_J":base["population_certificate"]/base["J"],
            "old_compensated_budget_bound_ratio":
                const["C_record"]*const["C_pm"]/const["L_v"],
            "center_known_N10000":c["sampling"]["centered_known_bound"],
            "center_two_N10000":c["sampling"]["centered_two_bound"],
            "source":original_results.relative_to(ROOT).as_posix(),
            "source_sha256":sha(original_results),
        })
    selected = [
        row for row in csv.DictReader(io.StringIO(original_rows.read_text(encoding="utf-8")))
        if float(row["b"]) == .1
    ]
    (HERE/"saved_evidence.json").write_text(
        json.dumps(dict(summary=evidence, damage_decomposition_rows=selected,
                        old_csv_sha256=sha(original_rows), rerun=False),
                   ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    models = [dict(id=name,A=A,m0=0,P0=.8,Q=.05,R=.2,Z=2,k=4,
                   design_constants=scalar_constants(A))
              for name,A in (("S1",.82),("U1",1.04))]
    protocol = {
        "protocol_version":"v0.1",
        "status":"DESIGN_ONLY_NOT_RUN",
        "calculated":"Covariance label enumeration and parameter range only",
        "models":models,
        "provenance":"Standalone scalar surrogates from first-coordinate coefficients; not marginals of the coupled 2D models.",
        "b":.1, "b_ref":.1, "delta_ref":.1,
        "selector":"delta_cap=min(delta_ref,delta_star/2,alpha_max*b/2); delta=cap*[.25,.5,1]",
        "quantizer":"Q(x)=2*delta*floor((x+delta)/(2*delta)); half-open cells; no saturation",
        "coupling":{
            "base_samples_per_model":2048, "models_independent":True,
            "shared_across":["precision","protocol","healthy_and_sign_branches"],
            "sign_integration":"Average + and - per base sample; not two independent observations"
        },
        "rng_plan":{"bit_generator":"PCG64","master_seed":2026111901,
                    "SeedSequence_components":["master_seed","model_id","base_sample_id","noise_type"],
                    "model_id":{"S1":1,"U1":2},
                    "noise_type":{"initial":0,"process":1,"measurement":2,"trigger_uniform":3},
                    "generated_in_this_stage":False},
        "actual_protocols":["A_exact_feedback","B_quantized_feedback"],
        "views":["C_payload_same_B","C_predictor_same_B","A_rounded_log_same_A"],
        "policy":"One predeclared central-half-cell gate at k=4, eta=min(b,delta/(2*alpha_max)), sign branches +/-; no other action",
        "history_end":5,
        "branch_runs_max":2*3*2*3*2048,
        "independent_base_paths":2*2048,
        "bootstrap":{"replicates":1000,"seed":2026111902,
                     "unit":"base sample within model, paired across cells","role":"exploratory intervals only"},
        "TV_claims":{"B":"analytic equality; sample path identity for implementation only",
                     "C":"analytic moment witness plus observed paired moments; no V_C=0 claim",
                     "histogram":"No full continuous-log TV estimation"},
        "stops":["source/version/permission mismatch","any B event or quantizer-index mismatch",
                 "deterministic identity failure","numerical scale unresolved"],
        "new_simulation_results_exist":False,
    }
    assert protocol["branch_runs_max"] == 73728
    assert protocol["independent_base_paths"] == 4096
    assert len(selected) == 4
    (HERE/"experiment_protocol.json").write_text(
        json.dumps(protocol,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":protocol["status"],"models":models,
                      "saved_evidence_rows":len(selected)},ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()
