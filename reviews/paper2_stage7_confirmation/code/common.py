"""Shared immutable inputs and point-score helpers for Stage 7 confirmation."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path


HERE = Path(__file__).resolve().parent
TASK = HERE.parent
REVIEWS = TASK.parent
STAGE6 = REVIEWS / "paper2_stage6_vector_correction_20261122"
STAGE7 = REVIEWS / "paper2_stage7_fixed_amplitude_20261122"

import sys
sys.path.insert(0, str(STAGE6))



def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _log_trigger_float(value, z):
    exponent = -0.5 * z * value * value
    if exponent == 0.0:
        return -math.inf
    return math.log(-math.expm1(exponent))


def source_hashes():
    names = {
        "stage6_model": STAGE6 / "model.json",
        "stage6_vector_record": STAGE6 / "vector_record.py",
        "stage6_exact_linear": STAGE6 / "exact_linear.py",
        "stage6_pilot": STAGE6 / "pilot_v2.py",
        "stage6_projection": STAGE6 / "projection.py",
        "stage7_fixed_amplitude": STAGE7 / "fixed_amplitude.py",
        "stage7_direction_cache": STAGE7 / "direction_cache_corrected.py",
        "stage7_protocol": STAGE7 / "fresh_protocol.json",
    }
    return {key: sha(path) for key, path in names.items()}
