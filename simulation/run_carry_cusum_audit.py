"""Cross-message CUSUM comparator audit using fresh tuning/audit/test seeds."""
from __future__ import annotations
import argparse,copy,csv,hashlib,json,shutil,time
from pathlib import Path
import numpy as np
from scipy import stats
from model import Model,generate_data
from engine import simulate,basic_metrics
from cache_screen import get_schedule
from sequential_cache import PhaseStatistics,SequentialController,PHASES,phase_rates
from run_sequential_validation import episode_rows
from run_study import write_json,write_csv,paired_interval
from validation_summary import holm


def load_statistics(path):
    with np.load(path) as f:
        meta=json.loads(str(f["metadata"]));st=PhaseStatistics(meta["E"],meta["m"],meta["max_length"],meta["warmup"],meta["window"],meta["signed_reference"])
        st.counts=meta["counts"]
        for method in st.thresholds:st.thresholds[method]=f["threshold_"+method].copy()
        for row in st.counts:
            p=PHASES.index(row["phase"]);e,L=row["edge"],row["length"];prefix=f"p{p}_e{e}_l{L}_"
            fit={k[len(prefix):]:f[k].copy() for k in f.files if k.startswith(prefix)}
            fit.update(fallback=row["fallback"],train_count=row["train_count"]);st.models[p,e,L]=fit
    return st


def method_args(method):
    return ("mean",False) if method=="mean" else ("white_cusum",True) if method=="carry_energy_cusum" else ("white_signed_cusum",True)


def checks(cfg,st):
    model=Model.build(cfg);E=len(model.edges);n=cfg["n"];edge=0
    # At age zero construct a known whitened innovation z=[3,3].
    fit=st.models[0,edge,1];z=np.array([3.,3.]);residual=fit["mean"]+np.linalg.cholesky(fit["cov"])@z
    # Use all initial-phase moment blocks for synthetic transition check.
    toy=copy.deepcopy(st)
    for p in range(3):
        for e in range(E):toy.models[p,e,1]=copy.deepcopy(fit);toy.thresholds["white_cusum"][p,e]=1.
    carry=SequentialController(model,toy,"white_cusum",[1e6]*3,4,carry_across_packets=True)
    reset=SequentialController(model,toy,"white_cusum",[1e6]*3,4)
    fresh=np.ones((1,E),bool);age=np.zeros((1,E),int);zero=np.zeros((1,E,n));measure=np.broadcast_to(residual,(1,E,n)).copy()
    for t in range(2):carry.update(t,fresh,age,zero,measure,zero);reset.update(t,fresh,age,zero,measure,zero)
    assert np.allclose(carry.cs,2*(z@z-n)) and np.allclose(reset.cs,z@z-n)
    hit=SequentialController(model,toy,"white_cusum",[1]*3,4,carry_across_packets=True)
    weight=hit.update(0,fresh,age,zero,measure,zero)
    assert np.all(weight==0) and np.all(hit.cs==0)
    return {"passed":True,"carry_sum_two_packets":float(carry.cs[0,0]),"reset_sum_two_packets":float(reset.cs[0,0]),"alarm_resets_cusum_not_cache_isolation":True}


def main(out):
    out=Path(out)
    if out.exists():raise FileExistsError("Preserve previous evidence")
    out.mkdir(parents=True)
    plan_path=Path("simulation/cusum_carry_plan.json");plan=json.loads(plan_path.read_text(encoding="utf-8"));source=Path(plan["source_run"])
    write_json(out/"plan.json",plan);shutil.copy2(plan_path,out/"registered_plan_original.json")
    src=out/"sources";src.mkdir()
    for f in Path("simulation").glob("*.py"):shutil.copy2(f,src/f.name)
    from datetime import datetime,timezone
    write_json(out/"registration.json",{"created_utc":datetime.now(timezone.utc).isoformat(),"plan_sha256":hashlib.sha256(plan_path.read_bytes()).hexdigest(),"source_sha256":{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in src.iterdir()},"prior_results_seen":True,"fresh_test_not_generated":True})
    rows=[];phase_records=[];started=time.perf_counter();test_seeds=None;audit_rates={}
    for schedule_name in plan["schedules"]:
        folder=out/schedule_name;folder.mkdir();cfg=json.loads((source/schedule_name/"config.json").read_text(encoding="utf-8"))
        model=Model.build(cfg);st=load_statistics(source/schedule_name/"phase_statistics.npz")
        write_json(folder/"extension_check.json",checks(cfg,st));write_json(folder/"config.json",cfg)
        old=json.loads((source/schedule_name/"frozen_controls.json").read_text(encoding="utf-8"));cap,half=old["cap"],old["half_life"]
        tune=plan["tune_seeds"];seeds=np.arange(tune["start"],tune["start"]+tune["count"]);x,y=generate_data(model,seeds);schedule=get_schedule(model,len(seeds))
        control={};history=[]
        for method in plan["methods"]:
            detector,carry=method_args(method);lo=np.full(3,.05);hi=np.full(3,40.)
            for iteration in range(plan["tune_rounds"]):
                mu=np.sqrt(lo*hi);mon=SequentialController(model,st,detector,mu,half,carry_across_packets=carry)
                simulate(model,x,y,seeds,"capped",schedule=schedule,cap=cap,cache_monitor=mon,collect=False)
                rates=phase_rates(mon.finish(),cfg["warmup"]);history.append({"method":method,"round":iteration,"multipliers":mu.tolist(),"rates":rates})
                more=np.array([rates[p]["false_isolation_rate"]>plan["normal_target"] for p in PHASES]);lo=np.where(more,mu,lo);hi=np.where(more,hi,mu)
            control[method]=np.sqrt(lo*hi)
        write_json(folder/"controls.json",{"half_life":half,"cap":cap,"multipliers":control});write_json(folder/"tuning.json",history)
        ad=plan["normal_audit_seeds"];aseeds=np.arange(ad["start"],ad["start"]+ad["count"]);ax,ay=generate_data(model,aseeds);asch=get_schedule(model,len(aseeds))
        for method in plan["methods"]:
            detector,carry=method_args(method);mon=SequentialController(model,st,detector,control[method],half,carry_across_packets=carry)
            simulate(model,ax,ay,aseeds,"capped",schedule=asch,cap=cap,cache_monitor=mon,collect=False)
            rates=phase_rates(mon.finish(),cfg["warmup"]);audit_rates[schedule_name,method]=rates
            print(json.dumps({"schedule":schedule_name,"method":method,"independent_normal_audit":rates}),flush=True)
        t=plan["test_seeds"];test_seeds=np.arange(t["start"],t["start"]+t["count"]);tx,ty=generate_data(model,test_seeds);tsch=get_schedule(model,len(test_seeds))
        np.savez_compressed(folder/"test_inputs.npz",x=tx,y=ty,seeds=test_seeds,schedule=tsch)
        for edge_label,(sender,receiver) in plan["attack_edges"].items():
            sub=folder/edge_label;sub.mkdir();model.cfg["attack"].update(sender=sender,receiver=receiver)
            for method in plan["methods"]:
                detector,carry=method_args(method)
                for scenario in plan["scenarios"]:
                    mon=SequentialController(model,st,detector,control[method],half,carry_across_packets=carry)
                    run=simulate(model,tx,ty,test_seeds,"capped",scenario,tsch,cap=cap,cache_monitor=mon)
                    metrics,error=basic_metrics(model,run,tx);a=cfg["attack"]
                    metrics["receiver_attack_mse"]=error[:,a["start"]+1:a["end_inclusive"]+2,receiver].mean(axis=1)
                    metrics["receiver_normal_full_mse"]=error[:,cfg["warmup"]+1:,receiver].mean(axis=1)
                    eps=mon.finish();phase_records+=episode_rows(eps,test_seeds,schedule_name,method,edge_label,scenario,cfg["warmup"])
                    for s,seed in enumerate(test_seeds):rows.append({"schedule":schedule_name,"edge_label":edge_label,"method":method,"scenario":scenario,"seed":int(seed),**{k:float(v[s]) for k,v in metrics.items()}})
                    np.savez_compressed(sub/(method+"__"+scenario+".npz"),estimates=run.estimates,weights=run.weights,sends=run.sends,injected=run.injected,replay_source=run.replay_source)
                    assert np.isfinite(run.estimates).all() and np.array_equal(run.sends,tsch)
                    print(json.dumps({"schedule":schedule_name,"edge":edge_label,"method":method,"scenario":scenario,"receiver_mse":float(metrics["receiver_attack_mse"].mean())}),flush=True)
        write_csv(out/"per_seed_metrics.csv",rows);write_csv(out/"phase_rates.csv",phase_records)
    write_json(out/"normal_audit_rates.json",[{"schedule":s,"method":m,"rates":r} for (s,m),r in audit_rates.items()])
    lookup={(r["schedule"],r["edge_label"],r["method"],r["scenario"],r["seed"]):r for r in rows}
    def vals(s,e,m,c,k):return np.array([lookup[s,e,m,c,int(seed)][k] for seed in test_seeds])
    def fpr(s,e,m):
        r=[z for z in phase_records if z["schedule"]==s and z["edge_label"]==e and z["method"]==m and z["scenario"]=="clean" and z["phase"]=="steady"]
        return sum(z["alarm_episodes"] for z in r)/sum(z["complete_episodes"] for z in r)
    comparisons=[];primary=[];acceptance=plan["normal_acceptance"]
    for s in plan["schedules"]:
        for e in plan["attack_edges"]:
            for c in ("step","half_step"):
                for baseline in ("carry_energy_cusum","carry_signed_cusum"):
                    a,b=vals(s,e,"mean",c,"receiver_attack_mse"),vals(s,e,baseline,c,"receiver_attack_mse")
                    mu,lo,hi=paired_interval(a-b);margin=a-.99*b
                    normal_net=vals(s,e,"mean","clean","mse_all").mean()/vals(s,e,baseline,"clean","mse_all").mean()-1
                    normal_rec=vals(s,e,"mean","clean","receiver_normal_full_mse").mean()/vals(s,e,baseline,"clean","receiver_normal_full_mse").mean()-1
                    ma,mb=fpr(s,e,"mean"),fpr(s,e,baseline);aa=audit_rates[s,"mean"]["steady"]["false_isolation_rate"];ab=audit_rates[s,baseline]["steady"]["false_isolation_rate"]
                    low,high=acceptance["target_steady_fpr_range"]
                    fair=all(low<=v<=high for v in (ma,mb,aa,ab)) and max(abs(ma-mb),abs(aa-ab))<=acceptance["max_steady_fpr_difference"]
                    row={"schedule":s,"edge_label":e,"scenario":c,"baseline":baseline,"receiver_relative_gain":float(-mu/b.mean()),"paired_diff":mu,"bootstrap95_low":lo,"bootstrap95_high":hi,
                        "test_mean_fpr":ma,"test_baseline_fpr":mb,"audit_mean_fpr":aa,"audit_baseline_fpr":ab,"fpr_comparable":fair,"normal_network_cost":float(normal_net),"normal_receiver_cost":float(normal_rec),
                        "practical_p":float(stats.ttest_1samp(margin,0,alternative="less").pvalue)}
                    comparisons.append(row)
                    if e=="primary" and c=="step":primary.append(row.copy())
    assert len(primary)==4
    for row,pv in zip(primary,holm([r["practical_p"] for r in primary])):
        row["holm_p"]=float(pv);row["passes"]=bool(pv<.05 and row["fpr_comparable"] and row["normal_network_cost"]<=.02 and row["normal_receiver_cost"]<=.02)
    write_csv(out/"comparisons.csv",comparisons);write_csv(out/"primary_tests.csv",primary)
    write_json(out/"gate.json",{"passed_cases":sum(r["passes"] for r in primary),"total_cases":4,"scope":"Comparator fairness follow-up; does not erase the failed broader primary gate"})
    write_json(out/"execution.json",{"completed":True,"elapsed_seconds":time.perf_counter()-started,"method_trajectories":len(rows),"test_seeds":len(test_seeds)})
    print(json.dumps(primary));print("COMPLETED "+str(out.resolve()),flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",required=True);a=p.parse_args();main(a.out)
