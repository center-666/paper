"""Final integrity checks for the Stage 7 research package."""
import hashlib, json
from pathlib import Path
HERE=Path(__file__).resolve().parent
STAGE6=HERE.parent/"paper2_stage6_vector_correction_20261122"


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding="utf8"))


def main():
    checks=[]
    def ok(name,value):
        checks.append({"name":name,"pass":bool(value)})
        if not value:raise AssertionError(name)
    fixed=read(HERE/"deterministic_checks.json")
    cache=read(HERE/"direction_cache_corrected_checks.json")
    replay=read(HERE/"analysis"/"replay_summary.json")
    equivalent=read(HERE/"analysis"/"cache_equivalence.json")
    completion=read(HERE/"results"/"fresh_confirmation_completion.json")
    fresh=read(HERE/"analysis"/"fresh_confirmation_summary.json")
    response_audit=read(HERE/"analysis"/"fresh_response_audit.json")
    core_freeze=read(HERE/"stage7_freeze.json")
    cache_freeze=read(HERE/"stage7_corrected_freeze.json")
    fresh_freeze=read(HERE/"fresh_confirmation_freeze.json")
    ok("exact_interval_deterministic_checks",fixed["status"]=="PASS" and fixed["check_count"]>=10000)
    ok("adjoint_cache_deterministic_checks",cache["status"]=="PASS" and cache["one_sided_checks"]>=1000)
    ok("stage6_old_branch_replayed_exactly",replay["max_stage6_old_branch_reproduction_error"]==0)
    ok("direct_and_cached_outputs_match",equivalent["status"]=="PASS" and
       all(v==0 for v in equivalent["max_absolute_output_difference"].values()))
    ok("all_36_frozen_replay_episodes_present",len(list((HERE/"results"/"replay").glob("b*_episode*.json")))==36)
    ok("all_36_corrected_cache_episodes_present",len(list((HERE/"results"/"replay_cached_corrected").glob("b*_episode*.json")))==36)
    ok("fresh_full_search_completed",completion["status"]=="PASS" and completion["episodes"]==36 and not completion["failures"])
    ok("fresh_summary_has_all_cases",set(fresh["cases"])=={"0.0","0.1","0.25"})
    ok("fresh_sample_seed_is_new",fresh["seed"] not in (202611226601,202611226602))
    ok("all_fresh_true_responses_inside_outward_intervals",response_audit["status"]=="PASS" and
       response_audit["true_onset_interval_step_checks"]==18432 and
       response_audit["all_successful_certificate_margins_nonnegative"])
    ok("all_successful_constraints_checked",response_audit["successful_certificate_truth_constraints"]==37)
    ok("fresh_confidence_protocol_is_frozen",fresh_freeze["random_samples_generated"] is False and fresh_freeze["tuning_after_freeze"] is False)
    for name,digest in core_freeze["stage7_sources"].items():
        ok("core_source_hash:"+name,sha(HERE/name)==digest)
    for name,digest in cache_freeze["sources"].items():
        ok("cache_source_hash:"+name,sha(HERE/name)==digest)
    for name,digest in fresh_freeze["stage7_sources"].items():
        ok("fresh_source_hash:"+name,sha(HERE/name)==digest)
    for name,digest in fresh_freeze["stage6_inputs"].items():
        ok("stage6_input_hash:"+name,sha(STAGE6/name)==digest)
    baseline_hashes=core_freeze["stage6_final_trace_manifest"]
    for name,digest in baseline_hashes.items():
        ok("stage6_frozen_trace_hash:"+name,sha(STAGE6/"results_v2"/"final"/name)==digest)
    out={"status":"PASS","check_count":len(checks),"checks":checks,
         "stage6_paired_replay_episodes":36,"fresh_independent_episodes":36,
         "fresh_seed":fresh["seed"],"strong_attack_successful_certificate_episodes":fresh["cases"]["0.25"]["successful_certificate_episodes"]["k"],
         "strong_attack_lag50_useful_episodes":fresh["cases"]["0.25"]["lag_summary"]["50"]["new_useful_episode_rate"]["k"],
         "exact_response_interval_step_checks":response_audit["true_onset_interval_step_checks"],
         "successful_certificate_truth_constraints":response_audit["successful_certificate_truth_constraints"],
         "formal_manuscript_modified":False}
    (HERE/"delivery_validation.json").write_text(json.dumps(out,indent=2)+"\n",encoding="utf8",newline="\n")
    print(json.dumps({k:v for k,v in out.items() if k!="checks"},indent=2))


if __name__=="__main__":main()
