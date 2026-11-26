from __future__ import annotations

from pathlib import Path
import subprocess
import sys

TASK = Path(__file__).resolve().parent
REPO = TASK.parents[2]
SCENARIOS = (
    "eps_+0.00%",
    "eps_+1.00%",
    "eps_-1.00%",
    "eps_+2.00%",
    "eps_-2.00%",
    "eps_+5.00%",
    "eps_-5.00%",
)
GROUPS = ("health", "strong_positive", "strong_negative")


def run(*args):
    subprocess.run(
        [sys.executable, "-B", str(TASK / "run_exploration.py"), *args],
        cwd=REPO,
        check=True,
    )


def main():
    run("check")
    for scenario in ("eps_+5.00%",):
        for group in GROUPS:
            for start, stop in ((0, 6), (6, 12)):
                run(
                    "model_mismatch",
                    "--workers", "6",
                    "--scenario", scenario,
                    "--group", group,
                    "--index-start", str(start),
                    "--index-stop", str(stop),
                )
    subprocess.run(
        [sys.executable, "-B", str(TASK / "rebuild_report_final.py")],
        cwd=REPO,
        check=True,
    )


if __name__ == "__main__":
    main()


