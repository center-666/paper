"""Developer calibration, immutable registration and disjoint confirmation runs."""
import argparse
from concurrent.futures import ProcessPoolExecutor
from decimal import Decimal as D
from pathlib import Path
import subprocess
import sys
import time
from experiment import ROOT, REV, MODEL, TIMES, Methods, record, evaluate, read, save, digest

SPEC=read(ROOT/"config/confirmation_protocol.json")
GROUPS=list(SPEC["groups"])

def amplitude(g,cap):
    if g=="health":
        return 0.
    value=float(cap) if g.startswith("strong") else SPEC["weak"]
    return -value if g.endswith("negative") else value

def job(args):
    phase,g,i,cap,h,seed=args
    start=time.process_time()
    payload,truth=record(seed,GROUPS.index(g),i,amplitude(g,cap))
    if phase=="calibration":
        method=Methods(D(cap),"Infinity","M1")
        scores=[]
        for frame in payload[:TIMES[-1]+1]:
            _,q,_,_=method.step(frame)
            if q:
                scores.append(q["score"])
        return dict(index=i,scores=scores,cpu=time.process_time()-start)
    result=evaluate(payload,truth,amplitude(g,cap),D(cap),h)
    result.update(id=f"{g}-{i:02d}",group=g,index=i,b=amplitude(g,cap),cpu=time.process_time()-start)
    if phase=="confirmation":
        result["registration"]=digest(ROOT/"registration.json")
        save(ROOT/"results/confirmation"/(result["id"]+".json"),result)
        return result["id"]
    return dict(id=result["id"],useful=result["metrics"]["M3"]["useful"],miss=result["miss"],
                violations=result["violations"],active=result["checked"],cpu=result["cpu"])

def develop(pool):
    log=[]
    for strength in SPEC["strong_ladder"]:
        cap=str(strength)
        rows=list(pool.map(job,[("dev",g,i,cap,"Infinity",SPEC["dev_seed"])
                                for g in GROUPS[:2] for i in range(4)]))
        counts=[sum(r["useful"]>0 for r in rows if r["id"].startswith(g)) for g in GROUPS[:2]]
        log.append(dict(cap=cap,counts=counts,rows=rows))
        save(ROOT/"results/development_ladder.json",log)
        print("dev",cap,counts,flush=True)
        if min(counts)>=3:
            break
    weak=list(pool.map(job,[("dev",g,i,cap,"Infinity",SPEC["dev_seed"]) for g in GROUPS[2:4] for i in range(4)]))
    save(ROOT/"results/development_weak.json",weak)
    scores=list(pool.map(job,[("calibration","health",i,cap,"Infinity",SPEC["calibration_seed"])
                              for i in range(SPEC["calibration_n"])]))
    ordered=sorted(max(map(D,r["scores"])) for r in scores)
    rank=int((D(str(SPEC["threshold_quantile"]))*len(scores)).to_integral_value(rounding="ROUND_CEILING"))
    save(ROOT/"results/calibration.json",dict(cap=cap,rank=rank,threshold=str(ordered[rank-1]),rows=scores))
    print("calibration",cap,rank,ordered[rank-1],flush=True)

def register():
    path=ROOT/"registration.json"
    if path.exists() or (ROOT/"results/confirmation").exists():
        raise FileExistsError("Registration or test results already exist")
    import numpy, scipy
    cal=read(ROOT/"results/calibration.json")
    inputs=list((ROOT/"config").glob("*.json"))+list((ROOT/"code").glob("*.py"))
    inputs+=list((ROOT/"results").glob("*.json"))
    for folder,files in {
        "paper2_stage7_confirmation/code":["engine.py","common.py"],
        "paper2_stage7_fixed_amplitude_20261122":["fixed_amplitude.py","direction_cache_corrected.py"],
        "paper2_stage6_vector_correction_20261122":["pilot_v2.py","vector_record.py","exact_linear.py","projection.py","model.json"],
        "paper2_stage4_certified_correction_20261122":["interval_arithmetic.py","certificate.py"],
        "paper2_stage5_certification_acceleration_20261122":["strong_concavity.py"]}.items():
        inputs.extend(REV/folder/name for name in files)
    reg=dict(**SPEC,source_commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
             inputs={p.relative_to(REV).as_posix():digest(p) for p in inputs},strong=cal["cap"],
             threshold=cal["threshold"],versions=[sys.version,numpy.__version__,scipy.__version__],
             aggregate="per group paired cumulative loss; two-sided trajectory t intervals; opportunity-weighted conditional share",
             representative="first ID with a useful M3 after the first shared certificate in each strong sign; otherwise first ID",
             elapsed="IDs 0,1 of each strong sign, four simultaneous workers, same prewarm and caches cleared before each method",
             risk_tolerance=1e-10,direct_tolerance=1e-9)
    save(path,reg)

def confirmation(pool):
    reg=read(ROOT/"registration.json")
    for p,h in reg["inputs"].items():
        if digest(REV/p)!=h:
            raise ValueError("Input mismatch: "+p)
    jobs=[]
    for g,n in reg["groups"].items():
        for i in range(n):
            path=ROOT/"results/confirmation"/f"{g}-{i:02d}.json"
            if path.exists():
                if read(path)["registration"]!=digest(ROOT/"registration.json"):
                    raise ValueError("Foreign row")
            else:
                jobs.append(("confirmation",g,i,reg["strong"],reg["threshold"],reg["test_seed"]))
    for ident in pool.map(job,jobs):
        print(ident,flush=True)

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("stage",choices=["development","register","confirmation"])
    stage=parser.parse_args().stage
    if stage=="register":
        register()
    else:
        with ProcessPoolExecutor(SPEC["workers"]) as pool:
            (develop if stage=="development" else confirmation)(pool)
