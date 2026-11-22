"""Freeze the Stage 7 replay after deterministic checks and before replay."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
STAGE6 = HERE.parent / "paper2_stage6_vector_correction_20261122"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    freeze = HERE / "stage7_freeze.json"
    if freeze.exists():
        raise SystemExit("Stage 7 already frozen")
    check = json.loads((HERE / "deterministic_checks.json").read_text(encoding="utf8"))
    assert check["status"] == "PASS"
    assert check["performance_random_samples_generated"] is False
    protocol = json.loads((HERE / "stage7_protocol.json").read_text(encoding="utf8"))
    stage6_files = [STAGE6 / "model.json", STAGE6 / "pilot_protocol.json",
                    STAGE6 / "freeze_v2.json", STAGE6 / "pilot_v2.py"]
    stage6_results = sorted((STAGE6 / "results_v2" / "final").glob("b*_episode*.json"))
    assert len(stage6_results) == 36
    sources = [HERE / "fixed_amplitude.py", HERE / "check_fixed_amplitude.py",
               HERE / "replay_stage6.py", HERE / "stage7_protocol.json"]
    record = {
        "identity": protocol["identity"],
        "baseline_commit": protocol["baseline_commit"],
        "stage6_freeze_sha256": sha(STAGE6 / "freeze_v2.json"),
        "stage6_inputs": {p.name: sha(p) for p in stage6_files},
        "stage6_final_trace_manifest": {p.name: sha(p) for p in stage6_results},
        "stage7_sources": {p.name: sha(p) for p in sources},
        "deterministic_check_sha256": sha(HERE / "deterministic_checks.json"),
        "random_samples_generated": False,
        "certificate_queries_cached_from_same_stage6_final_episodes": 36,
        "confirmation_seeds": None,
        "confirmation_runs": False,
    }
    freeze.write_text(json.dumps(record, indent=2) + "\n", encoding="utf8", newline="\n")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
