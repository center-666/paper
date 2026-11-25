"""Self-check the multi-gate replay on saved data before new-seed execution."""
import hashlib
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import extend


def main():
    temp = extend.protocol
    thresholds = extend.THRESHOLDS
    extend.protocol = lambda: {"cap": extend.BASE["strong"], "thresholds": thresholds, "onset": 50}
    count = 0
    for name in ("health-00", "strong_positive-00", "strong_negative-00"):
        row = extend.read(extend.TASK / "results/confirmation" / (name+".json"))
        group = list(extend.BASE["groups"]).index(row["group"])
        public, states = extend.record(extend.BASE["test_seed"], group, row["index"], row["b"])
        assert public == row["public"]
        result = extend.point_gates(row, states)
        assert result["original_M1_identical"]
        count += 1
    extend.protocol = temp
    original = subprocess.check_output(
        ["git", "diff", "--name-only", "240cb7ec", "--",
         "reviews/paper2_stage7_confirmation", "reviews/paper2_stage8_deepening/code",
         "reviews/paper2_stage8_deepening/config", "reviews/paper2_stage8_deepening/results",
         "reviews/paper2_stage8_deepening/registration.json"],
        cwd=extend.TASK, text=True)
    assert original.strip() == ""
    extend.save(extend.SUPPLEMENT / "checks.json", dict(
        existing_trajectory_checks=count,
        public_prefix_identical=True,
        original_M1_action_hash_identical=True,
        frozen_original_files_identical=True,
    ))
    print("Replay precheck passed", count)


if __name__ == "__main__":
    main()
