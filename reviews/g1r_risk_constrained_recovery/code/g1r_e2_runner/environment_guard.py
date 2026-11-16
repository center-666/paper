"""Live execution guard grounded only in immutable Task 5 and R12 records."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import platform
from pathlib import Path

import numpy as np
import scipy

CALIBRATION = "results/g1r_task5_calibration_20261115_r01/calibration_manifest.json"
R12 = "results/g1r_e2_runner_dryrun_20261115_r12/source_hashes.json"
REFERENCE_SHA256 = {
    CALIBRATION: "7ccd2a04d94e464a4f4b2b0ef67c134bbd3c613d73f08b95e1b0aa91663ee813",
    R12: "e715d11c3ab48e03e5fa81ddcc758d3f216753311c827369634f8b299f7a88cf",
}


class EnvironmentMismatch(RuntimeError):
    pass


def normalize_blas(text: str) -> str:
    # Calibration captured redirect_stdout(np.show_config()) without parsing.
    # Preserve all paths, compiler, architecture, ABI and BLAS/LAPACK fields.
    # Normalize line endings ONLY, identically for archived and live records.
    if not isinstance(text, str) or not text.strip():
        raise EnvironmentMismatch("missing BLAS configuration evidence")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def fingerprint(record: dict) -> dict:
    versions = {key: record[key] for key in ("python", "numpy", "scipy")}
    if not all(isinstance(v, str) and v for v in versions.values()):
        raise EnvironmentMismatch("incomplete environment version evidence")
    return {**versions,
            "blas_sha256": hashlib.sha256(normalize_blas(record["blas_configuration"]).encode("utf-8")).hexdigest(),
            "capture": "redirect_stdout(numpy.show_config())",
            "normalization": "line-endings-only-v1"}


def reference_environment(base: Path) -> dict:
    records = []
    for relative, digest in REFERENCE_SHA256.items():
        path = base / relative
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise EnvironmentMismatch(f"untrusted environment reference: {relative}")
        records.append(json.loads(path.read_text(encoding="utf-8")))
    ref = fingerprint(records[0])
    if ref != fingerprint(records[1]):
        raise EnvironmentMismatch("Task 5 and R12 environment evidence disagree; no baseline selected")
    return ref


def current_environment() -> dict:
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        np.show_config()
    return {"python": platform.python_version(), "numpy": np.__version__,
            "scipy": scipy.__version__, "blas_configuration": output.getvalue()}


def verify_environment(config) -> dict:
    reference = reference_environment(config.base)
    if dict(config.environment_fingerprint) != reference:
        raise EnvironmentMismatch("loaded experiment environment differs from verified reference")
    actual = fingerprint(current_environment())
    mismatches = [key for key in reference if actual.get(key) != reference[key]]
    if mismatches:
        raise EnvironmentMismatch("live environment mismatch: " + ", ".join(mismatches))
    return {"reference": reference, "actual": actual, "match": True,
            "sources_sha256": REFERENCE_SHA256.copy()}

