"""Local cache-residency monitoring screen; no additional communication or truth input."""
from __future__ import annotations
import argparse,copy,hashlib,json,shutil,time
from pathlib import Path
import numpy as np
from model import Model,generate_data,seed_range
from engine import simulate,basic_metrics
from run_study import quantile,write_json,write_csv,paired_interval
from validation_suite import repeated_schedule


class EpisodeCollector:
    def __init__(self,model):
        self.model=model;self.buf=None;self.active=None;self.episodes=[]
    def update(self,t,fresh,age,aligned,measurement,local_hat):
        residual=measurement-np.einsum("emn,sen->sem",self.model.H[self.model.edges[:,1]],aligned)
        if self.buf is None:
            self.buf=np.zeros((len(fresh),len(self.model.edges),self.model.cfg["max_interval"],self.model.cfg["n"]))
            self.active=np.zeros(fresh.shape,bool)
        if not hasattr(self,"length"):self.length=np.zeros(fresh.shape,int)
        # The engine's age has already reset at arrival; use saved previous length.
        for e in range(len(self.model.edges)):
            fresh_active=np.flatnonzero(fresh[:,e]&self.active[:,e])
            for s in fresh_active:self.episodes.append((e,self.buf[s,e,:self.length[s,e]].copy()))
        self.active|=fresh
        self.length=np.where(fresh,0,self.length)
        self.buf=np.where(fresh[...,None,None],0,self.buf)
        for e in range(len(self.model.edges)):
            for a in np.unique(age[:,e]):
                selected=np.flatnonzero((age[:,e]==a)&self.active[:,e])
                if a<self.model.cfg["max_interval"]:
                    self.buf[selected,e,int(a)]=residual[selected,e]
                    self.length[selected,e]=int(a)+1
        return np.ones(fresh.shape)
    def finish(self):
        for e in range(len(self.model.edges)):
            for s in range(len(self.buf)):
                if self.length[s,e]:self.episodes.append((e,self.buf[s,e,:self.length[s,e]].copy()))
        self.episodes=[(e,r) for e,r in self.episodes if len(r)>0]
        return self.episodes


class MonitorController:
    def __init__(self,model,statistics,kind,multiplier=1.0):
        self.model=model;self.statistics=statistics;self.kind=kind;self.multiplier=multiplier
        self.prefix=None;self.active=None;self.bad=None
        self.episodes=0;self.alarmed=0
    def update(self,t,fresh,age,aligned,measurement,local_hat):
        S,E=fresh.shape;n=self.model.cfg["n"];L=self.model.cfg["max_interval"]
        if self.prefix is None:
            self.prefix=np.zeros((S,E,L,n));self.active=np.zeros((S,E),bool);self.bad=np.zeros((S,E),bool)
        ended=fresh&self.active
        self.episodes+=int(ended.sum());self.alarmed+=int(self.bad[ended].sum())
        self.bad=np.where(fresh,False,self.bad);self.active|=fresh
        self.prefix=np.where(fresh[...,None,None],0,self.prefix)
        if self.kind=="age_decay":return np.exp(-np.log(2)*age/self.multiplier)
        residual=measurement-np.einsum("emn,sen->sem",self.model.H[self.model.edges[:,1]],aligned)
        for e in range(E):
            for a in np.unique(age[:,e]):
                select=np.flatnonzero(age[:,e]==a)
                if a>=L:raise ValueError("Cache age exceeds configured no-drop maximum")
                self.prefix[select,e,int(a)]=residual[select,e]
                if self.kind=="packet_spatial" and a!=0:continue
                key="instant" if self.kind=="packet_spatial" else self.kind.split("_")[0]
                values=self.statistics.scores_batch(e,self.prefix[select,e,:int(a)+1])[key]
                q=self.statistics.packet_thresholds[e] if self.kind=="packet_spatial" else self.statistics.thresholds[e][key]
                self.bad[select,e]|=values>q*self.multiplier
        return (~self.bad).astype(float)
    def alarm_rate(self):
        total=self.episodes+int(self.active.sum());alarms=self.alarmed+int(self.bad[self.active].sum())
        return alarms/max(1,total)


def model_for(setting,base,refplan,plan):
    c=copy.deepcopy(base)
    if setting=="heterogeneous_sensing":
        s=next(r for r in refplan["models"] if r["id"]==setting)
        c.update(A=s["A"],H_matrices=s["H_matrices"])
    for split,v in plan["splits"].items():c[split+"_seeds"]=v
    c["attack"].update(matched_replay_time_lag=80,low_bias_factor=.25)
    return Model.build(c)


def get_schedule(model,count):
    pattern=model.cfg.get("cache_schedule_pattern",[1,2,3,4,6,8,6,4,3,3])
    return repeated_schedule(model.cfg,count,{"repeated_gap_pattern":pattern,"node_phase_step":model.cfg.get("cache_schedule_phase",3),"matched_replay_time_lag":80})


def main(plan_path,out):
    from cache_monitor import CacheMonitor,CacheEpisode
    out=Path(out)
    if out.exists():raise FileExistsError("Do not overwrite")
    out.mkdir(parents=True)
    plan=json.loads(Path(plan_path).read_text(encoding="utf-8-sig"));base=json.loads(Path(plan["base_config"]).read_text(encoding="utf-8-sig"))
    refplan=json.loads(Path("simulation/reference_exploration_plan.json").read_text(encoding="utf-8-sig"))
    write_json(out/"plan.json",plan)
    source=out/"sources";source.mkdir()
    for f in Path("simulation").glob("*.py"):shutil.copy2(f,source/f.name)
    from datetime import datetime,timezone
    write_json(out/"registration.json",{"created":datetime.now(timezone.utc).isoformat(),"plan_sha256":hashlib.sha256(Path(plan_path).read_bytes()).hexdigest(),"source_sha256":{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in source.iterdir()},"test_not_generated":True})
    rows=[];validation=[];started=time.perf_counter()
    for setting in plan["models"]:
        folder=out/setting;folder.mkdir();model=model_for(setting,base,refplan,plan);cfg=model.cfg
        if "schedule_pattern" in plan:
            cfg["cache_schedule_pattern"]=plan["schedule_pattern"]
            cfg["cache_schedule_phase"]=plan.get("schedule_phase",1)
        write_json(folder/"config.json",cfg)
        episodes={};data={};cap=None
        for split in ("train","calibration","validation"):
            seeds=seed_range(cfg,split);x,y=generate_data(model,seeds);schedule=get_schedule(model,len(seeds));data[split]=(x,y,seeds,schedule)
            if split in {"train","calibration"}:
                collector=EpisodeCollector(model)
                run=simulate(model,x,y,seeds,"capped",schedule=schedule,cap=np.inf if cap is None else cap,cache_monitor=collector)
                if split=="train":
                    cap=quantile(run.cap_norms.ravel(),cfg["cap_quantile"])
                    collector=EpisodeCollector(model)
                    run=simulate(model,x,y,seeds,"capped",schedule=schedule,cap=cap,cache_monitor=collector)
                episodes[split]=[CacheEpisode(edge=e,residuals=r) for e,r in collector.finish()]
                lengths=np.asarray([len(ep.residuals) for ep in episodes[split]],int)
                packed=np.zeros((len(lengths),cfg["max_interval"],cfg["n"]))
                for idx,ep in enumerate(episodes[split]):packed[idx,:len(ep.residuals)]=ep.residuals
                np.savez_compressed(folder/(split+"_episodes.npz"),edge=np.asarray([ep.edge for ep in episodes[split]]),length=lengths,residuals=packed,seeds=seeds)
        statistics=CacheMonitor.fit(episodes["train"],episodes["calibration"],dict(enumerate(model.H[model.edges[:,1]])),model.A,
                                    max_age=cfg["max_interval"]-1,min_samples=40,ridge_relative=1e-3,false_alarm_target=plan["episode_false_alarm_target"])
        statistics.save(folder/"cache_statistics.npz")
        vx,vy,vs,schedule=data["validation"];controls={}
        for method in plan["methods"]:
            if method in {"packet_spatial","instant_cache","joint_cache","gls_cache","mean_cache","age_decay"}:
                options=plan["age_decay_half_lives"] if method=="age_decay" else plan["normal_validation_multipliers"]
                candidates=[]
                for factor in options:
                    monitor=MonitorController(model,statistics,method,float(factor))
                    r=simulate(model,vx,vy,vs,"capped",schedule=schedule,cap=cap,cache_monitor=monitor)
                    metrics,_=basic_metrics(model,r,vx)
                    trial={"model":setting,"method":method,"factor":factor,"normal_mse":float(metrics["mse_all"].mean()),"episode_alarm_rate":monitor.alarm_rate(),"mean_cache_weight":float(r.weights[:,cfg["warmup"]:].mean()),"selected":False,"budget_feasible":None}
                    validation.append(trial);candidates.append(trial)
                eligible=candidates if method=="age_decay" else [v for v in candidates if v["episode_alarm_rate"]<=.06]
                chosen=min(eligible or candidates,key=lambda z:z["normal_mse"])
                chosen["selected"]=True;chosen["budget_feasible"]=bool(eligible)
                controls[method]=chosen["factor"]
            else:controls[method]=1.0
        write_json(folder/"controls.json",{"cap":cap,"controls":controls})
        tseeds=seed_range(cfg,"test");x,y=generate_data(model,tseeds);schedule=get_schedule(model,len(tseeds))
        np.savez_compressed(folder/"test_inputs.npz",x=x,y=y,seeds=tseeds,schedule=schedule)
        for method in plan["methods"]:
            for scenario in plan["scenarios"]:
                monitor=MonitorController(model,statistics,method,float(controls[method])) if method in controls and method in {"packet_spatial","instant_cache","joint_cache","gls_cache","mean_cache","age_decay"} else None
                actual="capped" if monitor is not None else method
                r=simulate(model,x,y,tseeds,actual,scenario,schedule,cap=cap,cache_monitor=monitor)
                metrics,_=basic_metrics(model,r,x)
                receiver=cfg["attack"]["receiver"]
                errs=np.sum((r.estimates-x[:,:,None,:])**2,axis=-1)
                metrics["receiver_attack_mse"]=errs[:,cfg["attack"]["start"]+1:cfg["attack"]["end_inclusive"]+2,receiver].mean(axis=1)
                metrics["receiver_clean_window_mse"]=errs[:,cfg["warmup"]+1:,receiver].mean(axis=1)
                for s,seed in enumerate(tseeds):
                    rows.append({"model":setting,"method":method,"scenario":scenario,"seed":int(seed),**{k:float(v[s]) for k,v in metrics.items()},
                        "episode_alarm_rate_batch":monitor.alarm_rate() if monitor is not None and method!="age_decay" else float("nan")})
                np.savez_compressed(folder/(method+"__"+scenario+".npz"),estimates=r.estimates,weights=r.weights,sends=r.sends,injected=r.injected,replay_source=r.replay_source)
                print(json.dumps({"model":setting,"method":method,"scenario":scenario,"attack_mse":float(metrics["mse_attack_window"].mean()),"normal_mse":float(metrics["mse_all"].mean())}),flush=True)
        write_csv(out/"per_seed_metrics.csv",rows);write_csv(out/"normal_validation.csv",validation)
    write_json(out/"execution.json",{"completed":True,"elapsed_seconds":time.perf_counter()-started,"method_trajectories":len(rows),"scope":"exploratory cache episode mechanism screen"})
    print("COMPLETED "+str(out.resolve()),flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--plan",default="simulation/cache_exploration_plan.json");p.add_argument("--out",required=True);a=p.parse_args();main(a.plan,a.out)
