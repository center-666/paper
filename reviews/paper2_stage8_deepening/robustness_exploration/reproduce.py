from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

TASK = Path(__file__).resolve().parent


def run(*arguments):
    subprocess.run(
        [sys.executable, "-B", str(TASK / "run_exploration.py"), *arguments],
        cwd=TASK.parents[2],
        check=True,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    run("check")
    run("drift", "--workers", str(args.workers))
    for epsilon in ("eps_+0.00%", "eps_+1.00%", "eps_-1.00%",
                    "eps_+2.00%", "eps_-2.00%", "eps_+5.00%", "eps_-5.00%"):
        for group in ("health", "strong_positive", "strong_negative"):
            for start, stop in ((0, 6), (6, 12)):
                run(
                    "model_mismatch",
                    "--workers", str(args.workers),
                    "--scenario", epsilon,
                    "--group", group,
                    "--index-start", str(start),
                    "--index-stop", str(stop),
                )
    subprocess.run(
        [sys.executable, "-B", str(TASK / "rebuild_report_final.py")],
        cwd=TASK.parents[2],
        check=True,
    )


if __name__ == "__main__":
    main()
