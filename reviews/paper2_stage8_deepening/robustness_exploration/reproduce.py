from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

TASK = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    subprocess.run(
        [sys.executable, "-B", str(TASK / "run_exploration.py"), "check"],
        cwd=TASK.parents[2],
        check=True,
    )
    for phase in ("drift", "model_mismatch"):
        subprocess.run(
            [sys.executable, "-B", str(TASK / "run_exploration.py"), phase,
             "--workers", str(args.workers)],
            cwd=TASK.parents[2],
            check=True,
        )
    subprocess.run(
        [sys.executable, "-B", str(TASK / "rebuild_report.py")],
        cwd=TASK.parents[2],
        check=True,
    )


if __name__ == "__main__":
    main()
