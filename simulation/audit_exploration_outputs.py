"""Recompute key metrics from retained exploration artifacts; no new simulations."""
from __future__ import annotations
import csv,hashlib,json
from pathlib import Path
import numpy as np
from run_study import write_json


def audit(folder):
    folder=Path(folder)
    plan=json.loads((folder/"plan.json").read_text(encoding="utf-8"))
    with (folder/"per_seed_metrics.csv").open(encoding="utf-8-sig",newline="") as f:rows=list(csv.DictReader(f))
    key="model" if "model" in rows[0] else "schedule"
    ix={(r[key],r["method"],r["scenario"],int(r["seed"])):r for r in rows}
    assert len(ix)==len(rows)
    splitsets=[]
    for name,s in plan["splits"].items():splitsets.append(set(range(s["start"],s["start"]+s["count"])))
    for i,a in enumerate(splitsets):
        for b in splitsets[i+1:]:assert not a&b
    checked=0;maxerr=0;replays=0
    settings=sorted({r[key] for r in rows})
    for setting in settings:
        sub=folder/setting;cfg=json.loads((sub/"config.json").read_text(encoding="utf-8"))
        with np.load(sub/"test_inputs.npz") as d:x=d["x"];seeds=d["seeds"];schedule=d["schedule"]
        assert set(map(int,seeds))==splitsets[-1]
        for method in plan["methods"]:
            for scenario in plan["scenarios"]:
                with np.load(sub/(method+"__"+scenario+".npz")) as r:
                    assert np.isfinite(r["estimates"]).all() and np.isfinite(r["weights"]).all()
                    assert np.all((r["weights"]>=0)&(r["weights"]<=1))
                    if method!="local":assert np.array_equal(r["sends"],schedule)
                    start,end=cfg["attack"]["start"],cfg["attack"]["end_inclusive"]
                    errors=np.sum((r["estimates"]-x[:,:,None,:])**2,axis=-1)
                    computed=errors[:,start+1:end+2].mean(axis=(1,2))
                    saved=np.asarray([float(ix[setting,method,scenario,int(s)]["mse_attack_window"]) for s in seeds])
                    e=float(np.max(np.abs(computed-saved)));maxerr=max(maxerr,e);assert e<1e-12
                    for trial,t in zip(*np.where(r["injected"])):
                        assert start<=t<=end and r["sends"][trial,t,cfg["attack"]["sender"]]
                        if scenario.startswith("replay"):
                            old=int(r["replay_source"][trial,t]);assert 0<=old<t
                            assert r["sends"][trial,old,cfg["attack"]["sender"]];replays+=1
                    checked+=1
    registration=folder/"registration.json"
    hashes=True
    if registration.exists():
        r=json.loads(registration.read_text(encoding="utf-8"))
        for f,sha in r["source_sha256"].items():
            hashes&=hashlib.sha256((folder/"sources"/f).read_bytes()).hexdigest()==sha
    assert hashes
    result={"passed":True,"cases":checked,"metric_rows":len(rows),"mse_max_recompute_error":maxerr,"legal_replay_packets":replays,
        "sources_match_snapshot_hash":hashes,"split_seeds_disjoint":True,"new_simulations":0,
        "limits":"Does not prove novelty or general stability; metrics and permissions consistent with declared runs"}
    write_json(folder/"output_audit.json",result);print(json.dumps({"folder":str(folder),**result}))


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("folders",nargs="+");a=p.parse_args()
    for f in a.folders:audit(f)
