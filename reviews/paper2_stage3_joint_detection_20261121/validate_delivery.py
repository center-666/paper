"""Full stage-three artifact, sample, numerical and provenance validation."""
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
from core import NAMES
from run_experiment import HERE,METHODS,sha,check_frozen

REPO=HERE.parents[1]


def read(p):
    return json.loads(Path(p).read_text(encoding="utf8"))


def main():
    checks=[]
    def check(name,ok,detail=None):
        checks.append({"name":name,"pass":bool(ok),"detail":detail})
        if not ok:raise AssertionError(f"{name}: {detail}")
    p=read(HERE/"protocol.json");frozen=read(HERE/"freeze.json")
    check_frozen()
    check("all_frozen_performance_inputs_unchanged",True,frozen["input_hashes"])
    for name,digest in frozen["evidence_hashes"].items():
        check("frozen_evidence_"+name,sha(HERE/name)==digest)
    check("reference_integrals_pass",read(HERE/"joint_reference_checks.json")["status"]=="PASS")
    check("core_integrals_recurrence_zero_policy_pass",read(HERE/"joint_kernel_checks.json")["status"]=="PASS")
    check("scalar_receiver_equivalent",read(HERE/"receiver_interface_checks.json")["status"]=="PASS"
          and read(HERE/"receiver_interface_checks.json")["receiver_source_sha256"]==sha(HERE/"receiver_detector.py"))
    check("precision_checks_pass",read(HERE/"precision_sensitivity_checks.json")["status"]=="PASS")
    phasecheck=read(HERE/"phase_visibility_checks.json")
    check("phase_visibility_checks_pass",phasecheck["status"]=="PASS"
          and phasecheck["max_center_to_codeword_projection_error"]<1e-12
          and phasecheck["max_codeword_kernel_normalization_error"]<1e-12
          and phasecheck["max_silent_event_projection_error"]<1e-12)
    check("phase_permission_independent_review",
          (HERE/"12_phase_visibility_review.md").is_file()
          and (HERE/"11_phase_visibility_addendum.md").is_file())
    phasecheck=read(HERE/"phase_visibility_checks.json")
    check("phase_visibility_checks_pass",phasecheck["status"]=="PASS"
          and phasecheck["max_center_to_codeword_projection_error"]<1e-12
          and phasecheck["max_codeword_kernel_normalization_error"]<1e-12
          and phasecheck["max_silent_event_projection_error"]<1e-12)
    check("fractional_moment_checks_pass",read(HERE/"fractional_moment_checks.json")["status"]=="PASS")
    seednames=[key for key in p if key.endswith("_seed")]
    check("independent_stage_seed_roots",len({p[key] for key in seednames})==len(seednames))
    allfiles=[];episode_count=0
    for stage in ("screen","final","offgrid"):
        expected_cases=4 if stage=="offgrid" else 24
        finish=read(HERE/"results"/stage/"completion.json")
        check(stage+"_scheduler_complete",finish["status"]=="COMPLETE" and finish["cases"]==expected_cases)
        files=list((HERE/"results"/stage).glob("*_b*.json"))
        check(stage+"_case_count",len(files)==expected_cases)
        for file in files:
            case=read(file);allfiles.append(file);episode_count+=case["n"]
            assert case["n"]==p[stage+"_episodes"] and case["frozen_hash"]==sha(HERE/"freeze.json")
            assert case["recovery_actions"] is False
            n=case["n"]
            previous={name:0 for name in METHODS};eligible_old={}
            for H in p["horizons_after_onset"]:
                s=case["statistics"][str(H)]
                for name in ("monitor_MSE","healthy_MSE","MSE_excess","bias_energy","sends",
                             "oracle_joint_log_LR","oracle_phase_event_log_LR","oracle_conditional_payload_log_LR"):
                    assert s[name]["n"]==n and math.isfinite(s[name]["mean"])
                assert s["sends"]["mean"]<=H
                identity=(s["oracle_joint_log_LR"]["mean"]-s["oracle_phase_event_log_LR"]["mean"]
                          -s["oracle_conditional_payload_log_LR"]["mean"])
                assert abs(identity)<1e-9
                for name in METHODS:
                    false=round(s[name+"/pre_attack_alarm"]["sum"])
                    eligible=s[name+"/detection_eligible"]["n"]
                    count=round(s[name+"/detection_eligible"]["sum"])
                    assert false+eligible==n
                    assert count==round(s[name+"/detection_unconditional"]["sum"])
                    assert previous[name]<=count<=eligible
                    previous[name]=count
                    if name in eligible_old:assert eligible_old[name]==eligible
                    eligible_old[name]=eligible
                    assert 1<=s[name+"/restricted_delay_eligible"]["mean"]<=H
                    assert s[name+"/pre_MSE_unconditional"]["mean"]<=s["monitor_MSE"]["mean"]+1e-9
                    assert s[name+"/pre_MSE_unconditional"]["n"]==n
            assert all(r["oracle_chain_identity_max_error"]<1e-8 for r in case["runtime_checks"])
        check(stage+"_denominators_time_indices_log_decomposition",True)
    for stage in ("health_screen","health_final"):
        finish=read(HERE/"results"/stage/"completion.json")
        assert finish["status"]=="COMPLETE"
        for model in p["models"]:
            path=HERE/"results"/stage/(model["id"]+".json")
            row=read(path);episode_count+=row["n"];allfiles.append(path)
            assert row["n"]==p[stage+"_episodes"] and row["frozen_hash"]==sha(HERE/"freeze.json")
            previous={name:0 for name in NAMES}
            for H in (512,2048,8192):
                for name in NAMES:
                    m=row["statistics"][str(H)][name+"/healthy_alarm"]
                    assert m["n"]==row["n"] and previous[name]<=m["sum"]<=row["n"]
                    previous[name]=m["sum"]
        check(stage+"_complete_and_denominators_valid",True)
    check("all_1510000_independent_episode_units",episode_count==1510000,episode_count)
    table=list(csv.DictReader((HERE/"analysis/delay_bins.csv").open(encoding="utf8")))
    check("all_delay_bins_nonnegative_and_complete",
          all(all(int(row[key])>=0 for key in ("1_128","129_512","513_1024","1025_2048","not_detected_2048"))
              and sum(int(row[key]) for key in ("1_128","129_512","513_1024","1025_2048","not_detected_2048"))==int(row["eligible_n"])
              for row in table))
    check("all_final_metric_rows",len(list(csv.DictReader((HERE/"analysis/final_metrics.csv").open(encoding="utf8"))))==24*4*8)
    for file in ("01_power_vs_horizon.pdf","02_delay_by_magnitude.pdf","03_pre_alarm_exposure.pdf"):
        check("figure_"+file,(HERE/"figures"/file).is_file())
    for file in ("04_independent_math_review.md","06_fractional_moment_review.md"):
        check("independent_review_"+file,(HERE/file).is_file())
    old=read(HERE/"protected_before.json")
    changed=[name for name,digest in old.items() if not (REPO/name).is_file() or sha(REPO/name)!=digest]
    check("all_preexisting_files_unchanged",not changed,changed)
    missing=[]
    for path in HERE.rglob("*.md"):
        for target in re.findall(r"\]\(([^)]+)\)",path.read_text(encoding="utf8")):
            if "://" in target or target.startswith("#"):continue
            if not (path.parent/target.split("#")[0]).exists():
                missing.append({"file":str(path.relative_to(HERE)),"target":target})
    check("local_document_links_resolve",not missing,missing)
    cmd=["git","-c",f"safe.directory={REPO.as_posix()}"]
    staged=subprocess.check_output(cmd+["diff","--cached","--name-only"],cwd=REPO,text=True).splitlines()
    scope=HERE.relative_to(REPO).as_posix()+"/"
    check("staged_files_task_scoped",all(name.startswith(scope) for name in staged),len(staged))
    if staged:
        bad=[]
        for name in list(frozen["input_hashes"])+list(frozen["evidence_hashes"])+["freeze.json"]:
            data=subprocess.check_output(cmd+["show",":"+scope+name],cwd=REPO)
            if hashlib.sha256(data).hexdigest()!=sha(HERE/name):bad.append(name)
        check("staged_frozen_bytes_preserved",not bad,bad)
    artifacts={str(file.relative_to(HERE)):sha(file) for file in HERE.rglob("*")
               if file.is_file() and "__pycache__" not in file.parts
               and file.name not in ("delivery_validation.json","artifact_manifest.json")}
    (HERE/"artifact_manifest.json").write_text(json.dumps(artifacts,indent=2)+"\n",encoding="utf8",newline="\n")
    result={"status":"PASS","check_count":len(checks),"checks":checks,"episodes":episode_count,
            "formal_manuscript_modified":False,"performance_data_generated_by_validation":False}
    (HERE/"delivery_validation.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf8",newline="\n")
    print(json.dumps({"status":"PASS","checks":len(checks),"artifacts":len(artifacts),"episodes":episode_count}))


if __name__=="__main__":
    main()
