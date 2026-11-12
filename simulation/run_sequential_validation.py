"""Registered phase-separated, equal-FPR-target sequential benchmark validation."""
from __future__ import annotations
import argparse,copy,hashlib,json,shutil,sys,time
from pathlib import Path
import numpy as np
from model import Model,generate_data,seed_range
from engine import simulate,basic_metrics
from cache_screen import get_schedule
from sequential_cache import PhaseStatistics,SequentialController,PHASES,DETECTORS,phase_of,phase_rates,retune_multipliers,save_episodes
from run_study import write_json,write_csv,quantile


def episode_rows(episodes,seeds,schedule,method,edge_label,scenario,warmup):
    out=[]
    for p,name in enumerate(PHASES):
        counts=np.zeros(len(seeds),int);alarms=counts.copy();censored=counts.copy()
        for ep in episodes:
            if phase_of(ep.start,warmup)!=p:continue
            if not ep.complete:censored[ep.trajectory]+=1;continue
            counts[ep.trajectory]+=1;alarms[ep.trajectory]+=ep.alarm
        for s,seed in enumerate(seeds):
            out.append({"schedule":schedule,"method":method,"edge_label":edge_label,"scenario":scenario,"seed":int(seed),"phase":name,
                "complete_episodes":int(counts[s]),"alarm_episodes":int(alarms[s]),"censored_episodes":int(censored[s]),
                "episode_alarm_rate":float(alarms[s]/counts[s]) if counts[s] else float("nan")})
    return out


def fit_schedule(cfg,plan,folder):
    model=Model.build(cfg);data={}
    for split in ("train","calibration","design","tune","normal_audit"):
        seeds=seed_range(cfg,split);x,y=generate_data(model,seeds);data[split]=(x,y,seeds,get_schedule(model,len(seeds)))
    x,y,seeds,schedule=data["train"]
    reference=simulate(model,x,y,seeds,"yang",schedule=schedule)
    cap=quantile(reference.cap_norms.ravel(),cfg["cap_quantile"])
    dx,dy,ds,sch=data["design"];choices=[]
    for half_life in plan["half_lives"]:
        controller=SequentialController(model,half_life=half_life)
        run=simulate(model,dx,dy,ds,"capped",schedule=sch,cap=cap,cache_monitor=controller,collect=False)
        mse=np.sum((run.estimates[:,cfg["warmup"]+1:]-dx[:,cfg["warmup"]+1:,None,:])**2,axis=-1).mean()
        choices.append({"half_life":half_life,"normal_design_mse":float(mse)})
    half_life=min(choices,key=lambda z:z["normal_design_mse"])["half_life"]
    episodes={}
    for split in ("train","calibration"):
        x,y,seeds,schedule=data[split];collector=SequentialController(model,half_life=half_life,record_residuals=True)
        simulate(model,x,y,seeds,"capped",schedule=schedule,cap=cap,cache_monitor=collector,collect=False)
        episodes[split]=collector.finish()
        save_episodes(folder/(split+"_episodes.npz"),episodes[split],cfg["max_interval"],cfg["n"])
    statistics=PhaseStatistics.fit(episodes["train"],episodes["calibration"],len(model.edges),cfg["n"],cfg["max_interval"],cfg["warmup"],
        plan["window_length"],plan["signed_cusum_reference"],cfg["covariance_ridge_relative"])
    statistics.save(folder/"phase_statistics.npz");write_csv(folder/"phase_sample_counts.csv",statistics.counts)
    tune=data["tune"];auditdata=data["normal_audit"];controls={};history=[];audit=[]
    for method in DETECTORS:
        multipliers=np.ones(3)
        for iteration in range(plan["threshold_tuning_rounds"]):
            x,y,seeds,schedule=tune;monitor=SequentialController(model,statistics,method,multipliers,half_life)
            simulate(model,x,y,seeds,"capped",schedule=schedule,cap=cap,cache_monitor=monitor,collect=False)
            eps=monitor.finish()
            history.append({"method":method,"round":iteration,"multipliers":multipliers.tolist(),"phase_rates":phase_rates(eps,cfg["warmup"])})
            multipliers=retune_multipliers(eps,cfg["warmup"])
        controls[method]=multipliers
        x,y,seeds,schedule=auditdata;monitor=SequentialController(model,statistics,method,multipliers,half_life)
        run=simulate(model,x,y,seeds,"capped",schedule=schedule,cap=cap,cache_monitor=monitor,collect=False)
        eps=monitor.finish();audit+=episode_rows(eps,seeds,folder.name,method,"normal_audit","clean",cfg["warmup"])
        print(json.dumps({"schedule":folder.name,"stage":"independent_normal_audit","method":method,
            "phase_rates":phase_rates(eps,cfg["warmup"])}),flush=True)
    write_json(folder/"frozen_controls.json",{"half_life":half_life,"half_life_candidates":choices,"cap":cap,"multipliers":controls})
    write_json(folder/"tuning_history.json",history);write_csv(folder/"normal_audit_rates.csv",audit)
    return model,statistics,controls,cap,half_life


def main(plan_path,out):
    out=Path(out)
    if out.exists():raise FileExistsError("Do not overwrite prior evidence")
    out.mkdir(parents=True)
    plan=json.loads(Path(plan_path).read_text(encoding="utf-8-sig"));base=json.loads(Path(plan["base_config"]).read_text(encoding="utf-8"))
    model_source=json.loads(Path("simulation/reference_exploration_plan.json").read_text(encoding="utf-8"))["models"][1]
    write_json(out/"plan.json",plan);sources=out/"sources";sources.mkdir()
    for file in Path("simulation").glob("*.py"):shutil.copy2(file,sources/file.name)
    shutil.copy2("simulation/requirements-lock.txt",sources/"requirements-lock.txt")
    from datetime import datetime,timezone
    write_json(out/"registration.json",{"created_utc":datetime.now(timezone.utc).isoformat(),"plan_sha256":hashlib.sha256(Path(plan_path).read_bytes()).hexdigest(),
        "source_sha256":{file.name:hashlib.sha256(file.read_bytes()).hexdigest() for file in sources.iterdir()},"python":sys.version,"numpy":np.__version__,
        "future_test_generated":False,"prior_exploratory_results_seen":True})
    rows=[];ep_rows=[];audits=[];curves={};started=time.perf_counter()
    for schedule_name,pattern in plan["schedules"].items():
        folder=out/schedule_name;folder.mkdir();cfg=copy.deepcopy(base)
        cfg.update(A=model_source["A"],H_matrices=model_source["H_matrices"],cache_schedule_pattern=pattern,cache_schedule_phase=plan["phase_step"])
        for split,v in plan["splits"].items():cfg[split+"_seeds"]=v
        cfg["attack"].update(matched_replay_time_lag=80,low_bias_factor=.25)
        write_json(folder/"config.json",cfg)
        model,statistics,controls,cap,half_life=fit_schedule(cfg,plan,folder)
        seeds=seed_range(cfg,"test");x,y=generate_data(model,seeds);schedule=get_schedule(model,len(seeds))
        np.savez_compressed(folder/"test_inputs.npz",x=x,y=y,seeds=seeds,schedule=schedule)
        for edge_label,edge_pair in plan["attack_edges"].items():
            edge_dir=folder/edge_label;edge_dir.mkdir();model.cfg=copy.deepcopy(cfg)
            model.cfg["attack"].update(sender=edge_pair[0],receiver=edge_pair[1])
            write_json(edge_dir/"attack.json",model.cfg["attack"])
            for method in plan["methods"]:
                for scenario in plan["scenarios"]:
                    monitor=None if method=="local" else SequentialController(model,statistics if method in DETECTORS else None,
                        method,controls.get(method),half_life)
                    run=simulate(model,x,y,seeds,"local" if method=="local" else "capped",scenario,schedule,cap=cap,cache_monitor=monitor)
                    metrics,error=basic_metrics(model,run,x);a=cfg["attack"];start,end=a["start"]+1,a["end_inclusive"]+2;receiver=edge_pair[1]
                    metrics["receiver_attack_mse"]=error[:,start:end,receiver].mean(axis=1)
                    metrics["receiver_normal_full_mse"]=error[:,cfg["warmup"]+1:,receiver].mean(axis=1)
                    metrics["receiver_recovery_mse"]=error[:,end:end+a["recovery_steps"],receiver].mean(axis=1)
                    metrics["cache_weight_loss"]=1-run.weights[:,cfg["warmup"]:].mean(axis=(1,2)) if method!="local" else np.zeros(len(seeds))
                    for s,seed in enumerate(seeds):rows.append({"schedule":schedule_name,"edge_label":edge_label,"method":method,"scenario":scenario,"seed":int(seed),**{k:float(v[s]) for k,v in metrics.items()}})
                    if monitor is not None:
                        eps=monitor.finish();ep_rows+=episode_rows(eps,seeds,schedule_name,method,edge_label,scenario,cfg["warmup"])
                        # Save per-episode state without needlessly repeating all residual prefixes.
                        write_csv(edge_dir/(method+"__"+scenario+"_episodes.csv"),[{"trajectory":ep.trajectory,"edge":ep.edge,"start":ep.start,"length":len(ep.residuals),"complete":ep.complete,"maximum_ratio":ep.maximum,"alarm":ep.alarm} for ep in eps])
                    assert np.isfinite(run.estimates).all() and np.all((run.weights>=0)&(run.weights<=1))
                    if method!="local":assert np.array_equal(run.sends,schedule)
                    source,target=edge_pair;matched=0
                    for trial,t in zip(*np.where(run.injected)):
                        assert a["start"]<=t<=a["end_inclusive"] and run.sends[trial,t,source]
                        if scenario=="replay_matched":
                            old=run.replay_source[trial,t];assert old>=0 and old<t and run.sends[trial,old,source] and t-old==80;matched+=1
                    audits.append({"schedule":schedule_name,"edge_label":edge_label,"method":method,"scenario":scenario,"finite":True,"common_schedule":True,"legal_replay_packets":matched})
                    curves[schedule_name+"__"+edge_label+"__"+method+"__"+scenario]=error.mean(axis=(0,2))
                    np.savez_compressed(edge_dir/(method+"__"+scenario+".npz"),estimates=run.estimates,weights=run.weights,sends=run.sends,injected=run.injected,replay_source=run.replay_source,cache_bad=run.cache_bad)
                    print(json.dumps({"schedule":schedule_name,"edge":edge_label,"method":method,"scenario":scenario,
                        "receiver_mse":float(metrics["receiver_attack_mse"].mean()),"network_mse":float(metrics["mse_attack_window"].mean())}),flush=True)
            write_csv(out/"per_seed_metrics.csv",rows);write_csv(out/"per_seed_phase_rates.csv",ep_rows);write_json(out/"run_checks.json",audits)
            np.savez_compressed(out/"curves.npz",**curves)
    write_json(out/"execution.json",{"completed":True,"elapsed_seconds":time.perf_counter()-started,"method_trajectories":len(rows),"case_count":len(audits),"test_seeds":len(seeds),"no_test_parameter_updates":True})
    from summarize_sequential_validation import summarize
    summarize(out)
    print("COMPLETED "+str(out.resolve()),flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--plan",default="simulation/sequential_validation_plan.json");p.add_argument("--out",required=True)
    a=p.parse_args();main(a.plan,a.out)
