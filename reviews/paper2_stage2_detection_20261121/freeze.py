"""Freeze input hashes and preserve existing repository files before sampling."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import platform
import numpy as np
import scipy

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    if (HERE / "freeze.json").exists() or (HERE / "results").exists():
        raise SystemExit("Already frozen or results exist; refusing to rewrite history")
    inputs = ("core.py", "run_experiment.py", "protocol.json")
    evidence = ("detector_enumeration_checks.json", "error_coordinate_checks.json", "constants.json")
    for name in evidence:
        json.loads((HERE / name).read_text(encoding="utf8"))
    cmd = ["git", "-c", f"safe.directory={REPO.as_posix()}"]
    base = subprocess.check_output(cmd + ["rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    if not base.startswith("8cf49e73"):
        raise SystemExit("Unexpected baseline: " + base)
    paths = subprocess.check_output(cmd + ["ls-files", "-co", "--exclude-standard", "-z"], cwd=REPO).decode("utf8").split("\0")
    scope = HERE.relative_to(REPO).as_posix() + "/"
    protected = {p: sha(REPO / p) for p in paths if p and not p.startswith(scope)
                 and (REPO / p).is_file()}
    (HERE / "protected_before.json").write_text(json.dumps(protected, indent=2) + "\n", encoding="utf8")
    record = {
        "base_commit": base, "stage": "FROZEN_BEFORE_ANY_STAGE2_PERFORMANCE_SAMPLING",
        "input_hashes": {name: sha(HERE / name) for name in inputs},
        "deterministic_evidence_hashes": {name: sha(HERE / name) for name in evidence},
        "runtime": {"python": sys.version, "numpy": np.__version__, "scipy": scipy.__version__,
                    "platform": platform.platform()},
        "protected_count": len(protected),
        "random_performance_samples_generated": False,
        "screen_and_final_parameters_identical": True,
        "final_seed_independent_of_screen": True,
    }
    (HERE / "freeze.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf8")
    print(json.dumps(record, indent=2))

if __name__ == "__main__":
    main()
