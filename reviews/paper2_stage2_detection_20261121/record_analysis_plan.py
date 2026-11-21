"""Record supplementary information-bound analysis before confirmation data."""
from pathlib import Path
import json
from run_experiment import sha, write

HERE = Path(__file__).resolve().parent
if (HERE / "results" / "final").exists():
    raise SystemExit("Final data already started; cannot label this pre-confirmation")
write(HERE / "supplementary_analysis_plan.json", {
    "stage": "AFTER_SCREEN_STARTED_BEFORE_FINAL_SAMPLING",
    "not_part_of_original_attachment": True,
    "performance_inputs_changed": False,
    "scope": "all 24 final cases x 3 horizons, no subset selection",
    "method": "bounded empirical Bernstein on per-episode summed conditional KL, then binary data processing",
    "confidence_family_failure_probability": 0.05,
    "cells": 72,
    "per_cell_failure_probability": 0.05/72,
    "required_samples": 50000,
    "information_record": "trusted event history, deterministic covariance labels; no payload, phase, or codewords",
    "sources": {name:sha(HERE/name) for name in
                ("information_upper_bounds.py","information_upper_constants.json",
                 "04_information_upper_bound.md","analyze.py")},
    "notes": "Analytic bounds remain separate from sample-based confidence refinements; final seeds do not overlap screen.",
})
print("Supplementary analysis plan recorded before confirmation.")
