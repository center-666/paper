from __future__ import annotations
import argparse,copy,hashlib,json,shutil,time
from pathlib import Path
import numpy as np
from scipy import stats
from model import Model,generate_data,seed_range
from engine import simulate,basic_metrics
from cache_monitor import CacheMonitor,CacheEpisode
from cache_screen import EpisodeCollector,MonitorController,get_schedule
from run_study import quantile,write_json,write_csv,paired_interval
from validation_summary import holm


class AgeCollector(EpisodeCollector):
    def __init__(self,model,half_life):super().__init__(model);self.half_life=half_life
    def update(self,t,fresh,age,aligned,measurement,local_hat):
        super().update(t,fresh,age,aligned,measurement,local_hat)
        return np.exp(-np.log(2)*age/self.half_life)


class AgeGatedMonitor(MonitorController):
    def __init__(self,model,statistics,kind,multiplier,half_life):
        super().__init__(model,statistics,kind,multiplier);self.half_life=half_life
    def update(self,t,fresh,age,aligned,measurement,local_hat):
        return super().update(t,fresh,age,aligned,measurement,local_hat)*np.exp(-np.log(2)*age/self.half_life)


def main(out):
    out=Path(out)
    if out.exists():raise FileExistsError("Preserve outputs")
    out.mkdir(parents=True)
    plan=json.loads(Path("simulation/cache_aged_plan.json").read_text(encoding="utf-8"))
    base=json.loads(Path("simulation/config.json").read_text(encoding="utf-8"));ref=json.loads(Path("simulation/reference_exploration_plan.json").read_text(encoding="utf-8"))
    write_json(out/"plan.json",plan);src=out/"sources";src.mkdir()
    for f in Path("simulation").glob("*.py"):shutil.copy2(f,src/f.name)
    from datetime import datetime,timezone
    write_json(out/"registration.json",{"created":datetime.now(timezone.utc).isoformat(),"plan_sha256":hashlib.sha256(Path("simulation/cache_aged_plan.json").read_bytes()).hexdigest(),"source_sha256":{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in src.iterdir()},"new_test_data_not_generated":True})
    rows=[];validrows=[];started=time.perf_counter()
    for schedule_name,pattern in plan["schedules"].items():
        folder=out/schedule_name;folder.mkdir()
        cfg=copy.deepcopy(base);h=ref["models"][1];cfg.update(A=h["A"],H_matrices=h["H_matrices"],cache_schedule_pattern=pattern,cache_schedule_phase=1)
        for split,v in plan["splits"].items():cfg[split+"_seeds"]=v
        cfg["attack"].update(matched_replay_time_lag=80,low_bias_factor=.25)
        write_json(folder/"config.json",cfg);model=Model.build(cfg)
        data={}
        for split in ("train","calibration","validation"):
            seeds=seed_range(cfg,split);x,y=generate_data(model,seeds);data[split]=(x,y,seeds,get_schedule(model,len(seeds)))
        x,y,seeds,sch=data["train"]
        reference=simulate(model,x,y,seeds,"yang",schedule=sch)
        cap=quantile(reference.cap_norms.ravel(),.995)
        vx,vy,vs,vsch=data["validation"];hrows=[]
        for hlf in plan["half_lives"]:
            monitor=MonitorController(model,None,"age_decay",hlf)
            rr=simulate(model,vx,vy,vs,"capped",schedule=vsch,cap=cap,cache_monitor=monitor)
            metrics,_=basic_metrics(model,rr,vx);hrows.append({"half_life":hlf,"normal_mse":float(metrics["mse_all"].mean())})
        half_life=min(hrows,key=lambda z:z["normal_mse"])["half_life"]
        eps={}
        for split in ("train","calibration"):
            x,y,seeds,sch=data[split];collector=AgeCollector(model,half_life)
            simulate(model,x,y,seeds,"capped",schedule=sch,cap=cap,cache_monitor=collector)
            episodes=collector.finish();eps[split]=[CacheEpisode(e,r) for e,r in episodes]
            lengths=np.array([len(r) for _,r in episodes]);packed=np.zeros((len(lengths),cfg["max_interval"],cfg["n"]))
            for j,(_,r) in enumerate(episodes):packed[j,:len(r)]=r
            np.savez_compressed(folder/(split+"_episodes.npz"),edge=np.array([e for e,_ in episodes]),length=lengths,residuals=packed,seeds=seeds)
        stat=CacheMonitor.fit(eps["train"],eps["calibration"],dict(enumerate(model.H[model.edges[:,1]])),model.A,max_age=cfg["max_interval"]-1,false_alarm_target=.05)
        stat.save(folder/"cache_statistics.npz")
        controls={};kinds={"age_packet":"packet_spatial","age_instant":"instant_cache","age_mean":"mean_cache"}
        for method,kind in kinds.items():
            cand=[]
            for multiplier in plan["detector_choices"]:
                mon=AgeGatedMonitor(model,stat,kind,multiplier,half_life)
                rr=simulate(model,vx,vy,vs,"capped",schedule=vsch,cap=cap,cache_monitor=mon)
                metrics,_=basic_metrics(model,rr,vx)
                row={"schedule":schedule_name,"method":method,"multiplier":multiplier,"normal_mse":float(metrics["mse_all"].mean()),"episodeFPR":mon.alarm_rate(),"selected":False}
                cand.append(row)
            allowed=[z for z in cand if z["episodeFPR"]<=plan["normal_alarm_limit"]];selected=min(allowed or cand,key=lambda z:z["normal_mse"]);selected["selected"]=True
            controls[method]=selected["multiplier"];validrows+=cand
        write_json(folder/"frozen_controls.json",{"half_life":half_life,"normal_half_life_candidates":hrows,"cap":cap,"controls":controls})
        seeds=seed_range(cfg,"test");x,y=generate_data(model,seeds);sch=get_schedule(model,len(seeds))
        np.savez_compressed(folder/"test_inputs.npz",x=x,y=y,seeds=seeds,schedule=sch)
        for method in plan["methods"]:
            for scenario in plan["scenarios"]:
                if method=="local":monitor=None
                elif method=="age_only":monitor=MonitorController(model,None,"age_decay",half_life)
                else:monitor=AgeGatedMonitor(model,stat,kinds[method],controls[method],half_life)
                rr=simulate(model,x,y,seeds,"local" if method=="local" else "capped",scenario,sch,cap=cap,cache_monitor=monitor)
                metrics,_=basic_metrics(model,rr,x);err=np.sum((rr.estimates-x[:,:,None,:])**2,axis=-1)
                receiver=err[:,cfg["attack"]["start"]+1:cfg["attack"]["end_inclusive"]+2,cfg["attack"]["receiver"]].mean(axis=1)
                for s,seed in enumerate(seeds):rows.append({"schedule":schedule_name,"method":method,"scenario":scenario,"seed":int(seed),"receiver_attack_mse":float(receiver[s]),"episodeFPR_batch":monitor.alarm_rate() if method in kinds else float("nan"),**{k:float(v[s]) for k,v in metrics.items()}})
                assert np.isfinite(rr.estimates).all()
                np.savez_compressed(folder/(method+"__"+scenario+".npz"),estimates=rr.estimates,weights=rr.weights,sends=rr.sends,injected=rr.injected,replay_source=rr.replay_source)
                print(json.dumps({"schedule":schedule_name,"method":method,"scenario":scenario,"network_mse":float(metrics["mse_attack_window"].mean()),"receiver_mse":float(receiver.mean())}),flush=True)
        write_csv(out/"per_seed_metrics.csv",rows);write_csv(out/"normal_validation.csv",validrows)
    ix={(r["schedule"],r["method"],r["scenario"],r["seed"]):r for r in rows}
    comparisons=[];tests=[]
    for setting in plan["schedules"]:
        def values(method,scenario,key):return np.array([ix[setting,method,scenario,int(s)][key] for s in seeds])
        normal=values("age_mean","clean","mse_all").mean()/values("age_instant","clean","mse_all").mean()-1
        for scenario in plan["scenarios"]:
            if scenario=="clean":continue
            a=values("age_mean",scenario,"receiver_attack_mse");b=values("age_instant",scenario,"receiver_attack_mse")
            mu,lo,hi=paired_interval(a-b);margin=a-.99*b
            row={"schedule":setting,"scenario":scenario,"receiver_relative_gain":float(-mu/b.mean()),"paired_diff":mu,"bootstrap95_low":lo,"bootstrap95_high":hi,"normal_network_cost":float(normal),"episodeFPR":float(values("age_mean","clean","episodeFPR_batch").mean()),"practical_p":float(stats.ttest_1samp(margin,0,alternative="less").pvalue)}
            comparisons.append(row)
            if scenario in {"step","half_step"}:tests.append(row)
    ps=holm([r["practical_p"] for r in tests])
    for row,p in zip(tests,ps):row.update(holm_p=float(p),passed=bool(p<.05 and row["normal_network_cost"]<=.02 and row["episodeFPR"]<=.06))
    write_csv(out/"comparisons.csv",comparisons);write_csv(out/"primary_tests.csv",tests)
    write_json(out/"gate.json",{"passed":sum(r["passed"] for r in tests)>=2 and all(any(r["passed"] for r in tests if r["schedule"]==schedule) for schedule in plan["schedules"]),"passed_cases":sum(r["passed"] for r in tests),"total_cases":4})
    write_json(out/"execution.json",{"completed":True,"elapsed_seconds":time.perf_counter()-started,"method_trajectories":len(rows),"test_seeds":len(seeds)})
    print(json.dumps(tests));print("COMPLETED "+str(out.resolve()),flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",required=True);args=p.parse_args();main(args.out)
