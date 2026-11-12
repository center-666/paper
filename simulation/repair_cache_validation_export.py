"""Repair a CSV export field-list issue without rerunning any attack/test estimator."""
from __future__ import annotations
import argparse,json,shutil
from pathlib import Path
import numpy as np
from model import Model,generate_data,seed_range
from cache_monitor import CacheMonitor
from cache_screen import MonitorController,get_schedule
from engine import simulate,basic_metrics
from run_study import write_json,write_csv


def main(folder):
    folder=Path(folder);plan=json.loads((folder/"plan.json").read_text(encoding="utf-8"));rows=[]
    for setting in plan["models"]:
        sub=folder/setting;cfg=json.loads((sub/"config.json").read_text(encoding="utf-8"));model=Model.build(cfg)
        stat=CacheMonitor.load(sub/"cache_statistics.npz");control=json.loads((sub/"controls.json").read_text(encoding="utf-8"))
        seeds=seed_range(cfg,"validation");x,y=generate_data(model,seeds);schedule=get_schedule(model,len(seeds))
        for method in plan["methods"]:
            if method not in {"age_decay","packet_spatial","instant_cache","joint_cache","mean_cache","gls_cache"}:continue
            options=plan["age_decay_half_lives"] if method=="age_decay" else plan["normal_validation_multipliers"]
            cc=[]
            for factor in options:
                monitor=MonitorController(model,stat,method,float(factor))
                r=simulate(model,x,y,seeds,"capped",schedule=schedule,cap=control["cap"],cache_monitor=monitor)
                metrics,_=basic_metrics(model,r,x)
                cc.append({"model":setting,"method":method,"factor":factor,"normal_mse":float(metrics["mse_all"].mean()),"episode_alarm_rate":monitor.alarm_rate(),
                           "mean_cache_weight":float(r.weights[:,cfg["warmup"]:].mean()),"selected":factor==control["controls"][method],"budget_feasible":method=="age_decay" or monitor.alarm_rate()<=.06})
            eligible=cc if method=="age_decay" else [z for z in cc if z["budget_feasible"]]
            assert min(eligible or cc,key=lambda z:z["normal_mse"])["factor"]==control["controls"][method]
            rows+=cc
    path=folder/"normal_validation.csv"
    if path.exists():shutil.copy2(path,folder/"normal_validation_interrupted.csv")
    write_csv(path,rows)
    expected=len(plan["models"])*len(plan["methods"])*len(plan["scenarios"])
    npz=[p for setting in plan["models"] for p in (folder/setting).glob("*__*.npz")]
    assert len(npz)==expected
    write_json(folder/"export_repair.json",{"normal_validation_only_recomputed":True,"test_trajectories_unchanged":True,"frozen_controls_confirmed":True,
        "reason":"optional selected/budget_feasible fields not present on first CSV row caused export error after all test runs","saved_case_count":len(npz)})
    write_json(folder/"execution.json",{"completed":True,"elapsed_seconds":None,"method_trajectories":expected*plan["splits"]["test"]["count"],"export_repaired":True,"scope":"All test outputs completed before CSV error; only normal validation export replayed"})
    print(json.dumps({"repaired":str(folder),"case_count":len(npz),"test_rerun":False}))


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("folder");a=p.parse_args();main(a.folder)
