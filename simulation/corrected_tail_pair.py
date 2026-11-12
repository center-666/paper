"""Correct the calibration-data mismatch identified by independent code review.

No model/attack selection changes; fresh holdout seeds; only two fixed-scale tail variants.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time
import numpy as np
from calibration import Calibration,fit_control,interval_bins,quadratic,quantile
from engine import simulate,basic_metrics
from model import Model,generate_data,seed_range
from run_study import write_json,write_csv
from validation_suite import repeated_schedule,diagnostics,audit_run


def pair_policies(model,source_dir,plan,out):
    cfg=model.cfg
    scale=Calibration.load(source_dir/"interval_scale_calibration.npz")
    controls=json.loads((source_dir/"frozen_controls.json").read_text(encoding="utf-8"))
    control=controls["interval_scale"]["control"];cap=controls["interval_scale"]["cap"]
    cseeds=seed_range(cfg,"calibration");vseeds=seed_range(cfg,"validation")
    seeds=np.r_[cseeds,vseeds];x,y=generate_data(model,seeds)
    setting=out.name
    external=repeated_schedule(cfg,len(seeds),plan) if setting=="repeated_gaps" else None
    schedule=simulate(model,x,y,seeds,"yang",schedule=external,collect=False).sends
    frozen_run=simulate(model,x,y,seeds,"interval_scale",schedule=schedule,calibration=scale,control=control,cap=cap)
    obs=frozen_run.observations;ncal=len(cseeds)
    cal={k:v[obs["trajectory"]<ncal] for k,v in obs.items()}
    val={k:v[obs["trajectory"]>=ncal] for k,v in obs.items()}
    np.savez_compressed(out/"shared_normal_calibration_residuals.npz",**cal,seeds=cseeds)
    pooled=copy.deepcopy(scale);tail=copy.deepcopy(scale)
    pooled.mode="interval_scale";tail.mode="tail_shared_scale"
    bins=interval_bins(cal["delta"],cfg)
    for e in range(len(model.edges)):
        selected=(cal["edge"]==e)&cal["time_valid"]
        scores=quadratic(cal["temporal"][selected],scale.time_mu[e,bins[selected]],scale.time_precision[e,bins[selected]])
        common=max(quantile(scores,cfg["marginal_quantile"]),1e-10)
        for b in range(len(cfg["interval_upper_bounds"])):
            mask=bins[selected]==b
            pooled.time_q[e,b]=common
            tail.time_q[e,b]=max(quantile(scores[mask],cfg["marginal_quantile"]),1e-10) if mask.sum()>=cfg["minimum_bin_samples"] and not scale.fallback[e,b] else common
            pooled.cal_counts[e,b]=tail.cal_counts[e,b]=mask.sum()
    for attr in ("space_mu","space_precision","space_q","time_mu","time_precision","train_counts","cal_counts","fallback"):
        assert np.array_equal(getattr(pooled,attr),getattr(tail,attr))
    policies={};hist=[]
    for method,calibration in (("interval_scale",pooled),("tail_shared_scale",tail)):
        value=fit_control(method,val,calibration,cfg)
        for it in range(cfg["validation_control_rounds"]):
            run=simulate(model,x[ncal:],y[ncal:],vseeds,method,schedule=schedule[ncal:],calibration=calibration,control=value,cap=cap)
            hist.append({"method":method,"iteration":it,"control":value,"low_weight_rate":float(np.mean(run.observations["weight"]<.5))})
            value=fit_control(method,run.observations,calibration,cfg)
        final=simulate(model,x[ncal:],y[ncal:],vseeds,method,schedule=schedule[ncal:],calibration=calibration,control=value,cap=cap)
        hist.append({"method":method,"stage":"final_validation","control":value,"low_weight_rate":float(np.mean(final.observations["weight"]<.5)),"mean_weight":float(np.mean(final.observations["weight"]))})
        calibration.save(out/(method+"_calibration.npz"));policies[method]=(calibration,value,cap)
    write_json(out/"validation_history.json",hist)
    write_json(out/"shared_calibration_audit.json",{"passed":True,"shared_residuals_sha256":hashlib.sha256((out/"shared_normal_calibration_residuals.npz").read_bytes()).hexdigest(),
        "identical_fields":["space_mu","space_precision","space_q","time_mu","time_precision","train_counts","cal_counts","fallback"],
        "same_tail_calibration_samples":True,"differences_allowed":["time_q pooled vs interval-grouped","normal-validation fitted scalar weight sensitivity"],
        "source_scale_calibration_sha256":hashlib.sha256((source_dir/"interval_scale_calibration.npz").read_bytes()).hexdigest()})
    write_json(out/"frozen_controls.json",{m:{"control":v[1],"cap":v[2]} for m,v in policies.items()})
    return policies


def main():
    p=argparse.ArgumentParser();p.add_argument("--source",required=True);p.add_argument("--out",required=True);args=p.parse_args()
    source=Path(args.source);out=Path(args.out)
    if out.exists():raise FileExistsError("Do not overwrite earlier evidence")
    out.mkdir(parents=True)
    plan=json.loads((source/"plan.json").read_text(encoding="utf-8"))
    plan["plan_id"]="2026-11-10_corrected_shared_data_pair_v2"
    plan["methods"]=["interval_scale","tail_shared_scale"]
    plan["splits"]["test"]={"start":240000,"count":128}
    plan["amendment"]={"reason":"Independent reviewer found baseline pooled q and candidate binned q came from different normal calibration trajectories in locked_v1",
        "repair":"Both q variants recomputed from exactly the same frozen scale-policy calibration residuals; all non-tail statistics identical",
        "previous_results_seen":True,"fresh_test_seeds":True,"model_attacks_regimes_gate_unchanged":True,
        "scope":"Corrected direct ablation only; original nine-method deployment comparison remains preserved at source"}
    write_json(out/"plan.json",plan)
    sources=out/"sources";sources.mkdir()
    for f in Path("simulation").glob("*.py"):shutil.copy2(f,sources/f.name)
    shutil.copy2("simulation/requirements-lock.txt",sources/"requirements-lock.txt")
    from datetime import datetime,timezone
    write_json(out/"preregistration.json",{"created_utc":datetime.now(timezone.utc).isoformat(),"source_run":str(source),
        "plan_sha256":hashlib.sha256((out/"plan.json").read_bytes()).hexdigest(),"source_sha256":{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sources.iterdir()},
        "python":sys.version,"numpy":np.__version__,"fresh_test_data_not_generated":True})
    rows=[];windows=[];groups=[];audit=[];curves={};started=time.perf_counter()
    for regime in plan["regimes"]:
        setting=regime["id"];folder=out/setting;folder.mkdir()
        cfg=json.loads((source/setting/"config.json").read_text(encoding="utf-8"));cfg["test_seeds"]=plan["splits"]["test"];cfg["methods"]=plan["methods"]
        write_json(folder/"config.json",cfg);model=Model.build(cfg)
        policies=pair_policies(model,source/setting,plan,folder)
        seeds=seed_range(cfg,"test");x,y=generate_data(model,seeds)
        external=repeated_schedule(cfg,len(seeds),plan) if setting=="repeated_gaps" else None
        schedule=simulate(model,x,y,seeds,"yang",schedule=external,collect=False).sends
        np.savez_compressed(folder/"test_inputs.npz",x=x,y=y,seeds=seeds,schedule=schedule)
        scenarios=plan["common_scenarios"]+(plan["extra_repeated_scenarios"] if setting=="repeated_gaps" else [])
        for method in plan["methods"]:
            fitted,control,cap=policies[method]
            for scenario in scenarios:
                run=simulate(model,x,y,seeds,method,scenario,schedule,fitted,control,cap)
                metrics,sq=basic_metrics(model,run,x);pairs=audit_run(model,run,x,seeds,schedule,scenario,metrics)
                audit.append({"setting":setting,"method":method,"scenario":scenario,"passed":True,"matched_replay_pairs":pairs})
                for s,seed in enumerate(seeds):
                    row={"setting":setting,"method":method,"scenario":scenario,"seed":int(seed)};row.update({k:float(v[s]) for k,v in metrics.items()});rows.append(row)
                ww,gg=diagnostics(model,run,seeds,setting,method,scenario,plan);windows+=ww;groups+=gg
                curves[setting+"__"+method+"__"+scenario]=sq.mean(axis=(0,2))
                np.savez_compressed(folder/(method+"__"+scenario+".npz"),estimates=run.estimates,sends=run.sends,weights=run.weights,
                    injected=run.injected,replay_source=run.replay_source,cache_bad=run.cache_bad,clipped=run.clipped)
                print(json.dumps({"setting":setting,"method":method,"scenario":scenario,"mse":float(metrics["mse_attack_window"].mean())}),flush=True)
        write_csv(out/"per_seed_metrics.csv",rows);write_csv(out/"window_metrics.csv",windows);write_csv(out/"normal_group_metrics.csv",groups)
        write_json(out/"run_audit.json",audit);np.savez_compressed(out/"curves.npz",**curves)
    write_json(out/"execution.json",{"completed":True,"elapsed_seconds":time.perf_counter()-started,"test_seed_count":len(seeds),"paired_method_trajectories":len(rows),"case_count":len(audit),"no_test_parameter_updates":True})
    from validation_summary import summarize
    summarize(out)
    print("COMPLETED "+str(out.resolve()),flush=True)


if __name__=="__main__":main()
