"""Predeclared follow-up validation; no test-driven parameter selection."""
from __future__ import annotations
import argparse
import copy
import csv
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time
import numpy as np
from calibration import Calibration, fit_control, interval_bins, quadratic, quantile
from engine import simulate, basic_metrics, subset_observations
from model import Model, generate_data, seed_range
from run_study import calibrate_mode, write_json, write_csv


def repeated_schedule(cfg, count, plan):
    gaps=plan["repeated_gap_pattern"]
    period=sum(gaps)
    assert plan["matched_replay_time_lag"] % period==0
    positions=np.r_[0,np.cumsum(gaps)[:-1]]
    schedule=np.zeros((count,cfg["T"],cfg["N"]),bool)
    for node in range(cfg["N"]):
        times=(positions+node*plan["node_phase_step"])%period
        schedule[:,:,node]=np.isin(np.arange(cfg["T"])%period,times)
    schedule[:,0]=True
    return schedule


def build_shared_tail(model, x, y, seeds, schedule, scale_policy, out):
    cfg=model.cfg
    scale,control,cap=scale_policy
    frozen=copy.deepcopy(scale)
    frozen.mode="tail_shared_scale"
    run=simulate(model,x,y,seeds,"interval_scale",schedule=schedule,calibration=scale,control=control,cap=cap)
    nt,nc=cfg["train_seeds"]["count"],cfg["calibration_seeds"]["count"]
    cal=subset_observations(run.observations,nt,nt+nc)
    b=interval_bins(cal["delta"],cfg)
    for edge in range(len(model.edges)):
        for bin_id in range(len(cfg["interval_upper_bounds"])):
            keep=(cal["edge"]==edge)&cal["time_valid"]&(b==bin_id)
            # Same fallback locations/scales as the source method; no hidden new pooling.
            if not scale.fallback[edge,bin_id] and keep.sum()>=cfg["minimum_bin_samples"]:
                score=quadratic(cal["temporal"][keep],scale.time_mu[edge,bin_id],scale.time_precision[edge,bin_id])
                frozen.time_q[edge,bin_id]=max(quantile(score,cfg["marginal_quantile"]),1e-10)
    for field in ("space_mu","space_precision","space_q","time_mu","time_precision","fallback"):
        assert np.array_equal(getattr(frozen,field),getattr(scale,field)),field
    val=subset_observations(run.observations,nt+nc,len(seeds))
    shared_control=fit_control("tail_shared_scale",val,frozen,cfg)
    hist=[]
    for iteration in range(cfg["validation_control_rounds"]):
        r=simulate(model,x[nt+nc:],y[nt+nc:],seeds[nt+nc:],"tail_shared_scale",schedule=schedule[nt+nc:],calibration=frozen,control=shared_control,cap=cap)
        hist.append({"iteration":iteration,"control":shared_control,"low_weight_rate":float(np.mean(r.observations["weight"]<.5))})
        shared_control=fit_control("tail_shared_scale",r.observations,frozen,cfg)
    final=simulate(model,x[nt+nc:],y[nt+nc:],seeds[nt+nc:],"tail_shared_scale",schedule=schedule[nt+nc:],calibration=frozen,control=shared_control,cap=cap)
    hist.append({"stage":"final_validation","control":shared_control,"low_weight_rate":float(np.mean(final.observations["weight"]<.5)),"mean_weight":float(np.mean(final.observations["weight"]))})
    frozen.save(out/"tail_shared_scale_calibration.npz")
    write_json(out/"tail_shared_scale_validation.json",hist)
    write_json(out/"shared_scale_audit.json",{"passed":True,"identical_fields":["space_mu","space_precision","space_q","time_mu","time_precision","fallback"],"source_method":"interval_scale","tail_data":"final scale-policy NORMAL calibration trajectories","control_data":"normal validation only","time_q_max_absolute_difference":float(np.max(np.abs(frozen.time_q-scale.time_q)))})
    return frozen,shared_control,cap


def finite_mean(x):
    return float(np.mean(x)) if len(x) else float("nan")


def diagnostics(model,run,seeds,setting,method,scenario,plan):
    cfg=model.cfg
    obs=run.observations
    windows=[];groups=[]
    bins=interval_bins(obs["delta"],cfg) if len(obs["edge"]) else np.empty(0,int)
    target=np.flatnonzero(np.all(model.edges==[cfg["attack"]["sender"],cfg["attack"]["receiver"]],axis=1))[0]
    for s,seed in enumerate(seeds):
        for name,(left,right) in plan["time_windows"].items():
            mask=(obs["trajectory"]==s)&(obs["time"]>=left)&(obs["time"]<=right)
            injected=mask&obs["injected"].astype(bool)
            cache=run.weights[s,left:right+1]
            windows.append({"setting":setting,"method":method,"scenario":scenario,"seed":int(seed),"window":name,
                "new_packets":int(mask.sum()),"low_weight_rate":finite_mean(obs["weight"][mask]<cfg["low_weight_threshold"]),
                "mean_new_weight":finite_mean(obs["weight"][mask]),"gap1_fraction":finite_mean(obs["delta"][mask]==1),
                "mean_gap":finite_mean(obs["delta"][mask]),"broadcast_rate":float(run.sends[s,left:right+1].mean()),
                "cache_weight_loss":float(np.mean(1-cache)) if method!="local" else float("nan"),
                "injected_weight_below_001":finite_mean(obs["weight"][injected]<.01),
                "target_cache_bad_fraction":float(run.cache_bad[s,left:right+1,target].mean()),
                "injected_clip_fraction":finite_mean(run.clipped[s,obs["time"][injected].astype(int),target])})
        if scenario=="clean":
            for b in range(len(cfg["interval_upper_bounds"])):
                mask=(obs["trajectory"]==s)&(bins==b)
                groups.append({"setting":setting,"method":method,"seed":int(seed),"bin":b,"n":int(mask.sum()),
                    "low_weight_rate":finite_mean(obs["weight"][mask]<cfg["low_weight_threshold"]),
                    "mean_weight":finite_mean(obs["weight"][mask])})
    return windows,groups


def audit_run(model,run,x,seeds,schedule,scenario,metrics):
    cfg=model.cfg;sender=cfg["attack"]["sender"]
    assert np.isfinite(run.estimates).all()
    assert np.all((run.weights>=0)&(run.weights<=1))
    if run.sends.any():assert np.array_equal(run.sends,schedule)
    if scenario=="clean":assert not run.injected.any()
    start,end=cfg["attack"]["start"],cfg["attack"]["end_inclusive"]
    pairs=0
    for s in range(len(seeds)):
        times=np.flatnonzero(run.injected[s])
        assert np.all((times>=start)&(times<=end))
        assert np.all(run.sends[s,times,sender])
        if scenario.startswith("replay"):
            old=run.replay_source[s,times]
            assert np.all((old>=0)&(old<times))
            assert np.all(run.sends[s,old,sender])
            if scenario=="replay_matched":
                expected=np.flatnonzero(schedule[s,start:end+1,sender])+start
                if run.sends.any():assert np.array_equal(times,expected)
                assert np.all(times-old==cfg["attack"]["matched_replay_time_lag"])
                assert np.array_equal(np.diff(times),np.diff(old))
                pairs+=max(0,len(times)-1)
    recomputed=np.sum((run.estimates[:,start+1:end+2]-x[:,start+1:end+2,None,:])**2,axis=-1).mean(axis=(1,2))
    assert np.allclose(recomputed,metrics["mse_attack_window"],rtol=1e-12,atol=1e-12)
    return pairs


def run(plan_path,out):
    out=Path(out)
    if out.exists():raise FileExistsError("Preserve old validation evidence; select a new run directory")
    out.mkdir(parents=True)
    plan=json.loads(Path(plan_path).read_text(encoding="utf-8-sig"))
    base=json.loads(Path(plan["base_config"]).read_text(encoding="utf-8-sig"))
    sources=out/"sources";sources.mkdir()
    for f in Path("simulation").glob("*.py"):shutil.copy2(f,sources/f.name)
    shutil.copy2("simulation/requirements-lock.txt",sources/"requirements-lock.txt")
    write_json(out/"plan.json",plan);write_json(out/"base_config.json",base)
    from datetime import datetime,timezone
    write_json(out/"preregistration.json",{"created_utc":datetime.now(timezone.utc).isoformat(),"plan_sha256":hashlib.sha256(Path(plan_path).read_bytes()).hexdigest(),
        "base_config_sha256":hashlib.sha256(Path(plan["base_config"]).read_bytes()).hexdigest(),"source_sha256":{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sources.iterdir()},
        "python":sys.version,"numpy":np.__version__,"test_data_not_generated_at_registration":True})
    rows=[];windows=[];groups=[];curves={};audit=[]
    started=time.perf_counter()
    for regime in plan["regimes"]:
        setting=regime["id"];folder=out/setting;folder.mkdir()
        cfg=copy.deepcopy(base)
        cfg["send_delta_squared"]=regime["delta_squared"]
        cfg["methods"]=[m for m in plan["methods"] if m!="tail_shared_scale"]
        for split,values in plan["splits"].items():cfg[split+"_seeds"]=values
        cfg["attack"]["low_bias_factor"]=plan["low_bias_factor"]
        cfg["attack"]["matched_replay_time_lag"]=plan["matched_replay_time_lag"]
        write_json(folder/"config.json",cfg)
        model=Model.build(cfg)
        devseeds=np.concatenate([seed_range(cfg,s) for s in ("train","calibration","validation")])
        dx,dy=generate_data(model,devseeds)
        external=None if regime["schedule"]=="normal_reference" else repeated_schedule(cfg,len(devseeds),plan)
        ref=simulate(model,dx,dy,devseeds,"yang",schedule=external)
        policies=calibrate_mode(model,(dx,dy),devseeds,ref,"reference_schedule",folder)
        policies["tail_shared_scale"]=build_shared_tail(model,dx,dy,devseeds,ref.sends,policies["interval_scale"],folder)
        write_json(folder/"frozen_controls.json",{m:{"control":v[1],"cap":v[2]} for m,v in policies.items()})
        testseeds=seed_range(cfg,"test")
        x,y=generate_data(model,testseeds)
        external=None if regime["schedule"]=="normal_reference" else repeated_schedule(cfg,len(testseeds),plan)
        testref=simulate(model,x,y,testseeds,"yang",schedule=external,collect=False)
        schedule=testref.sends
        np.savez_compressed(folder/"test_inputs.npz",x=x,y=y,seeds=testseeds,schedule=schedule)
        scenarios=plan["common_scenarios"]+(plan["extra_repeated_scenarios"] if setting=="repeated_gaps" else [])
        for method in plan["methods"]:
            fitted,control,cap=policies[method]
            for scenario in scenarios:
                run=simulate(model,x,y,testseeds,method,scenario,schedule,fitted,control,cap)
                metrics,sq=basic_metrics(model,run,x)
                pairs=audit_run(model,run,x,testseeds,schedule,scenario,metrics)
                audit.append({"setting":setting,"method":method,"scenario":scenario,"passed":True,"matched_replay_pairs":pairs})
                for s,seed in enumerate(testseeds):
                    row={"setting":setting,"method":method,"scenario":scenario,"seed":int(seed)}
                    row.update({k:float(v[s]) for k,v in metrics.items()});rows.append(row)
                ww,gg=diagnostics(model,run,testseeds,setting,method,scenario,plan);windows+=ww;groups+=gg
                curves[setting+"__"+method+"__"+scenario]=sq.mean(axis=(0,2))
                np.savez_compressed(folder/(method+"__"+scenario+".npz"),estimates=run.estimates,sends=run.sends,weights=run.weights,
                    injected=run.injected,replay_source=run.replay_source,cache_bad=run.cache_bad,clipped=run.clipped)
                print(json.dumps({"setting":setting,"method":method,"scenario":scenario,"mse":float(metrics["mse_attack_window"].mean())}),flush=True)
        # Checkpoints retain every setting if later work is interrupted.
        write_csv(out/"per_seed_metrics.csv",rows);write_csv(out/"window_metrics.csv",windows);write_csv(out/"normal_group_metrics.csv",groups)
        write_json(out/"run_audit.json",audit);np.savez_compressed(out/"curves.npz",**curves)
    write_json(out/"execution.json",{"completed":True,"elapsed_seconds":time.perf_counter()-started,"test_seed_count":plan["splits"]["test"]["count"],
        "paired_method_trajectories":len(rows),"case_count":len(audit),"no_test_parameter_updates":True})
    from validation_summary import summarize
    summarize(out)
    print("COMPLETED "+str(out.resolve()),flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--plan",default="simulation/validation_plan.json");p.add_argument("--out",required=True)
    args=p.parse_args();run(args.plan,args.out)
