"""Freeze corrected cached replay implementation before deterministic traces."""
import hashlib, json
from pathlib import Path
HERE = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    target = HERE / "stage7_corrected_freeze.json"
    if target.exists():
        raise SystemExit("Corrected cache replay already frozen")
    check = json.loads((HERE / "direction_cache_corrected_checks.json").read_text(encoding="utf8"))
    assert check["status"] == "PASS" and check["direction_key_synchrony"]
    sources = [HERE / "direction_cache_corrected.py", HERE / "check_direction_cache_corrected.py",
               HERE / "replay_stage6_corrected.py"]
    record = {"identity": "Stage 7 corrected synchronized direction cache replay",
              "prior_frozen_replay_sha256": sha(HERE / "stage7_freeze.json"),
              "deterministic_check_sha256": sha(HERE / "direction_cache_corrected_checks.json"),
              "sources": {p.name: sha(p) for p in sources},
              "input_frozen_trace_manifest_sha256": sha(HERE / "stage7_freeze.json"),
              "new_random_samples": False,
              "purpose": "validate exact output equivalence and incremental support runtime"}
    target.write_text(json.dumps(record, indent=2)+"\n", encoding="utf8", newline="\n")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
