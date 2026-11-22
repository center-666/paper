"""Task-scoped artifact, arithmetic-source and proof-tree delivery checks."""
import ast,csv,hashlib,json,re,subprocess
from pathlib import Path
from decimal import Decimal

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding="utf8"))


def main():
    checks=[]
    def check(name,ok,detail=None):
        checks.append({"name":name,"pass":bool(ok),"detail":detail})
        if not ok:raise AssertionError(name+": "+str(detail))
    for p in HERE.glob("*.py"):ast.parse(p.read_text(encoding="utf8"))
    check("sources_parse",True)
    op=read(HERE/"optimizer_checks.json")
    check("optimizer_checks_pass",op["status"]=="PASS" and all(x["pass"] for x in op["checks"]),op["check_count"])
    check("optimizer_verified_source",op["source_sha256"]==sha(HERE/"strong_concavity.py"))
    ac=read(HERE/"analytic_checks.json")
    check("analytic_formula_checks",ac["status"]=="PASS" and all(x["pass"] for x in ac["checks"]),ac["check_count"])
    total_leaves=0
    for model in ("S1","U1"):
        for gap in ("0.15","0.2","0.25"):
            stem=f"{model}_gap{gap}_target0.0001"
            folder=HERE/"fourier_certificates"
            cert=read(folder/(stem+".json"))
            verify=read(folder/(stem+"_verification.json"))
            check(stem+"_certified",cert["status"]=="CERTIFIED" and cert["pending"]==0)
            check(stem+"_source",cert["source_sha256"]==sha(HERE/"certify_fourier.py"))
            check(stem+"_leaf_file",cert["leaves_sha256"]==sha(folder/(stem+".csv")))
            check(stem+"_full_replay",verify["status"]=="PASS" and verify["root_domain_covered"]
                  and verify["every_leaf_interval_recomputed"]
                  and verify["certificate_sha256"]==sha(folder/(stem+".json")))
            check(stem+"_replayed_target",Decimal(verify["minimum_gap_lower"])>=Decimal(".0001"))
            total_leaves+=verify["verified_leaves"]
    times=read(HERE/"new_time_bounds.json")
    check("time_bound_contract_unchanged",times["status"]=="PASS" and times["same_risk_budget_and_reference_as_stage4"])
    check("sufficient_time_strictly_improved",all(x["new_sufficient_age"]<x["old_sufficient_age"] and
          Decimal(x["conditional_risk_improvement_expectation_lower"])>0 and
          Decimal(x["later_age_monotonicity_upper"])<1 for x in times["rows"]))
    independent=read(HERE/"independent_time_checks.json")
    check("independent_100digit_time_recomputation",independent["status"]=="PASS"
          and all(x["pass"] for x in independent["checks"])
          and independent["input_sha256"]==sha(HERE/"new_time_bounds.json"))
    calls=[]
    for path in HERE.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf8"))):
            if isinstance(node,ast.Call):
                name=node.func.id if isinstance(node.func,ast.Name) else node.func.attr if isinstance(node.func,ast.Attribute) else ""
                if name in ("random","default_rng","SeedSequence","randn"):calls.append((path.name,name))
    check("no_random_generator_calls",not calls,calls)
    protected=read(HERE/"protected_before.json")
    changes=[name for name,digest in protected["files"].items()
             if not (REPO/name).is_file() or sha(REPO/name)!=digest]
    check("task_external_files_unchanged",not changes,changes)
    missing=[]
    for doc in HERE.rglob("*.md"):
        for target in re.findall(r"\]\(([^)]+)\)",doc.read_text(encoding="utf8")):
            if "://" in target or target.startswith("#"):continue
            if (doc.parent/target).resolve()==(HERE/"delivery_validation.json").resolve():continue
            if not (doc.parent/target.split("#")[0]).exists():missing.append((doc.name,target))
    check("local_links_resolve",not missing,missing)
    staged=subprocess.check_output(["git","-c",f"safe.directory={REPO.as_posix()}",
        "diff","--cached","--name-only"],cwd=REPO,text=True).splitlines()
    check("staged_scope",all(x.startswith(HERE.relative_to(REPO).as_posix()+"/") for x in staged),len(staged))
    result={"status":"PASS","check_count":len(checks),"checks":checks,
            "recomputed_parameter_leaves":total_leaves,"performance_random_samples":0,
            "formal_manuscript_modified":False,"base_commit":protected["base_commit"]}
    (HERE/"delivery_validation.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf8",newline="\n")
    artifacts={str(p.relative_to(HERE)):sha(p) for p in HERE.rglob("*") if p.is_file()
               and "__pycache__" not in p.parts and p.name!="artifact_manifest.json"}
    (HERE/"artifact_manifest.json").write_text(json.dumps(artifacts,indent=2)+"\n",encoding="utf8",newline="\n")
    print(json.dumps({"status":"PASS","checks":len(checks),"parameter_leaves":total_leaves,"artifacts":len(artifacts)}))


if __name__=="__main__":main()
