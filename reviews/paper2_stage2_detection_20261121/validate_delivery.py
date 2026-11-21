"""Validate complete frozen runs, all summary denominators, provenance and scope."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re
import subprocess

from information_upper_bounds import analytic_bounds

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
NAMES = ("D0_Azuma", "D1_fixed_LR", "D2_strength_mixture",
         "D3_start_strength_mixture", "D4_finite_horizon_CUSUM", "oracle_matched_LR")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read(p):
    return json.loads(Path(p).read_text(encoding="utf8"))


def main():
    checks = []
    def check(name, condition, detail=None):
        checks.append({"name":name, "pass":bool(condition), "detail":detail})
        if not condition:
            raise AssertionError(f"{name}: {detail}")

    protocol = read(HERE/"protocol.json")
    frozen = read(HERE/"freeze.json")
    for name,digest in frozen["input_hashes"].items():
        check("frozen_performance_input_"+name, sha(HERE/name)==digest)
    for name,digest in frozen["deterministic_evidence_hashes"].items():
        check("frozen_deterministic_evidence_"+name, sha(HERE/name)==digest)
    extra = read(HERE/"deterministic_correction.json")
    check("supplement_original_restored", extra["original_constants_exactly_match_freeze"]
          and sha(HERE/"constants.json")==extra["original_constants_sha256"])
    check("supplement_source_hash",sha(HERE/"compute_actual_candidate_constants.py")==extra["supplement_generator_sha256"])
    check("supplement_constants_hash",sha(HERE/"constants_actual_candidate.json")==extra["supplement_constants_sha256"])
    parallel = read(HERE/"parallel_confirmation_manifest.json")
    check("parallel_driver_matches_record",sha(HERE/"parallel_confirmation.py")==parallel["script_sha256"])
    plan = read(HERE/"supplementary_analysis_plan.json")
    for name in ("information_upper_bounds.py","information_upper_constants.json","04_information_upper_bound.md"):
        check("preconfirmation_information_analysis_"+name,sha(HERE/name)==plan["sources"][name])
    # Reporting source may acquire wording/figure corrections after sampling;
    # any such change is transparent in this record, not a performance input.
    reporting_changes = {name: {"recorded":digest,"current":sha(HERE/name)}
                         for name,digest in plan["sources"].items()
                         if sha(HERE/name)!=digest}
    check("reporting_changes_do_not_touch_information_method",
          set(reporting_changes).issubset({"analyze.py"}), reporting_changes)
    for name in ("screen_seed","final_seed","health_screen_seed","health_final_seed"):
        check("unique_stream_"+name, list(protocol.values()).count(protocol[name])==1)

    all_cases = []
    for stage in ("screen","final"):
        n = protocol[stage+"_episodes_per_case"]
        case_paths = []
        for model in protocol["models"]:
            for b in protocol["attack_strengths"]:
                bounds = analytic_bounds(model,b)
                for onset in protocol["onsets"]:
                    path=HERE/"results"/stage/f"{model['id']}_b{b:g}_onset{onset}.json"
                    case=read(path)
                    case_paths.append(path)
                    all_cases.append(case)
                    if case["n"] != n or case["frozen_hash"] != sha(HERE/"freeze.json"):
                        raise AssertionError("Wrong denominator/provenance: "+path.name)
                    for H in protocol["horizons_after_onset"]:
                        s=case["statistics"][str(H)]
                        if s["monitor_total_MSE"]["n"]!=n:
                            raise AssertionError("Missing simulation outputs")
                        if not s["total_sends"]["mean"]<=H:
                            raise AssertionError("Send horizon mismatch")
                        if s["total_bias_energy"]["mean"] > H*bounds["analysis_bias_absolute_upper"]**2 + 1e-10:
                            raise AssertionError("Bias invariant violated")
                        if s["oracle_conditional_KL"]["mean"] > H*bounds["conditional_Bernoulli_KL_upper_per_step"]+1e-12:
                            raise AssertionError("Information range violated")
                        for name in NAMES:
                            false=s[name+"/pre_onset_alarm"]
                            eligible=s[name+"/detection_eligible"]
                            det=s[name+"/detection_unconditional"]
                            if eligible["n"]+round(false["sum"])!=n:
                                raise AssertionError("Survival denominator mismatch")
                            if round(det["sum"])!=round(eligible["sum"]):
                                raise AssertionError("Detection count changed with denominator")
                            if not 0<=s[name+"/restricted_delay_eligible"]["mean"]<=H:
                                raise AssertionError("Censoring horizon invalid")
                            if s[name+"/pre_MSE"]["mean"] > s["monitor_total_MSE"]["mean"]+1e-9:
                                raise AssertionError("Pre-alarm exceeds full loss")
                            if s[name+"/pre_bias_energy"]["mean"] > s["total_bias_energy"]["mean"]+1e-9:
                                raise AssertionError("Pre-alarm exceeds full bias energy")
                    for r in case["runtime_checks"]:
                        if not (math.isfinite(r["max_abs_prior_error"]) and
                                r["max_abs_bias"]<=bounds["analysis_bias_absolute_upper"]+1e-12):
                            raise AssertionError("Runtime range check failed")
        check(stage+"_all_24_cases_complete",len(case_paths)==24)
        check(stage+"_all_denominators_ranges_and_risk_interfaces",True,{"episodes_each":n,"cases":24})
    for stage in ("health_screen","health_final"):
        n = protocol["final_episodes_per_case" if stage.endswith("final") else "screen_episodes_per_case"]
        for model in protocol["models"]:
            case=read(HERE/"results"/stage/f"{model['id']}.json")
            check(stage+"_"+model["id"]+"_complete",case["n"]==n and
                  case["frozen_hash"]==sha(HERE/"freeze.json"))
            for H,s in case["statistics"].items():
                for name in NAMES[:-1]:
                    metric=s[name+"/healthy_alarm"]
                    if metric["n"]!=n or not 0<=metric["sum"]<=n:
                        raise AssertionError("Health denominator invalid")
    info=read(HERE/"analysis"/"information_power_bounds.json")
    check("information_all_72_cells",len(info)==72)
    check("information_family_failure_le_05",
          sum(x["failure_probability"] for x in info)<=.05+1e-12)
    check("information_all_use_final_50000",all(x["n"]==50000 for x in info))
    check("three_pdf_figures_present",all((HERE/"figures"/name).is_file() for name in
          ("01_magnitude_delay.pdf","02_information_budget.pdf","03_delay_pre_alarm_loss.pdf")))
    check("independent_mathematical_review_present",(HERE/"06_independent_information_review.md").is_file())
    prior=read(HERE/"protected_before.json")
    changed=[name for name,digest in prior.items()
             if not (REPO/name).is_file() or sha(REPO/name)!=digest]
    check("preexisting_files_unchanged",not changed,changed)
    missing=[]
    for path in HERE.rglob("*.md"):
        for link in re.findall(r"\]\(([^)]+)\)",path.read_text(encoding="utf8")):
            if "://" in link or link.startswith("#"):
                continue
            if not (path.parent/link.split("#")[0]).exists():
                missing.append((str(path.relative_to(HERE)),link))
    check("all_local_document_links_resolve",not missing,missing)
    tracked=subprocess.check_output(
        ["git","-c",f"safe.directory={REPO.as_posix()}","diff","--cached","--name-only"],
        cwd=REPO,text=True).splitlines()
    check("staging_scope_clean",all(name.startswith(HERE.relative_to(REPO).as_posix()+"/")
                                   for name in tracked),tracked if len(tracked)<2 else len(tracked))
    if tracked:
        byte_mismatches=[]
        for name in tuple(frozen["input_hashes"])+tuple(frozen["deterministic_evidence_hashes"])+(
                "freeze.json","information_upper_constants.json","constants_actual_candidate.json"):
            relative=(HERE/name).relative_to(REPO).as_posix()
            staged=subprocess.check_output(
                ["git","-c",f"safe.directory={REPO.as_posix()}","show",":"+relative],cwd=REPO)
            if hashlib.sha256(staged).hexdigest()!=sha(HERE/name):
                byte_mismatches.append(name)
        check("staged_frozen_bytes_match_workspace",not byte_mismatches,byte_mismatches)
    manifest={str(path.relative_to(HERE)):sha(path) for path in HERE.rglob("*")
              if path.is_file() and "__pycache__" not in path.parts
              and path.name not in ("delivery_validation.json","artifact_manifest.json")}
    (HERE/"artifact_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf8")
    result={"status":"PASS","checks":checks,"check_count":len(checks),
            "independent_episode_units":1820000,"screen_cases":24,"final_cases":24,
            "source_manuscript_modified":False,"new_random_samples_generated_by_validation":False,
            "reporting_source_changes_since_supplementary_plan":reporting_changes}
    (HERE/"delivery_validation.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf8")
    print(json.dumps({"status":"PASS","checks":len(checks),"files_manifested":len(manifest)}))


if __name__=="__main__":
    main()
