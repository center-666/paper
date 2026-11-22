"""Freeze the one-sided-cache equivalence replay."""
import hashlib, json
from pathlib import Path
HERE = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    target = HERE / "stage7_fast_freeze.json"
    if target.exists():
        raise SystemExit("Fast replay already frozen")
    checks = json.loads((HERE / "direction_cache_fast_checks.json").read_text(encoding="utf8"))
    assert checks["status"] == "PASS"
    stage7 = json.loads((HERE / "stage7_freeze.json").read_text(encoding="utf8"))
    sources = [HERE / "direction_cache_fast.py", HERE / "check_direction_cache_fast.py",
               HERE / "replay_stage6_fast.py"]
    record = {"identity": "Stage 7 one-sided support-cache replay",
              "stage7_freeze_sha256": sha(HERE / "stage7_freeze.json"),
              "direction_cache_check_sha256": sha(HERE / "direction_cache_fast_checks.json"),
              "sources": {p.name: sha(p) for p in sources},
              "same_frozen_traces_sha256": stage7["stage6_final_trace_manifest"],
              "new_random_samples": False,
              "purpose": "check output equivalence and online support-cache cost"}
    target.write_text(json.dumps(record, indent=2)+"\n", encoding="utf8", newline="\n")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
