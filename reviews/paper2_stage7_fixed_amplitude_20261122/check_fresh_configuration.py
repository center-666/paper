"""Pre-sample checks for the locked fresh confirmation protocol."""
import hashlib, json
from pathlib import Path
HERE=Path(__file__).resolve().parent
STAGE6=HERE.parent/"paper2_stage6_vector_correction_20261122"


def main():
    p=json.loads((HERE/"fresh_protocol.json").read_text(encoding="utf8"))
    old=json.loads((STAGE6/"pilot_protocol.json").read_text(encoding="utf8"))
    assert p["seed"] not in (old["screen_seed"],old["final_seed"])
    assert p["attack_strengths"]==old["attack_strengths"]
    assert p["attack_start"]==old["attack_start"]
    assert p["evaluation_windows"]==old["evaluation_windows"]
    assert p["certification_times"]==old["certification_times"]
    assert p["confidence_failure"]==old["confidence_failure"]
    assert p["max_refinement_nodes_per_query"]==old["max_refinement_nodes_per_query"]
    assert p["output_l1_cap"]==old["output_l1_cap"]
    assert p["episodes_per_case"]==old["final_episodes_per_case"]==12
    assert p["full_certificate_search"] is True and p["tuning_after_freeze"] is False
    for f in ("deterministic_checks.json","direction_cache_corrected_checks.json"):
        assert json.loads((HERE/f).read_text(encoding="utf8"))["status"]=="PASS"
    assert json.loads((HERE/"analysis"/"replay_summary.json").read_text(encoding="utf8"))["status"]=="PASS_REPRODUCED"
    assert json.loads((HERE/"analysis"/"cache_equivalence.json").read_text(encoding="utf8"))["status"]=="PASS"
    assert not list((HERE/"results"/"fresh_confirmation").glob("*.json")) if (HERE/"results"/"fresh_confirmation").exists() else True
    out={"status":"PASS","fresh_seed":p["seed"],"stage6_seeds":[old["screen_seed"],old["final_seed"]],
         "cases":p["attack_strengths"],"episodes_per_case":p["episodes_per_case"],
         "schedule_unchanged":True,"full_certificate_search":True,"random_samples_generated":False,
         "source_sha256":hashlib.sha256((HERE/"fresh_confirmation.py").read_bytes()).hexdigest()}
    (HERE/"fresh_configuration_checks.json").write_text(json.dumps(out,indent=2)+"\n",encoding="utf8",newline="\n")
    print(json.dumps(out))


if __name__=="__main__":main()
