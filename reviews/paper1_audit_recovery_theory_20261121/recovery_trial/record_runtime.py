"""Record the actual local runtime used for the frozen trial."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import platform
import sys

import numpy
import scipy

HERE = Path(__file__).resolve().parent


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    frozen = json.loads((HERE / "freeze.json").read_text(encoding="utf8"))
    result = {
        "sampling_started": False,
        "frozen_code_sha256": sha(HERE / "run_trial.py"),
        "frozen_protocol_sha256": sha(HERE / "protocol.json"),
        "pre_sampling_validation_sha256": sha(HERE / "pre_sampling_validation.json"),
        "freeze_record_expected_runtime": {
            "python": frozen["python"],
            "numpy": frozen["numpy"],
        },
        "actual_runtime": {
            "python": sys.version,
            "python_executable": sys.executable,
            "numpy": numpy.__version__,
            "scipy": scipy.__version__,
            "platform": platform.platform(),
        },
        "runtime_note": (
            "The frozen source and protocol are unchanged. The originally recorded Python 3.14.9 "
            "runtime is unavailable offline in this workspace, so this run uses the locally cached "
            "Python 3.11.18 environment; exact package versions are recorded above."
        ),
    }
    (HERE / "execution_runtime.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf8", newline="\n",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
