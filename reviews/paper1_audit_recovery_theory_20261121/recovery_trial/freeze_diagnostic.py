"""Freeze a reporting-only rerun that adds uncertainty for the drift identity."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    original = (HERE / "run_trial.py").read_text(encoding="utf8")
    diagnostic_path = HERE / "run_trial_diagnostic.py"
    diagnostic = diagnostic_path.read_text(encoding="utf8")
    expected = original.replace(
        'OUT=HERE/"results/run_v1"', 'OUT=HERE/"results/run_v1_diagnostic"'
    )
    expected = expected.replace(
        '        "score_minus_predicted_drift_attack":float(np.mean(audit_sum_a-predicted_drift_sum_a)),\n',
        '        "score_minus_predicted_drift_attack":float(np.mean(audit_sum_a-predicted_drift_sum_a)),\n'
        '        "score_minus_predicted_drift_attack_se":float(np.std(audit_sum_a-predicted_drift_sum_a,ddof=1)/np.sqrt(n)),\n',
    )
    expected = expected.replace(
        '    if codehash!=frozen["recovery_trial_code_sha256"]:\n'
        '        raise SystemExit("Recovery trial code differs from pre-sampling freeze")\n',
        '    frozen_codehash=sha(HERE/"run_trial.py")\n'
        '    if frozen_codehash!=frozen["recovery_trial_code_sha256"]:\n'
        '        raise SystemExit("Original recovery trial code differs from pre-sampling freeze")\n',
    )
    if diagnostic != expected:
        raise AssertionError("Diagnostic script contains changes beyond output path and residual SE")
    frozen = json.loads((HERE / "freeze.json").read_text(encoding="utf8"))
    protocol_hash = sha(HERE / "protocol.json")
    original_hash = sha(HERE / "run_trial.py")
    if original_hash != frozen["recovery_trial_code_sha256"]:
        raise AssertionError("Original code no longer matches the frozen trial")
    if protocol_hash != frozen["protocol_sha256"]:
        raise AssertionError("Protocol no longer matches the frozen trial")
    out = HERE / "results" / "run_v1_diagnostic"
    if out.exists():
        raise AssertionError("Diagnostic output already exists")
    result = {
        "stage": "FROZEN_BEFORE_DIAGNOSTIC_RERUN",
        "purpose": "Estimate standard errors for the per-episode audit-score minus predicted-drift identity residual",
        "original_frozen_code_sha256": original_hash,
        "protocol_sha256": protocol_hash,
        "diagnostic_code_sha256": sha(diagnostic_path),
        "diagnostic_change": "adds only the across-episode SE of the already reported drift residual and writes to a separate output directory",
        "same_protocol_and_master_seed": True,
        "independent_new_replication": False,
        "random_samples_generated": False,
    }
    (HERE / "diagnostic_freeze.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf8", newline="\n"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
