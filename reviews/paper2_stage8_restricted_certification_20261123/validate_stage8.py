"""Validate Stage 8 deterministic restricted-search replay outputs."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

HERE=Path(__file__).resolve().parent
STAGE7=HERE.parent/"paper2_stage7_fixed_amplitude_20261122"


def read(path):return json.loads(Path(path).read_text(encoding="utf8"))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    data=read(HERE/"restricted_replay_results.json")
    protocol=read(HERE/"stage8_protocol.json")
    unit=read(HERE/"restricted_checks.json")
    checks=[]
    def ok(name,value):
        checks.append({"name":name,"pass":bool(value)})
        if not value:raise AssertionError(name)
    rows=data["queries"]
    ok("deterministic_restricted_search_checks_pass",unit["status"]=="PASS" and unit["check_count"]>=14)
    ok("all_preselected_queries_present",len(rows)==9 and
       [x["episode"] for x in rows]==protocol["selected_episodes"])
    ok("all_full_searches_certified",all(x["full"]["certified"] for x in rows))
    ok("all_restricted_searches_certified",all(x["restricted"]["certified"] for x in rows))
    ok("full_and_restricted_decisions_match",all(x["decision_match"] for x in rows))
    ok("restricted_matches_saved_stage7_decision",all(x["restricted_matches_original"] for x in rows))
    ok("no_witness_and_witness_decisions_match",all(x["witnessless_matches_witnessed"] for x in rows))
    ok("correction_vectors_match",all(x["full"]["correction"]==x["restricted"]["correction"] for x in rows))
    ok("guaranteed_gains_match",all(x["full"]["guaranteed_gain"]==x["restricted"]["guaranteed_gain"] for x in rows))
    ok("restricted_likelihood_calls_lower",data["sum_restricted_likelihood_evaluations"]<data["sum_full_likelihood_evaluations"])
    ok("restricted_intervals_lower",sum(x["restricted_segments_tested"] for x in rows)<sum(x["full_segments_tested"] for x in rows))
    files=[]
    for name in protocol["selected_episodes"]:
        path=STAGE7/"results"/"fresh_confirmation"/f"b0.25_episode{name:03d}.json"
        files.append({"name":path.name,"sha256":sha(path)})
    out={"status":"PASS","check_count":len(checks),"checks":checks,
         "base_commit":protocol["base_stage7_commit"],
         "stage7_fresh_freeze_sha256":sha(STAGE7/"fresh_confirmation_freeze.json"),
         "stage7_input_trace_hashes":files,
         "stage8_source_hashes":{name:sha(HERE/name) for name in
             ("restricted_certification.py","check_restricted.py","replay_stage7_queries.py","stage8_protocol.json")},
         "new_random_samples":False,"episodes":len(rows),
         "sum_full_likelihood_evaluations":data["sum_full_likelihood_evaluations"],
         "sum_restricted_likelihood_evaluations":data["sum_restricted_likelihood_evaluations"],
         "sum_full_segments":sum(x["full_segments_tested"] for x in rows),
         "sum_restricted_segments":sum(x["restricted_segments_tested"] for x in rows),
         "mean_full_seconds":data["mean_full_seconds"],
         "mean_restricted_seconds":data["mean_restricted_seconds"],
         "mean_of_query_speedups":data["mean_speedup"],
         "ratio_of_mean_seconds":data["mean_full_seconds"]/data["mean_restricted_seconds"],
         "diagnostic_witness_evaluations":data["sum_witnessed_likelihood_evaluations"]-
             data["sum_restricted_likelihood_evaluations"]}
    (HERE/"stage8_validation.json").write_text(json.dumps(out,indent=2)+"\n",encoding="utf8",newline="\n")
    print(json.dumps({k:v for k,v in out.items() if k not in ("checks","stage7_input_trace_hashes","stage8_source_hashes")},indent=2))


if __name__=="__main__":main()
