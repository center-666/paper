"""Freeze Stage 7's independent full-search confirmation before sampling."""
import hashlib, json
from pathlib import Path
HERE=Path(__file__).resolve().parent
STAGE6=HERE.parent/"paper2_stage6_vector_correction_20261122"


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    target=HERE/"fresh_confirmation_freeze.json"
    if target.exists():raise SystemExit("Fresh confirmation already frozen")
    check=json.loads((HERE/"fresh_configuration_checks.json").read_text(encoding="utf8"))
    assert check["status"]=="PASS" and not check["random_samples_generated"]
    protocol=json.loads((HERE/"fresh_protocol.json").read_text(encoding="utf8"))
    result_dir=HERE/"results"/"fresh_confirmation"
    if result_dir.exists() and list(result_dir.glob("*.json")):
        raise SystemExit("Fresh samples already exist before freeze")
    source_names=("fresh_confirmation.py","fresh_protocol.json","check_fresh_configuration.py",
                  "direction_cache_corrected.py","fixed_amplitude.py")
    stage6_names=("model.json","pilot_protocol.json","freeze_v2.json","pilot_v2.py","vector_record.py")
    record={"identity":protocol["identity"],"seed":protocol["seed"],
            "episodes_per_case":protocol["episodes_per_case"],"attack_strengths":protocol["attack_strengths"],
            "stage6_inputs":{n:sha(STAGE6/n) for n in stage6_names},
            "stage7_sources":{n:sha(HERE/n) for n in source_names},
            "protocol_check_sha256":sha(HERE/"fresh_configuration_checks.json"),
            "stage7_core_freeze_sha256":sha(HERE/"stage7_freeze.json"),
            "corrected_cache_freeze_sha256":sha(HERE/"stage7_corrected_freeze.json"),
            "stage7_paired_replay_summary_sha256":sha(HERE/"analysis"/"replay_summary.json"),
            "cached_replay_equivalence_sha256":sha(HERE/"analysis"/"cache_equivalence.json"),
            "random_samples_generated":False,"full_certificate_search":True,
            "independent_of_stage6_final_seeds":True,"tuning_after_freeze":False}
    target.write_text(json.dumps(record,indent=2)+"\n",encoding="utf8",newline="\n")
    print(json.dumps(record,indent=2))


if __name__=="__main__":main()
