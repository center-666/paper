from __future__ import annotations

from pathlib import Path
import subprocess
import sys

TASK = Path(__file__).resolve().parent
REPO = TASK.parents[2]


def main():
    for scenario in ("eps_+5.00%", "eps_-5.00%"):
        subprocess.run(
            [sys.executable, "-B", str(TASK / "run_exploration.py"),
             "model_mismatch", "--scenario", scenario, "--index-start", "0",
             "--index-stop", "2", "--workers", "6"],
            cwd=REPO,
            check=True,
        )
    subprocess.run(
        [sys.executable, "-B", str(TASK / "rebuild_report_final.py")],
        cwd=REPO,
        check=True,
    )


if __name__ == "__main__":
    main()

