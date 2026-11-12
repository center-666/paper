"""Attacker-visible historical packet selection probe on frozen normal trajectories.

This diagnoses feasible candidate payloads, not a closed-loop damage result.
Receiver measurements are used ONLY after selection to evaluate actual scores.
"""
from __future__ import annotations
import argparse,hashlib,json,shutil
from pathlib import Path
import numpy as np
from model import Model,generate_data
from calibration import Calibration,quadratic,interval_bins
from engine import simulate
from run_study import write_json,write_csv
from validation_suite import repeated_schedule


def choose(mode,candidates,current,previous,delta,calibration,edge,model,budget):
    """No receiver y, local estimate, latent state or future inputs are in this API."""
    if not len(candidates):return None
    difference=candidates-current
    H=model.H[model.edges[edge,1]]
    projected=difference@H.T
    spatial_proxy=quadratic(projected,np.zeros(len(current)),calibration.space_precision[edge])/calibration.space_q[edge]
    b=int(interval_bins(np.asarray(delta),model.cfg))
    tr=candidates-model.powers[delta]@previous
    time_score=quadratic(tr,calibration.time_mu[edge,b],calibration.time_precision[edge,b])/calibration.time_q[edge,b]
    displacement=np.sum((difference@model.A.T)**2,axis=1)
    if mode=="nearest":idx=int(np.argmin(displacement))
    elif mode=="fixed_lag":idx=max(0,len(candidates)-8)
    else:
        eligible=np.flatnonzero((spatial_proxy<=budget)&(time_score<=1.0))
        if not len(eligible):return None
        idx=int(eligible[np.argmax(displacement[eligible])])
    return idx,float(spatial_proxy[idx]),float(time_score[idx]),float(displacement[idx])


def main(out):
    out=Path(out)
    if out.exists():raise FileExistsError("Do not overwrite")
    out.mkdir(parents=True)
    plan={"scope":"Frozen NORMAL sender streams; no receiver feedback damage claim","seeds_start":740000,"count":64,
          "methods":["fixed_lag","nearest","risk_greedy"],"risk_budgets":[.25,1.0],"dictionary":"all earlier actual sends, latest64 packets; current packet excluded",
          "attacker_information":["current transmitted state estimate","previously transmitted same-sender estimates and times","last delivered substituted payload","public A,H,calibration constants"],
          "hidden":["receiver current measurement","receiver estimate","true state","future sends/values"],
          "proxy_warning":"spatial projection cost is not a guarantee of actual spatial detector acceptance"}
    write_json(out/"plan.json",plan);shutil.copy2(__file__,out/Path(__file__).name)
    records=[]
    for setting in ("original","heterogeneous_sensing"):
        old=Path("simulation/exploration_runs/2026-11-10_reference_screen_v1")/setting
        cfg=json.loads((old/"config.json").read_text(encoding="utf-8"));cfg["T"]=400
        model=Model.build(cfg);cal=Calibration.load(old/"interval_scale_calibration.npz")
        ctrl=json.loads((old/"frozen_controls.json").read_text(encoding="utf-8"))["controls"]["interval_scale"]
        seeds=np.arange(plan["seeds_start"],plan["seeds_start"]+plan["count"]);x,y=generate_data(model,seeds)
        sched=repeated_schedule(cfg,len(seeds),{"repeated_gap_pattern":[1,2,3,4,6,8,6,4,3,3],"node_phase_step":3,"matched_replay_time_lag":80})
        normal=simulate(model,x,y,seeds,"yang",schedule=sched,collect=False)
        edge=np.flatnonzero(np.all(model.edges==[0,1],axis=1))[0]
        for trial,seed in enumerate(seeds):
            times=np.flatnonzero(sched[trial,:,0])
            stream=normal.estimates[trial,times,0]
            for mode in plan["methods"]:
                budgets=plan["risk_budgets"] if mode=="risk_greedy" else [None]
                for budget in budgets:
                    previous=stream[0].copy()
                    for r in range(1,len(times)):
                        t=int(times[r]);delta=int(times[r]-times[r-1]);current=stream[r]
                        selected=None
                        if cfg["attack"]["start"]<=t<=cfg["attack"]["end_inclusive"]:
                            begin=max(0,r-64);candidates=stream[begin:r]
                            selected=choose(mode,candidates,current,previous,delta,cal,edge,model,budget)
                            index=begin+selected[0] if selected is not None else None
                            payload=stream[index] if index is not None else current
                            # Evaluation is deliberately outside attacker function.
                            residual=y[trial,t,1]-model.H[1]@payload
                            space=quadratic(residual,cal.space_mu[edge],cal.space_precision[edge])/cal.space_q[edge]
                            b=int(interval_bins(np.asarray(delta),cfg))
                            temporal=quadratic(payload-model.powers[delta]@previous,cal.time_mu[edge,b],cal.time_precision[edge,b])/cal.time_q[edge,b]
                            score=cfg["alpha"]*max(float(space)-1,0)+(1-cfg["alpha"])*max(float(temporal)-1,0)
                            weight=np.exp(-ctrl*score)
                            difference=payload-current
                            records.append({"model":setting,"seed":int(seed),"mode":mode,"proxy_budget":budget,"time":t,"selected":index is not None,
                                "source_time":int(times[index]) if index is not None else -1,"age":int(t-times[index]) if index is not None else 0,
                                "spatial_proxy":selected[1] if selected else float("nan"),"actual_spatial_ratio":float(space),"actual_temporal_ratio":float(temporal),
                                "actual_weight":float(weight),"squared_displacement":float(np.sum(difference**2)),"one_step_weighted_influence_squared":float(np.sum((cfg["epsilon"]*model.A@(weight*difference))**2))})
                        else:payload=current
                        previous=payload.copy()
    write_csv(out/"packet_results.csv",records)
    summary=[]
    for setting in ("original","heterogeneous_sensing"):
        for mode,budget in [("fixed_lag",None),("nearest",None),("risk_greedy",.25),("risk_greedy",1.)]:
            rr=[r for r in records if r["model"]==setting and r["mode"]==mode and r["proxy_budget"]==budget]
            picked=[r for r in rr if r["selected"]]
            summary.append({"model":setting,"mode":mode,"budget":budget,"opportunities":len(rr),"selected_rate":len(picked)/len(rr),
                "mean_displacement_squared_per_opportunity":float(np.mean([r["squared_displacement"] for r in rr])),
                "mean_weighted_influence_squared_per_opportunity":float(np.mean([r["one_step_weighted_influence_squared"] for r in rr])),
                "selected_low_weight_rate":float(np.mean([r["actual_weight"]<.5 for r in picked])) if picked else None,
                "mean_content_age":float(np.mean([r["age"] for r in picked])) if picked else None})
    write_json(out/"summary.json",summary);write_json(out/"checks.json",{"legal_history_only":all(r["source_time"]<r["time"] for r in records if r["selected"]),
        "no_closed_loop_damage_claim":True,"source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    print(json.dumps(summary))


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",required=True);a=p.parse_args();main(a.out)
