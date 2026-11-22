"""Freeze deterministic adjoint-cache equivalence replay."""
import hashlib, json
from pathlib import Path
HERE = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    target = HERE / "stage7_cached_freeze.json"
    if target.exists():
        raise SystemExit("Cached replay already frozen")
    base = json.loads((HERE / "stage7_freeze.json").read_text(encoding="utf8"))
    checks = json.loads((HERE / "direction_cache_checks.json").read_text(encoding="utf8"))
    assert checks["status"] == "PASS"
    assert base["random_samples_generated"] is False
    assert len(list((HERE / "results" / "replay").glob("b*_episode*.json"))) == 36
    sources = [HERE / "direction_cache.py", HERE / "check_direction_cache.py",
               HERE / "replay_stage6_cached.py"]
    record = {"identity": "Stage 7 cached direction replay equivalence",
              "stage7_original_freeze_sha256": sha(HERE / "stage7_freeze.json"),
              "original_paired_replay_summary_sha256": sha(HERE / "analysis" / "replay_summary.json"),
              "direction_cache_check_sha256": sha(HERE / "direction_cache_checks.json"),
              "sources": {p.name: sha(p) for p in sources},
              "cached_replay_random_samples": False,
              "purpose": "performance/equivalence validation only; same 36 frozen traces"}
    target.write_text(json.dumps(record, indent=2)+"\n", encoding="utf8", newline="\n")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
