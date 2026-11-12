"""Exploratory, predeclared tests of temporal-reference contamination recovery."""
from __future__ import annotations
import argparse
import copy
import csv
import hashlib
import json
from pathlib import Path
import shutil
import time
import numpy as np
from model import Model,generate_data,seed_range
from engine import simulate,basic_metrics
from calibration import fit_control,reference_evidence
from run_study import calibrate_mode,write_json,write_csv,paired_interval
from validation_suite import repeated_schedule


def recovery_metrics(model,run,x,scenario):
    cfg=model.cfg;a=cfg["attack"];source,target=a["sender"],a["receiver"]
    edge=np.flatnonzero(np.all(model.edges==[source,target],axis=1))[0]
    error=np.sum((run.estimates-x[:,:,None,:])**2,axis=-1)
    rows=[]
    for s in range(len(x)):
        attacked=np.flatnonzero(run.injected[s])
        # Local uses the known exogenous trial definition only for evaluation windows.
        end=(a["start"] if scenario=="single_step" else a["end_inclusive"]) if not len(attacked) else int(attacked[-1])
        if scenario=="clean":end=a["end_inclusive"]
        later=np.flatnonzero(run.sends[s,end+1:,source])+end+1
        first=int(later[0]) if len(later) else end+1
        window=slice(first+1,min(first+11,cfg["T"]+1))
        weight=float(run.weights[s,first,edge])
        restored=np.flatnonzero(run.weights[s,first:,edge]>=.5)
        delay=int(restored[0]) if len(restored) else cfg["T"]-first
        rows.append({"first_return_time":first,"first_return_weight":weight,"first_return_low":float(weight<.5),
            "receiver_recovery10_mse":float(error[s,window,target].mean()),"network_recovery10_mse":float(error[s,window].mean()),
            "return_restore_delay":delay})
    return rows


def tests_before_screen(plan,base):
    old=Path("simulation/runs/2026-11-10_five_node_v2")
    cfg=json.loads((old/"config.json").read_text(encoding="utf-8"));m=Model.build(cfg)
    with np.load(old/"test_inputs.npz") as f:x,y,seeds,schedule=(f[k][:3] for k in ("x","y","seeds","reference_schedule"))
    r=simulate(m,x,y,seeds,"yang","step",schedule)
    with np.load(old/"reference_schedule/yang__step.npz") as f:assert np.array_equal(r.estimates,f["estimates"][:3])
    for method in ("reference_reset","reference_soft"):
        g=reference_evidence(np.array([.5,.5]),np.array([100.,100.]),np.array([100.,.5]),np.array([True,True]),method,base)
        assert g[0]<1e-10 and g[1]>40
        g2=reference_evidence(np.array([10.]),np.array([100.]),np.array([100.]),np.array([True]),method,base)
        assert np.isclose(g2[0],9.)
    hetero=copy.deepcopy(base);hetero.update({k:v for k,v in plan["models"][1].items() if k in {"A","H_matrices"}})
    h=Model.build(hetero);assert np.array_equal(h.H,np.asarray(hetero["H_matrices"]))
    return {"passed":True,"unchanged_yang_step_output":True,"recovery_gate_does_not_hide_current_spatial_anomaly":True,"heterogeneous_builder_exact":True}


def main(plan_path,out):
    out=Path(out)
    if out.exists():raise FileExistsError("Preserve prior runs")
    out.mkdir(parents=True)
    plan=json.loads(Path(plan_path).read_text(encoding="utf-8-sig"));base=json.loads(Path(plan["base_config"]).read_text(encoding="utf-8-sig"))
    write_json(out/"plan.json",plan);write_json(out/"extension_checks.json",tests_before_screen(plan,base))
    source=out/"sources";source.mkdir()
    for f in Path("simulation").glob("*.py"):shutil.copy2(f,source/f.name)
    from datetime import datetime,timezone
    write_json(out/"registration.json",{"created_utc":datetime.now(timezone.utc).isoformat(),"plan_sha256":hashlib.sha256(Path(plan_path).read_bytes()).hexdigest(),"source_sha256":{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in source.iterdir()},"new_test_data_not_generated":True})
    allrows=[];started=time.perf_counter()
    for setting in plan["models"]:
        cfg=copy.deepcopy(base)
        for k in ("A","H_matrices"):
            if k in setting:cfg[k]=setting[k]
        for split,v in plan["splits"].items():cfg[split+"_seeds"]=v
        cfg["attack"]["matched_replay_time_lag"]=plan["schedule"]["replay_lag"]
        cfg["methods"]=["interval_scale"]
        folder=out/setting["id"];folder.mkdir();write_json(folder/"config.json",cfg)
        model=Model.build(cfg)
        seeds=np.concatenate([seed_range(cfg,s) for s in ("train","calibration","validation")])
        x,y=generate_data(model,seeds)
        scheduler={"repeated_gap_pattern":plan["schedule"]["gap_pattern"],"node_phase_step":plan["schedule"]["phase_step"],"matched_replay_time_lag":plan["schedule"]["replay_lag"]}
        schedule=repeated_schedule(cfg,len(seeds),scheduler)
        ref=simulate(model,x,y,seeds,"yang",schedule=schedule)
        fitted,rawcontrol,cap=calibrate_mode(model,(x,y),seeds,ref,"reference_schedule",folder)["interval_scale"]
        nt,nc=cfg["train_seeds"]["count"],cfg["calibration_seeds"]["count"]
        vx,vy,vs,vt=x[nt+nc:],y[nt+nc:],seeds[nt+nc:],schedule[nt+nc:]
        raw=simulate(model,vx,vy,vs,"interval_scale",schedule=vt,calibration=fitted,control=rawcontrol,cap=cap)
        controls={"interval_scale":rawcontrol};hist=[]
        for method in plan["methods"]:
            if method in {"spatial_soft","spatial_hard","reference_reset","reference_soft"}:
                ctrl=fit_control(method,raw.observations,fitted,cfg)
                for _ in range(plan["reference_rule"]["normal_control_rounds"]):
                    rv=simulate(model,vx,vy,vs,method,schedule=vt,calibration=fitted,control=ctrl,cap=cap)
                    ctrl=fit_control(method,rv.observations,fitted,cfg)
                rv=simulate(model,vx,vy,vs,method,schedule=vt,calibration=fitted,control=ctrl,cap=cap)
                hist.append({"method":method,"control":ctrl,"normal_low_weight_rate":float(np.mean(rv.observations["weight"]<.5)),"normal_mean_weight":float(np.mean(rv.observations["weight"]))})
                controls[method]=ctrl
            elif method not in controls:controls[method]=1.0
        write_json(folder/"frozen_controls.json",{"controls":controls,"cap":cap,"shared_calibration":"interval_scale_calibration.npz","validation":hist})
        tseeds=seed_range(cfg,"test");xx,yy=generate_data(model,tseeds);ss=repeated_schedule(cfg,len(tseeds),scheduler)
        np.savez_compressed(folder/"test_inputs.npz",x=xx,y=yy,seeds=tseeds,schedule=ss)
        for method in plan["methods"]:
            for scenario in plan["scenarios"]:
                run=simulate(model,xx,yy,tseeds,method,scenario,ss,fitted,controls[method],cap)
                metrics,_=basic_metrics(model,run,xx)
                # Evaluation uses the same exogenous schedule even for the no-communication local baseline.
                evaluation_sends=run.sends
                if method=="local":run.sends=ss
                rr=recovery_metrics(model,run,xx,scenario)
                run.sends=evaluation_sends
                for s,seed in enumerate(tseeds):
                    row={"model":setting["id"],"method":method,"scenario":scenario,"seed":int(seed)}
                    row.update({k:float(v[s]) for k,v in metrics.items()});row.update(rr[s]);allrows.append(row)
                assert np.isfinite(run.estimates).all()
                if method!="local":assert np.array_equal(run.sends,ss)
                np.savez_compressed(folder/(method+"__"+scenario+".npz"),estimates=run.estimates,weights=run.weights,sends=run.sends,injected=run.injected,replay_source=run.replay_source)
                print(json.dumps({"model":setting["id"],"method":method,"scenario":scenario,"attack_mse":float(metrics["mse_attack_window"].mean()),"receiver_recovery10":float(np.mean([v["receiver_recovery10_mse"] for v in rr])),"return_weight":float(np.mean([v["first_return_weight"] for v in rr]))}),flush=True)
        write_csv(out/"per_seed_metrics.csv",allrows)
    comparisons=[];lookup={(r["model"],r["method"],r["scenario"],r["seed"]):r for r in allrows}
    for setting in plan["models"]:
        for scenario in plan["scenarios"]:
            if scenario=="clean":continue
            for candidate in ("reference_reset","reference_soft"):
                for baseline in ("interval_scale","spatial_soft","reference_reset","local","fresh_only_cap"):
                    if candidate==baseline:continue
                    a=np.array([lookup[setting["id"],candidate,scenario,int(s)]["receiver_recovery10_mse"] for s in tseeds]);b=np.array([lookup[setting["id"],baseline,scenario,int(s)]["receiver_recovery10_mse"] for s in tseeds])
                    mean,lo,hi=paired_interval(a-b)
                    comparisons.append({"model":setting["id"],"scenario":scenario,"candidate":candidate,"baseline":baseline,"receiver_recovery_relative_gain":float(-mean/b.mean()),"paired_mean_difference":mean,"bootstrap95_low":lo,"bootstrap95_high":hi})
    write_csv(out/"recovery_comparisons.csv",comparisons)
    write_json(out/"execution.json",{"completed":True,"elapsed_seconds":time.perf_counter()-started,"method_trajectories":len(allrows),"independent_seeds":len(tseeds),"scope":"exploratory screen, not novelty proof"})
    print("COMPLETED "+str(out.resolve()),flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--plan",default="simulation/reference_exploration_plan.json");p.add_argument("--out",required=True);a=p.parse_args();main(a.plan,a.out)
