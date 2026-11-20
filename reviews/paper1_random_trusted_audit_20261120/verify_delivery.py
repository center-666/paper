"""Final integrity and cross-file checks. Not a new Monte Carlo experiment."""
from pathlib import Path
import csv
import hashlib
import json
import re
import subprocess

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
RUN=HERE/"results/run_20261120_v1"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    checks=[]
    def ck(name,passed,**details):
        checks.append(dict(name=name,passed=bool(passed),**details))
    protected=json.loads((HERE/"protected_before.json").read_text(encoding="utf-8"))
    changed=[n for n,h in protected["files"].items() if not (REPO/n).is_file() or sha(REPO/n)!=h]
    ck("all_preexisting_tracked_and_untracked_assets_unchanged",not changed,count=len(protected["files"]),changes=changed)
    freeze=json.loads((HERE/"freeze.json").read_text(encoding="utf-8"))
    ck("protocol_frozen",sha(HERE/"protocol.json")==freeze["protocol_sha256"])
    for n,h in freeze["other_scripts_sha256"].items():ck("frozen_code/"+n,sha(HERE/n)==h)
    ck("original_E1_code_frozen",sha(REPO/"reviews/paper1_e1_scalar_execution/code/run_e1.py")==freeze["saved_e1_script_sha256"])
    inp=json.loads((HERE/"input_manifest.json").read_text(encoding="utf-8"))
    ck("input_freeze_hash",inp["freeze_sha256"]==sha(HERE/"freeze.json"))
    for n,row in inp["files"].items():ck("input/"+n,sha(HERE/"inputs"/n)==row["sha256"])
    manifest=json.loads((RUN/"result_manifest.json").read_text(encoding="utf-8"))
    for n,h in manifest["files_sha256"].items():ck("frozen_result/"+n,sha(RUN/n)==h)
    audit=json.loads((RUN/"independent_array_audit.json").read_text(encoding="utf-8"))
    ck("separate_raw_array_audit_PASS",audit["status"]=="PASS" and not audit["failed"],checks=len(audit["checks"]))
    rows=list(csv.DictReader((RUN/"single_test_results.csv").open(encoding="utf-8-sig")))
    ck("sixty_planned_test_rows",len(rows)==60)
    for mid in ["S1","U1"]:
        for attack in ["cell_sign","balanced_reflection"]:
            subset=[r for r in rows if r["model"]==mid and r["attack"]==attack]
            for delta in sorted(set(r["delta"] for r in subset)):
                group=[r for r in subset if r["delta"]==delta]
                ck(f"{mid}/{attack}/{delta}/damage_independent_of_audit",
                   len(set(r["damage_mean"] for r in group))==1 and len(group)==5)
                for row in group:
                    cost=float(row["auth_packets_random_audit"])
                    full=float(row["auth_packets_all_auth"])
                    ck(f"{mid}/{attack}/{delta}/{row['rho']}/authentication_accounting",
                       abs(cost/full-float(row["auth_packet_fraction_vs_all_auth"]))<1e-14)
    q=json.loads((RUN/"quadrature_and_sample_planning.json").read_text(encoding="utf-8"))
    diffs=[r for r in q if "mean_score_abs_diff" in r]
    ck("quadrature_frozen_16_32_consistency",
       all(r["mean_score_abs_diff"]<1e-10 and r["second_moment_abs_diff"]<1e-10 for r in diffs),
       max_mean_difference=max(r["mean_score_abs_diff"] for r in diffs))
    for p in HERE.rglob("*.md"):
        t=p.read_text(encoding="utf-8")
        broken=[s for s in re.findall(r"\]\(([^)]+)\)",t)
                if not s.startswith(("http:","https:","#"))
                and not (p.parent/s).exists()]
        ck("document/"+p.relative_to(HERE).as_posix(),
           t.count(r"\(")==t.count(r"\)") and t.count(r"\[")==t.count(r"\]")
           and "\ufffd" not in t and not broken,broken_links=broken)
    staged=subprocess.check_output(["git","diff","--cached","--name-only","-z"],cwd=REPO,encoding="utf-8").split("\0")
    wrong=[n for n in staged if n and not n.startswith(HERE.relative_to(REPO).as_posix()+"/")]
    ck("staged_scope",not wrong,unexpected=wrong)
    status="PASS" if all(c["passed"] for c in checks) else "FAIL"
    output={"status":status,"checks":checks,"failed":[c for c in checks if not c["passed"]],
            "experiment_source_freeze_commit":"1e384e98","research_base":"19e7b7d8",
            "decision":"ADJUST","manuscript_changes":False,"new_simulation_runs":1,
            "theory":"conditional random-labelled-mixture identity and D single-shot identifiability",
            "evidence_limit":"nominal 1% healthy calibration; test FPR may exceed 1%; sample planning is a normal approximation",
            "all_task_files_sha256":{p.relative_to(HERE).as_posix():sha(p) for p in sorted(HERE.rglob("*"))
              if p.is_file() and p.name not in ["delivery_validation.json"] and "__pycache__" not in p.parts}}
    (HERE/"delivery_validation.json").write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",
                                                encoding="utf-8",newline="\n")
    print(json.dumps({"status":status,"checks":len(checks),"failures":output["failed"]},ensure_ascii=True))
    if status!="PASS":raise SystemExit(1)


if __name__=="__main__":
    main()
