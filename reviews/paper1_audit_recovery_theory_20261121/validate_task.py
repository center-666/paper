"""Final integrity checks for the theory and recovery-trial delivery."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
TRIAL = HERE / "recovery_trial"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf8"))


def main() -> None:
    checks: list[dict[str, object]] = []

    def check(name: str, ok: bool, detail: object = None) -> None:
        checks.append({"name": name, "pass": bool(ok), "detail": detail})
        if not ok:
            raise AssertionError(f"{name}: {detail}")

    frozen = load(TRIAL / "freeze.json")
    protocol = load(TRIAL / "protocol.json")
    preflight = load(TRIAL / "preflight.json")
    pre_sampling = load(TRIAL / "pre_sampling_validation.json")
    runtime = load(TRIAL / "execution_runtime.json")
    primary = load(TRIAL / "results" / "run_v1" / "manifest.json")
    protected = load(TRIAL / "results" / "run_v1" / "protected_file_check.json")
    diagnostic_freeze = load(TRIAL / "diagnostic_freeze.json")
    diagnostic = load(TRIAL / "results" / "run_v1_diagnostic" / "manifest.json")
    diagnostic_protected = load(TRIAL / "results" / "run_v1_diagnostic" / "protected_file_check.json")
    formula_checks = load(HERE / "formula_checks.json")

    check("frozen_trial_code_hash", sha(TRIAL / "run_trial.py") == frozen["recovery_trial_code_sha256"])
    check("frozen_protocol_hash", sha(TRIAL / "protocol.json") == frozen["protocol_sha256"])
    check("frozen_preflight_hash", sha(TRIAL / "preflight.json") == frozen["preflight_sha256"])
    check("preflight_pass", preflight["status"] == "PASS")
    check("pre_sampling_deterministic_checks", pre_sampling["status"] == "PASS" and len(pre_sampling["checks"]) == 17)
    check("actual_runtime_recorded", runtime["sampling_started"] is False and runtime["actual_runtime"]["numpy"] == "2.4.6")
    check("protocol_case_count", len(protocol["models"]) * len(protocol["attack_bounds"]) * len(protocol["attack_policies"]) == 8)
    check("all_episodes_run", primary["random_simulation_run"] and primary["episodes_per_case"] == 20000 and primary["model_runs"] == 8)
    check("primary_summary_hash", sha(TRIAL / "results" / "run_v1" / "summary.json") == primary["summary_sha256"])
    check("primary_protected_files_unchanged", protected["pass"] and not protected["changed"])
    check("diagnostic_is_reporting_only", diagnostic_freeze["diagnostic_code_sha256"] == sha(TRIAL / "run_trial_diagnostic.py")
          and diagnostic_freeze["independent_new_replication"] is False)
    check("diagnostic_result_hash", sha(TRIAL / "results" / "run_v1_diagnostic" / "summary.json") == diagnostic["summary_sha256"])
    check("diagnostic_protected_files_unchanged", diagnostic_protected["pass"] and not diagnostic_protected["changed"])
    check("formula_checks_pass", formula_checks["status"] == "PASS" and all(c["pass"] for c in formula_checks["checks"]))
    check("conditional_risk_note_present", (HERE / "04_conditional_risk_identity.md").is_file())
    check("trial_report_present", (TRIAL / "results" / "run_v1" / "results_analysis.md").is_file())
    check("trial_interpretation_present", (TRIAL / "trial_interpretation.md").is_file())
    repo = HERE.parents[1]
    scope = HERE.relative_to(repo).as_posix() + "/"
    old_hashes = load(TRIAL / "protected_before.json")
    current_changes = [name for name, digest in old_hashes.items()
                       if not name.startswith(scope)
                       and (not (repo / name).is_file() or sha(repo / name) != digest)]
    check("current_files_outside_task_unchanged", not current_changes, current_changes)
    missing_links = []
    for doc in HERE.rglob("*.md"):
        for target in re.findall(r"\]\(([^)]+)\)", doc.read_text(encoding="utf8")):
            if "://" in target or target.startswith("#"):
                continue
            if not (doc.parent / target.split("#")[0]).exists():
                missing_links.append({"document": str(doc.relative_to(HERE)), "target": target})
    check("local_document_links_resolve", not missing_links, missing_links)

    result = {
        "status": "PASS",
        "check_count": len(checks),
        "random_simulations": 8,
        "episodes_per_case": protocol["episodes"],
        "source_manuscript_modified": False,
        "checks": checks,
    }
    (HERE / "delivery_validation.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf8", newline="\n",
    )
    print(json.dumps({"status": result["status"], "check_count": len(checks), "source_manuscript_modified": False}))


if __name__ == "__main__":
    main()
