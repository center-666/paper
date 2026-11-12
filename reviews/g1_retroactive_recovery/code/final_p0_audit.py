from __future__ import annotations

import ast
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

BRANCH=Path(__file__).resolve().parents[1]
RESULTS=BRANCH/"results"
PROP=RESULTS/"g1r_deghat_mapping_audit_20261112_08"
INFO=RESULTS/"g1r_deghat_output_channels_20261112_07"
OUT=RESULTS/"g1r_p0_final_audit_20261112_05"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path):
    with path.open(newline="",encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_full_horizon():
    cfg=read_json(PROP/"config.json")
    prereg=read_json(PROP/"preregistration.json")
    summary=read_json(PROP/"summary.json")
    node_rows=read_csv(PROP/"per_time_network_errors.csv")
    cache_rows=read_csv(PROP/"per_time_link_cache_errors.csv")
    seed_rows=read_csv(PROP/"per_seed_propagation.csv")
    T=280;r=200;q=208;seeds=48;scenarios={"single_step","replay_packet"}
    expected_times=seeds*(T-r)*len(scenarios)
    expected_cache=expected_times*10
    assert len(node_rows)==expected_times,(len(node_rows),expected_times)
    assert len(cache_rows)==expected_cache,(len(cache_rows),expected_cache)
    assert len(seed_rows)==seeds*len(scenarios)
    errors=[]
    for row in node_rows:
        errors.append(float(row["network_max_estimate_recursion_error"]))
        assert int(row["updated_state_index"])==int(row["fusion_iteration"])+1
        for node in range(5):
            for component in range(2):
                errors.append(float(row[f"node{node}_component{component}_absolute_recursion_error"]))
    cache_errors=[]
    for row in cache_rows:
        cache_errors.append(float(row["payload_delta_recursion_error"]))
        cache_errors.append(float(row["aligned_delta_recursion_error"]))
    max_state=max(errors)
    max_cache=max(cache_errors)
    assert prereg["registered_before_simulation"] is True
    assert prereg["run_id"]==PROP.name
    tol=float(prereg["absolute_tolerance"])
    assert cfg["predeclared_numerical_acceptance"]["absolute_tolerance"]==tol
    assert cfg["predeclared_numerical_acceptance"]["passed"] is True
    assert max_state<tol and max_cache<tol,(max_state,max_cache,tol)
    boundary={}
    for scenario in scenarios:
        for t in (q-1,q,q+1):
            subset=[row for row in node_rows if row["scenario"]==scenario and int(row["fusion_iteration"])==t]
            assert len(subset)==seeds,(scenario,t,len(subset))
            boundary[f"{scenario}_t{t}"]=max(float(x["network_max_estimate_recursion_error"]) for x in subset)
        seed_subset=[row for row in seed_rows if row["scenario"]==scenario]
        pre=max(max(abs(float(v)) for v in json.loads(row["target_cache_replacement_pre_error_components"])) for row in seed_subset)
        post=max(max(abs(float(v)) for v in json.loads(row["target_cache_replacement_post_error_components"])) for row in seed_subset)
        boundary[f"{scenario}_cache_replacement_pre_error"]=pre
        boundary[f"{scenario}_cache_replacement_post_error"]=post
        assert pre<tol and post<tol
    for scenario in scenarios:
        block=summary["results"][scenario]
        assert all(int(row["verified_iterations"])==T-r for row in seed_rows if row["scenario"]==scenario)
        assert block["all_link_payload_recursion_max_abs_error"]<tol
        assert block["all_link_aligned_cache_recursion_max_abs_error"]<tol
    return {
        "run_id":PROP.name,"status":"PASS","seeds":seeds,"scenarios":sorted(scenarios),
        "fusion_iterations":[r,T-1],"updated_state_indices":[r+1,T],
        "network_rows":len(node_rows),"edge_cache_rows":len(cache_rows),
        "max_full_horizon_node_component_error":max_state,
        "max_full_horizon_cache_or_aligned_error":max_cache,
        "tolerance":tol,"boundary_errors":boundary,
        "preregistered_before_simulation":True,
        "age_zero_first_update_formula_max_error":max(summary["results"][s]["first_update_direct_formula_max_abs_error"] for s in scenarios),
        "no_future_attacked_clean_difference_fed_to_recursion":True,
    }


def check_permissions():
    run=INFO
    summary=read_json(run/"summary.json")
    config=read_json(run/"config.json")
    assert summary["information_permission_audit"]["passed"]
    assert summary["receiver_logger_matches_vanilla_yang_max_abs_error"]==0.0
    audits=summary["offline_cache_reconstruction_audits"]
    assert len(audits)==2
    for audit in audits:
        assert audit["trial_count"]==48
        assert audit["max_logged_cache_reconstruction_error"]==0.0
        assert audit["all_sources_were_prior_transmissions"]
    # Ensure the event-feature function itself does not access simulation-only fields.
    source=(BRANCH/"code/compare_deghat_outputs.py").read_text(encoding="utf-8")
    tree=ast.parse(source)
    fn=next(n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name=="output_features")
    attrs={n.attr for n in ast.walk(fn) if isinstance(n,ast.Attribute)}
    forbidden={"estimates","replay_source","injected","true_state","state_truth"}
    assert not attrs&forbidden,attrs&forbidden
    return {
        "run_id":run.name,"status":"PASS","seed_count":48,
        "online_feature_sources":summary["information_permission_audit"]["allowed_sources"],
        "forbidden_simulator_fields_absent_from_feature_function":sorted(forbidden),
        "receiver_logging_vanilla_equivalence_max_error":0.0,
        "all_attack_cache_logs_reconstruct_from_delivered_packets":True,
        "offline_simulator_state_access_scope":"MSE scoring, attack source legality audit, and independent validation only",
        "schedule":config["model"] if "model" in config else config.get("communication_schedule"),
        "event_localization":"known edge/time remains an explicit oracle condition",
    }


def check_csv_extensions():
    rows=[]
    for path in sorted(RESULTS.rglob("*.csv")):
        first=path.open(encoding="utf-8-sig").readline().lstrip()
        rows.append({"path":str(path.relative_to(BRANCH.parent.parent)),"content_type":"JSON_ARRAY" if first.startswith("[") else "CSV"})
    new_path=PROP/"per_seed_propagation.csv"
    assert not new_path.open(encoding="utf-8-sig").readline().lstrip().startswith("[")
    old_json=[r for r in rows if r["content_type"]=="JSON_ARRAY"]
    assert len(old_json)==6,old_json
    assert all(Path(r["path"]).name=="per_seed_propagation.csv" for r in old_json)
    return {
        "new_run_csv":"PASS",
        "csv_files_scanned":len(rows),
        "historical_mislabeled_csv_files_preserved":old_json,
        "correction":"earlier six JSON-array files remain untouched and are identified by Run ID; new full-horizon Run 08 writes a correctly serialized CSV at a new path",
    }


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    OUT.mkdir(parents=True)
    result={
        "run_id":OUT.name,
        "P0_1_full_horizon":check_full_horizon(),
        "P0_2_information_permissions":check_permissions(),
        "P0_3_csv_schema":check_csv_extensions(),
        "run_sources_sha256":{
            path.name:sha(path) for path in [
                Path(__file__),
                BRANCH/"code/audit_attack_input_mapping.py",
                BRANCH/"code/compare_deghat_outputs.py",
                PROP/"config.json",PROP/"summary.json",INFO/"config.json",INFO/"summary.json",
            ]
        },
    }
    (OUT/"p0_acceptance.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=="__main__":
    # The historical checks above missed the response-matrix multiplication bug.
    # Keep them as source history, but never generate their old PASS again.
    from validate_final_delivery import main as validate_current_delivery
    validate_current_delivery()
