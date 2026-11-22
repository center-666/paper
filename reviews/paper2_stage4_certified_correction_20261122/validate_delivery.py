"""Theory-only delivery checks; no new observations or random trajectories."""
import ast,hashlib,json,re,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]


def load(path):
    return json.loads(Path(path).read_text(encoding="utf8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    checks=[]
    def check(name,ok,detail=None):
        checks.append({"name":name,"pass":bool(ok),"detail":detail})
        if not ok:raise AssertionError(name+": "+str(detail))
    for source in HERE.glob("*.py"):
        ast.parse(source.read_text(encoding="utf8"))
    check("python_sources_parse",True)
    cert=load(HERE/"certificate_checks.json")
    check("interval_certificate_checks_pass",cert["status"]=="PASS" and
          all(row["pass_check"] for row in cert["checks"]),cert["check_count"])
    check("certificate_has_no_performance_claim",cert["random_samples_generated"] is False
          and cert["performance_recovery_claimed"] is False)
    for name,digest in cert["input_hashes"].items():
        check("validated_certificate_source_"+name,sha(HERE/name)==digest)
    budgets=load(HERE/"risk_budgets.json")
    check("risk_budget_checks_pass",budgets["status"]=="PASS" and
          all(row["pass"] for row in budgets["checks"]),len(budgets["checks"]))
    check("risk_budget_source_hash",budgets["source_sha256"]==sha(HERE/"compute_risk_budgets.py"))
    exact=load(HERE/"invariance_checks.json")
    check("coefficient_exact_rational_checks",exact["status"]=="PASS" and exact["event_paths"]==512)
    separation=load(HERE/"separation_bounds.json")
    check("explicit_separation_constants_pass",separation["status"]=="PASS" and
          separation["random_samples_generated"] is False)
    check("separation_generator_hash",separation["source_sha256"]==sha(HERE/"compute_separation_bounds.py"))
    independent=load(HERE/"independent_separation_checks.json")
    check("independent_high_precision_separation",independent["status"]=="PASS")
    forbidden={"default_rng","randn","SeedSequence","random"}
    stochastic_calls=[]
    for path in HERE.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf8"))):
            if isinstance(node,ast.Call):
                name=(node.func.id if isinstance(node.func,ast.Name) else
                      node.func.attr if isinstance(node.func,ast.Attribute) else "")
                if name in forbidden:stochastic_calls.append((path.name,name))
    check("no_random_generator_calls",not stochastic_calls,stochastic_calls)
    for name in ("01_identifiability_and_functional_contraction.md",
                 "02_confidence_sequence_and_risk.md","03_continuous_amplitude_certificate.md",
                 "04_computational_review.md","05_literature_and_scope.md",
                 "06_independent_theory_review.md","07_explicit_separation_and_expected_gain.md",
                 "08_continuous_functional_contraction.md","09_continuous_independent_review.md",
                 "10_finite_reference_outer_approximation.md"):
        check("required_"+name,(HERE/name).is_file())
    missing=[]
    for doc in HERE.rglob("*.md"):
        for target in re.findall(r"\]\(([^)]+)\)",doc.read_text(encoding="utf8")):
            if "://" in target or target.startswith("#"):continue
            if not (doc.parent/target.split("#")[0]).exists():
                missing.append((str(doc.relative_to(HERE)),target))
    check("local_links_resolve",not missing,missing)
    before=load(HERE/"protected_before.json")
    changed=[name for name,digest in before["files"].items()
             if not (REPO/name).is_file() or sha(REPO/name)!=digest]
    check("task_external_files_unchanged",not changed,changed)
    cmd=["git","-c",f"safe.directory={REPO.as_posix()}"]
    staged=subprocess.check_output(cmd+["diff","--cached","--name-only"],cwd=REPO,text=True).splitlines()
    scope=HERE.relative_to(REPO).as_posix()+"/"
    check("staged_scope",all(name.startswith(scope) for name in staged),len(staged))
    result={"status":"PASS","checks":checks,"check_count":len(checks),
            "performance_random_samples":0,"formal_manuscript_modified":False,
            "base_commit":before["base_commit"]}
    (HERE/"delivery_validation.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf8",newline="\n")
    artifacts={str(path.relative_to(HERE)):sha(path) for path in HERE.rglob("*")
               if path.is_file() and "__pycache__" not in path.parts and path.name!="artifact_manifest.json"}
    (HERE/"artifact_manifest.json").write_text(json.dumps(artifacts,indent=2)+"\n",encoding="utf8",newline="\n")
    print(json.dumps({"status":"PASS","checks":len(checks),"artifacts":len(artifacts),
                      "performance_random_samples":0}))


if __name__=="__main__":
    main()
