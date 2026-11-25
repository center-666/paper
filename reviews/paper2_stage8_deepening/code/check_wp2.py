"""WP2 deterministic checks for safe disk geometry and hard safety guards."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
from corrector import safe_disk_corrector, safety_margin

ROOT = Path(__file__).resolve().parents[1]

def main():
    weight = np.eye(2)
    responses = {0: np.array([1.0, 0.0]), 1: np.array([0.0, 1.0])}
    positive = safe_disk_corrector({0: (0.25, 0.25), 1: (0.25, 0.25)}, responses, weight,
                                  np.array([0.25, 0.25]), margin=0.0, cap=1.0)
    zero = safe_disk_corrector({0: (-0.25, 0.25)}, responses, weight,
                               np.array([0.25, 0.25]), margin=0.0, cap=1.0)
    separated = safe_disk_corrector({0: (0.20, 0.25), 1: (0.20, 0.25)}, responses,
                                    weight, np.array([0.25, 0.25]), margin=0.0, cap=1.0)
    assert positive.zero_reason is None
    assert zero.zero_reason == "ZERO_IN_INTERVAL"
    assert separated.zero_reason is None
    assert positive.margin >= -1e-9 and separated.margin >= -1e-9
    result = {"status": "PASS", "positive": positive.__dict__, "zero_interval": zero.__dict__,
              "separated": separated.__dict__,
              "claim": "returned action satisfies every endpoint safety constraint within 1e-9"}
    (ROOT / "results" / "wp2_checks.json").write_text(json.dumps(result, indent=2, default=lambda x: x.tolist()) + "\n", encoding="utf8")
    print(json.dumps(result, indent=2, default=lambda x: x.tolist()))

if __name__ == "__main__": main()
