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
import scipy
import matplotlib
from model import Model, seed_range, generate_data
from calibration import Calibration, fit_control, interval_bins, quantile
from engine import simulate, subset_observations, basic_metrics
from verify import verify


DEFENDED={"spatial_hard","pooled","interval_scale","interval_tail","zhou_random"}
SCORED={"spatial_hard","pooled","interval_scale","interval_tail"}


def write_json(path,obj):
    def default(x):
        if isinstance(x,np.ndarray):return x.tolist()
        if isinstance(x,np.generic):return x.item()
        raise TypeError(type(x).__name__)
    Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=default),encoding="utf-8")


def write_csv(path,rows):
    with Path(path).open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def observation_summary(obs,cfg):
    return {"packets":len(obs["edge"]),"low_weight_rate":float(np.mean(obs["weight"]<cfg["low_weight_threshold"])),
            "mean_weight":float(np.mean(obs["weight"]))}


def calibrate_mode(model,data,seeds,reference,protocol,out):
    cfg=model.cfg
    x,y=data
    nt,nc=cfg["train_seeds"]["count"],cfg["calibration_seeds"]["count"]
    nv=cfg["validation_seeds"]["count"]
    schedule=reference.sends if protocol=="reference_schedule" else None
    train=subset_observations(reference.observations,0,nt)
    cal=subset_observations(reference.observations,nt,nt+nc)
    val=subset_observations(reference.observations,nt+nc,nt+nc+nv)
    cap=quantile(reference.cap_norms[:nt].ravel(),cfg["cap_quantile"])
    policies={};history=[];fit_rows=[]
    for method in cfg["methods"]:
        if method not in DEFENDED:
            policies[method]=(None,1.0,cap)
            continue
        mode=method if method in {"pooled","interval_scale","interval_tail"} else "pooled"
        fitted=Calibration.fit(train,cal,cfg,mode) if method in SCORED else None
        control=fit_control(method,val,fitted,cfg)
        for it in range(cfg["calibration_rounds"] if fitted is not None else 0):
            run=simulate(model,x,y,seeds,method,schedule=schedule,calibration=fitted,control=control,cap=cap)
            own_train=subset_observations(run.observations,0,nt)
            own_cal=subset_observations(run.observations,nt,nt+nc)
            own_val=subset_observations(run.observations,nt+nc,nt+nc+nv)
            history.append({"method":method,"stage":"normal_distribution_iteration","iteration":it,
                            "control_used":control,**observation_summary(own_val,cfg)})
            fitted=Calibration.fit(own_train,own_cal,cfg,mode)
            control=fit_control(method,own_val,fitted,cfg)
        vx,vy=x[nt+nc:],y[nt+nc:]
        vs=seeds[nt+nc:]
        sched_val=None if schedule is None else schedule[nt+nc:]
        for it in range(cfg["validation_control_rounds"]):
            run=simulate(model,vx,vy,vs,method,schedule=sched_val,calibration=fitted,control=control,cap=cap)
            history.append({"method":method,"stage":"control_iteration","iteration":it,
                            "control_used":control,**observation_summary(run.observations,cfg)})
            control=fit_control(method,run.observations,fitted,cfg)
        final=simulate(model,vx,vy,vs,method,schedule=sched_val,calibration=fitted,control=control,cap=cap)
        metrics,_=basic_metrics(model,final,vx)
        summary={"method":method,"stage":"final_validation","control_used":control,
                 **observation_summary(final.observations,cfg),"mse":float(metrics["mse_all"].mean()),
                 "edge_messages":float(metrics["edge_messages"].mean())}
        history.append(summary)
        if fitted is not None:
            fitted.save(out/(method+"_calibration.npz"))
            for e in range(len(model.edges)):
                for b in range(len(cfg["interval_upper_bounds"])):
                    fit_rows.append({"method":method,"edge":e,"interval_bin":b,
                                     "train_n":int(fitted.train_counts[e,b]),"cal_n":int(fitted.cal_counts[e,b]),
                                     "fallback":bool(fitted.fallback[e,b]),"time_q":float(fitted.time_q[e,b])})
        policies[method]=(fitted,control,cap)
        print(json.dumps({"protocol":protocol,**summary}),flush=True)
    write_json(out/"normal_calibration_history.json",history)
    write_json(out/"policy_controls.json",{m:{"control":v[1],"cap":v[2]} for m,v in policies.items()})
    write_csv(out/"calibration_counts.csv",fit_rows)
    return policies


def paired_interval(diff,seed=7203):
    d=np.asarray(diff,float)
    rng=np.random.default_rng(seed)
    boot=d[rng.integers(0,len(d),size=(2000,len(d)))].mean(axis=1)
    return [float(d.mean()),float(np.quantile(boot,.025)),float(np.quantile(boot,.975))]


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--config",default="simulation/config.json")
    p.add_argument("--run-id",required=True)
    a=p.parse_args()
    cfg=json.loads(Path(a.config).read_text(encoding="utf-8-sig"))
    out=Path("simulation/runs")/a.run_id
    if out.exists():raise FileExistsError("Run exists; do not overwrite research evidence")
    out.mkdir(parents=True)
    sources=out/"sources";sources.mkdir()
    for file in Path("simulation").glob("*.py"):shutil.copy2(file,sources/file.name)
    for dependency in ("requirements.txt","requirements-lock.txt"):
        shutil.copy2(Path("simulation")/dependency,sources/dependency)
    shutil.copy2("simulation/run.ps1",sources/"run.ps1")
    write_json(out/"config.json",cfg)
    write_json(out/"environment.json",{"python":sys.version,"numpy":np.__version__,"scipy":scipy.__version__,"matplotlib":matplotlib.__version__,
        "source_sha256":{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sources.iterdir()},
        "scope":"Research adaptation, not exact reproduction of original Yang 2014 or Zhou 2022 experiments"})
    started=time.perf_counter()
    verification=verify(a.config,out/"verification.json")
    print("Verification passed: "+json.dumps(verification),flush=True)
    model=Model.build(cfg)
    np.savez_compressed(out/"nominal_gains.npz",gains=model.gains,local_gains=model.local_gains,covariance=model.nominal_covariance)
    devseeds=np.concatenate([seed_range(cfg,s) for s in ("train","calibration","validation")])
    tx,ty=generate_data(model,devseeds)
    ref=simulate(model,tx,ty,devseeds,"yang")
    testseeds=seed_range(cfg,"test")
    x,y=generate_data(model,testseeds)
    testref=simulate(model,x,y,testseeds,"yang")
    np.savez_compressed(out/"test_inputs.npz",x=x,y=y,seeds=testseeds,reference_schedule=testref.sends)
    rows=[];group_rows=[];all_loss={};curve_data={}
    for protocol in ("reference_schedule","closed_loop"):
        folder=out/protocol;folder.mkdir()
        policies=calibrate_mode(model,(tx,ty),devseeds,ref,protocol,folder)
        schedule=testref.sends if protocol=="reference_schedule" else None
        for method in cfg["methods"]:
            fitted,control,cap=policies[method]
            for scenario in cfg["test_scenarios"]:
                begin=time.perf_counter()
                run=simulate(model,x,y,testseeds,method,scenario,schedule,fitted,control,cap)
                metrics,sq=basic_metrics(model,run,x)
                elapsed=time.perf_counter()-begin
                curve_data[protocol+"__"+method+"__"+scenario]=sq.mean(axis=(0,2))
                all_loss[protocol,method,scenario]=metrics
                for s,seed in enumerate(testseeds):
                    row={"protocol":protocol,"method":method,"scenario":scenario,"seed":int(seed)}
                    row.update({k:float(v[s]) for k,v in metrics.items()});row["batch_runtime_seconds"]=elapsed;rows.append(row)
                np.savez_compressed(folder/(method+"__"+scenario+".npz"),estimates=run.estimates,sends=run.sends,
                    weights=run.weights,cache_bad=run.cache_bad,injected=run.injected,replay_source=run.replay_source,clipped=run.clipped)
                if scenario=="clean" and len(run.observations["edge"]):
                    obs=run.observations;b=interval_bins(obs["delta"],cfg)
                    for edge in range(len(model.edges)):
                        for bin_id in range(len(cfg["interval_upper_bounds"])):
                            keep=(obs["edge"]==edge)&(b==bin_id)
                            if not np.any(keep):continue
                            group_rows.append({"protocol":protocol,"method":method,"edge":edge,"interval_bin":bin_id,"n":int(keep.sum()),
                                "low_weight_rate":float(np.mean(obs["weight"][keep]<cfg["low_weight_threshold"])),
                                "mean_weight":float(np.mean(obs["weight"][keep])),"timeout_fraction":float(np.mean(obs["reason"][keep]==2)),
                                "temporal_tail_rate":float(np.mean(obs["temporal_ratio"][keep]>1)) if method in SCORED else np.nan})
                print(json.dumps({"protocol":protocol,"method":method,"scenario":scenario,"attack_window_mse":float(metrics["mse_attack_window"].mean()),
                    "messages":float(metrics["edge_messages"].mean()),"seconds":round(elapsed,2)}),flush=True)
    write_csv(out/"per_seed_metrics.csv",rows)
    write_csv(out/"normal_group_metrics.csv",group_rows)
    np.savez_compressed(out/"mse_curves.npz",**curve_data)
    summary=[];comparisons=[]
    for (protocol,method,scenario),metrics in all_loss.items():
        clean=all_loss[protocol,method,"clean"]
        summary.append({"protocol":protocol,"method":method,"scenario":scenario,
            **{k:float(np.nanmean(v)) if np.any(np.isfinite(v)) else None for k,v in metrics.items()},
            "attack_excess_loss":float(np.mean(metrics["mse_attack_window"]-clean["mse_attack_window"]))})
        if method=="interval_tail":
            for baseline in ("interval_scale","pooled","zhou_random","capped","local"):
                difference=metrics["mse_attack_window"]-all_loss[protocol,baseline,scenario]["mse_attack_window"]
                mean,lo,hi=paired_interval(difference)
                comparisons.append({"protocol":protocol,"scenario":scenario,"method":"interval_tail","baseline":baseline,
                                    "metric":"mse_attack_window","paired_mean_difference":mean,"bootstrap95_low":lo,"bootstrap95_high":hi})
    write_json(out/"summary.json",summary);write_csv(out/"paired_comparisons.csv",comparisons)
    write_json(out/"completion.json",{"completed":True,"elapsed_seconds":time.perf_counter()-started,"test_trajectories_per_method_scenario":len(testseeds),
        "no_test_based_parameter_updates":True,"multiple_comparisons":"Exploratory intervals; no multiplicity correction; not confirmatory significance claims"})
    from report import build_report
    build_report(out)
    print("COMPLETED "+str(out.resolve()),flush=True)


if __name__=="__main__":main()
