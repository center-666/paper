"""Verify vector proof certificates, frozen pilot, and task-scoped artifacts."""
from pathlib import Path
import ast,csv,hashlib,json,re,subprocess
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text(encoding="utf8"))


def main():
    checks=[]
    def check(name,ok,detail=None):
        checks.append({"name":name,"pass":bool(ok),"detail":detail})
        if not ok:raise AssertionError(name+": "+str(detail))
    for file in HERE.glob("*.py"):ast.parse(file.read_text(encoding="utf8"))
    check("all_python_parses",True)
    first=read(HERE/"freeze.json");second=read(HERE/"freeze_v2.json")
    for name,digest in first["inputs"].items():check("original_input_"+name,sha(HERE/name)==digest)
    for name,digest in second["inputs"].items():check("retry_input_"+name,sha(HERE/name)==digest)
    for name,digest in first["dependency_hashes"].items():check("frozen_dependency_"+name,sha(REPO/name)==digest)
    check("amendment_transparent",second["amendment"]["completed_prior_performance_episodes"]==0
          and second["superseded_freeze_sha256"]==sha(HERE/"freeze.json"))
    for name,digest in first["preflight"].items():
        check("preflight_"+name,sha(HERE/name)==digest and read(HERE/name)["status"]=="PASS")
    cov=read(HERE/"covariance_certificate.json")
    check("all_exact_covariance_inequalities",all(cov["checks"].values()))
    check("contraction_domain_all_histories",cov["metric_contraction_squared"]=="19/20"
          and cov["euclidean_prefactor_squared"]=="25")
    geometry=read(HERE/"projection_checks.json")
    check("projection_and_direction_tests",all(row["pass"] for row in geometry["checks"]),geometry["check_count"])
    dyn=read(HERE/"dynamics_checks.json")
    check("exact_tree_and_negative_pollution",dyn["exact_metric_inequalities_verified"]==1792
          and dyn["first_second_component_negative_on_all_send_path"]==7)
    check("deterministic_failure_boundaries",read(HERE/"counterexample_checks.json")["status"]=="PASS")
    p=read(HERE/"pilot_protocol.json");total=0
    for stage in ("screen","final"):
        n=p[stage+"_episodes_per_case"]
        completion=read(HERE/"results_v2"/stage/"completion.json")
        assert completion["status"]=="COMPLETE" and completion["episodes"]==3*n
        for b in p["attack_strengths"]:
            for i in range(n):
                row=read(HERE/"results_v2"/stage/f"b{b:g}_episode{i:03d}.json");total+=1
                assert row["stage"]==stage and row["b"]==b and row["episode"]==i
                assert row["freeze_sha256"]==sha(HERE/"freeze_v2.json")
                for H in p["evaluation_windows"]:
                    s=row["snapshots"][str(H)]
                    assert abs(s["monitor"]-s["certified"]-s["certified_gain"])<1e-9
                    assert abs(s["monitor"]-s["point"]-s["point_gain"])<1e-9
                    assert s["coverage_violating_steps"]>=0
                for query in row["certificate_queries"]:
                    if query["certified"]:
                        assert query["reason"]=="ALL_LOW_SUPPORT_MODELS_EXCLUDED"
                        assert float(query["guaranteed_gain"].split("/")[0])>=0
        check(stage+"_all_episodes_complete",True,3*n)
    check("pilot_total_48",total==48)
    summary=read(HERE/"analysis/summary.json")
    check("all_summary_cells",summary["status"]=="COMPLETE" and len(summary["rows"])==9)
    check("all_final_denominators_12",all(row["n"]==12 for row in summary["rows"]))
    check("all_three_standalone_figures",all((HERE/"figures"/name).is_file() for name in
          ("01_projection_geometry.pdf","02_signed_pollution_response.pdf","03_pilot_gain_and_cost.pdf")))
    protected=read(HERE/"protected_before.json")
    changed=[name for name,digest in protected.items() if not (REPO/name).is_file() or sha(REPO/name)!=digest]
    check("preexisting_files_unchanged",not changed,changed)
    missing=[]
    for path in HERE.rglob("*.md"):
        for target in re.findall(r"\]\(([^)]+)\)",path.read_text(encoding="utf8")):
            if "://" in target or target.startswith("#"):continue
            dest=(path.parent/target.split("#")[0])
            if dest==HERE/"delivery_validation.json":continue
            if not dest.exists():missing.append((path.name,target))
    check("local_links_resolve",not missing,missing)
    cmd=["git","-c",f"safe.directory={REPO.as_posix()}"]
    staged=subprocess.check_output(cmd+["diff","--cached","--name-only"],cwd=REPO,text=True).splitlines()
    check("staging_task_only",all(name.startswith(HERE.relative_to(REPO).as_posix()+"/") for name in staged))
    output={"status":"PASS","checks":checks,"check_count":len(checks),"pilot_episodes":total,
            "formal_manuscript_modified":False,"base_commit":first["base_commit"]}
    (HERE/"delivery_validation.json").write_text(json.dumps(output,indent=2)+"\n",encoding="utf8",newline="\n")
    artifacts={str(path.relative_to(HERE)):sha(path) for path in HERE.rglob("*")
               if path.is_file() and "__pycache__" not in path.parts and path.name!="artifact_manifest.json"}
    (HERE/"artifact_manifest.json").write_text(json.dumps(artifacts,indent=2)+"\n",encoding="utf8",newline="\n")
    print(json.dumps({"status":"PASS","checks":len(checks),"artifacts":len(artifacts),"pilot_episodes":total}))


if __name__=="__main__":main()
