"""Independent delivery/schema/reproduction checks, no new Monte Carlo sample."""
from pathlib import Path
import csv
import json
import hashlib
import re
import subprocess
import sys
import types
import numpy as np
from p0_verified import BRANCH, ROOT, PROTECTED, BASE
from minimal_recovery_screen import build_model, common_schedule
from model import generate_data
from engine import simulate

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def csvread(p):
    with Path(p).open(encoding="utf-8-sig",newline="") as f: return list(csv.DictReader(f))

def main():
    final=BRANCH/"results/g1r_p0_verified_20261113_v1"
    acc=read(final/"acceptance.json"); cfg=read(final/"config.json")
    tol=cfg["absolute_tolerance"]
    nr=csvread(final/"network_components.csv"); cr=csvread(final/"cache_components.csv")
    assert len(nr)==48*2*80*5*2
    assert len(cr)==48*2*80*10*2
    seen=set()
    for row in nr:
        key=tuple(row[k] for k in ("scenario","seed","iteration","node","component"))
        assert key not in seen; seen.add(key)
        assert 200<=int(row["iteration"])<280
        assert int(row["state_index"])==int(row["iteration"])+1
        actual=abs(float(row["predicted"])-float(row["reference_offline"]))
        assert abs(actual-float(row["abs_error"]))<1e-20
        assert actual<tol
    seen=set()
    for row in cr:
        key=tuple(row[k] for k in ("scenario","seed","iteration","edge","component"))
        assert key not in seen; seen.add(key)
        assert int(row["age"])==int(row["iteration"])-int(row["last_receive"])
        for label in ("raw","aligned"):
            actual=abs(float(row["predicted_"+label])-float(row["reference_"+label]))
            assert abs(actual-float(row[label+"_error"]))<1e-20
            assert actual<tol
    metrics=csvread(final/"per_seed_metrics.csv")
    assert len(metrics)==48*3*4
    assert set(int(r["seed"]) for r in metrics)==set(cfg["seeds"]["test"])
    assert not set(cfg["seeds"]["train"])&set(cfg["seeds"]["calibration"])
    assert not set(cfg["seeds"]["test"])&(set(cfg["seeds"]["train"])|set(cfg["seeds"]["calibration"]))
    for p in final.glob("*.csv"):
        assert p.read_text(encoding="utf-8-sig")[:1] not in "[{"
    baseline_source=subprocess.check_output(["git","show",f"{BASE}:simulation/engine.py"],cwd=ROOT).decode("utf-8")
    registry=read(BRANCH/"run_status_index.json")
    def lf_sha(p): return hashlib.sha256(Path(p).read_bytes().replace(b"\r\n",b"\n")).hexdigest()
    artifact_index={f["path"]:f for run in registry["runs"] for f in run["files"]}
    protected_checks={}
    def check_source(path,h,optional_private=False):
        p=ROOT/path
        if not p.exists():
            assert optional_private and path in PROTECTED and path!="simulation/engine.py",path
            return "NOT_PRESENT_IN_PUBLIC_CHECKOUT"
        if sha(p)==h: return "ORIGINAL_HASH_MATCH"
        recorded=registry["final_source_fingerprints"].get(path)
        if recorded and recorded["sha256"]==h and lf_sha(p)==recorded["sha256_lf"]:
            return "SOURCE_MATCH_AFTER_CRLF_NORMALIZATION"
        if path=="simulation/engine.py":
            assert p.read_text(encoding="utf-8").replace("\r\n","\n")==baseline_source.replace("\r\n","\n")
            return "PUBLIC_BASELINE_ENGINE_COMPATIBILITY_CHECK_REQUIRED"
        raise AssertionError(("Source hash mismatch",path))
    for path,h in acc["shared_files_unchanged"].items():
        protected_checks[path]=check_source(path,h,optional_private=True)
    for folder in (final,BRANCH/"results/g1r_p1_structure_20261113_v1"):
        for path,h in read(folder/"source_hashes.json").items(): check_source(path,h)
    json_count=0
    for p in (BRANCH/"results").rglob("*.json"):
        read(p);json_count+=1
    repair=BRANCH/"results/g1r_format_repair_20261113_v1"
    for item in read(repair/"index.json"):
        original=BRANCH/item["original"]
        if sha(original)!=item["original_sha256"]:
            recorded=artifact_index[item["original"]]
            assert recorded["sha256"]==item["original_sha256"] and lf_sha(original)==recorded["sha256_lf"]
        assert len(csvread(BRANCH/item["correct_csv"]))==len(read(BRANCH/item["correct_json"]))
    # Report checks: final references exist and no stale scientific claims.
    docs=[BRANCH/f"{i:02d}_{name}.md" for i,name in [
        (1,"literature_gap"),(2,"problem_formulation"),(3,"candidate_methods"),(4,"theorem_candidates"),
        (5,"minimal_experiment"),(6,"research_decision"),(7,"full_horizon_propagation_audit"),
        (8,"information_permission_audit"),(9,"deghat_discrete_baseline"),(10,"final_research_decision")]]
    for p in docs:
        s=p.read_text(encoding="utf-8")
        assert not any(ord(c)<32 and c not in "\r\n\t" for c in s)
        for link in re.findall(r"\]\(([^)#]+)(?:#[^)]*)?\)",s):
            if "://" not in link: assert (p.parent/link).exists(),(p,link)
    # GitHub baseline engine lacks the pending G2 selector API, but the G1-R
    # branches exercised here must give exactly the same trajectories.
    source=baseline_source
    module=types.ModuleType("g1r_baseline_engine")
    sys.modules[module.__name__]=module
    exec(compile(source,"baseline_engine.py","exec"),module.__dict__)
    m=build_model(); seeds=np.array([9900000])
    x,y=generate_data(m,seeds); sched=common_schedule(m,1); errors={}
    for scn in ("clean","single_step","replay_packet"):
        a=simulate(m,x,y,seeds,"yang",scn,sched,collect=False)
        b=module.simulate(m,x,y,seeds,"yang",scn,sched,collect=False)
        errors[scn]=float(np.max(np.abs(a.estimates-b.estimates)))
        assert np.array_equal(a.estimates,b.estimates)
        assert np.array_equal(a.replay_source,b.replay_source)
    result={"status":"PASS","state_rows":len(nr),"cache_rows":len(cr),"per_seed_metric_rows":len(metrics),
            "json_files_checked":json_count,"format_migration_verified":True,"reports_checked":len(docs),
            "original_G2_hashes":acc["shared_files_unchanged"],"current_protected_checks":protected_checks,
            "github_baseline_engine_vs_working_engine_errors":errors,"no_new_samples_generated":True,
            "validation_source_sha256":sha(__file__)}
    (BRANCH/"final_delivery_validation.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))

if __name__=="__main__": main()
