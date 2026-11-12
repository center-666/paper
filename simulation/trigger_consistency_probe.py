"""Exploratory legal-event/payload consistency: necessity, not authenticity proof."""
from __future__ import annotations
import csv,json,hashlib,shutil
from pathlib import Path
import numpy as np
from model import Model,generate_data
from engine import simulate
from run_study import write_json,write_csv


def main():
    out=Path("simulation/exploration_runs/2026-11-11_trigger_consistency_probe")
    if out.exists():raise FileExistsError("Preserve outputs")
    out.mkdir(parents=True)
    cfg=json.loads(Path("simulation/config.json").read_text(encoding="utf-8-sig"));cfg["T"]=400
    seeds=np.arange(540000,540064);m=Model.build(cfg);x,y=generate_data(m,seeds)
    plan={"seeds":seeds.tolist(),"purpose":"Probe necessary SoD payload difference constraint, no estimator defense claim",
          "scenarios":["clean","constant_bias","freeze","packet_replay"],"scope":"Payload mutation on same actual honest sending stream; no feedback-counterfactual simulation",
          "threshold":cfg["send_delta_squared"],"Tmax":cfg["max_interval"],"formula":"if delta<Tmax then ||m_r-m_prev||^2 > send threshold; violation can implicate either endpoint, not identify current one"}
    write_json(out/"plan.json",plan)
    run=simulate(m,x,y,seeds,"yang",collect=False)
    records=[];sender=cfg["attack"]["sender"];a=cfg["attack"]
    for s,seed in enumerate(seeds):
        times=np.flatnonzero(run.sends[s,:,sender]);original=run.estimates[s,times,sender]
        first=np.searchsorted(times,a["start"])
        for scenario in plan["scenarios"]:
            z=original.copy();attacked=np.zeros(len(times),bool)
            for r,t in enumerate(times):
                if not a["start"]<=t<=a["end_inclusive"]:continue
                if scenario=="constant_bias":z[r]+=np.asarray(a["bias"]);attacked[r]=True
                if scenario=="freeze" and first>0:z[r]=original[first-1];attacked[r]=True
                if scenario=="packet_replay" and r>=a["replay_packet_lag"]:z[r]=original[r-a["replay_packet_lag"]];attacked[r]=True
            for r in range(1,len(times)):
                delta=int(times[r]-times[r-1]);eligible=delta<cfg["max_interval"]
                violation=eligible and np.sum((z[r]-z[r-1])**2)<=cfg["send_delta_squared"]-1e-12
                if scenario=="clean":assert not violation
                if scenario=="constant_bias" and attacked[r] and attacked[r-1]:assert not violation
                if times[r]<cfg["warmup"]:continue
                records.append({"seed":int(seed),"scenario":scenario,"time":int(times[r]),"delta":delta,"eligible":eligible,"violation":violation,
                                "current_attack":bool(attacked[r]),"previous_attack":bool(attacked[r-1])})
    write_csv(out/"packet_checks.csv",records)
    summary=[]
    for scenario in plan["scenarios"]:
        r=[a for a in records if a["scenario"]==scenario]
        current=[a for a in r if a["current_attack"]]
        dual=[a for a in r if a["current_attack"] and a["previous_attack"]]
        healthy=[a for a in r if not a["current_attack"] and not a["previous_attack"]]
        summary.append({"scenario":scenario,"pairs":len(r),"healthy_pair_violations":sum(a["violation"] for a in healthy),"attack_pairs":len(current),
                        "violation_rate_on_attacked_current":float(np.mean([a["violation"] for a in current])) if current else None,
                        "violation_rate_inside_continuous_attack":float(np.mean([a["violation"] for a in dual])) if dual else None,
                        "violations_on_first_normal_return":sum(a["violation"] for a in r if not a["current_attack"] and a["previous_attack"])})
    write_json(out/"summary.json",summary);shutil.copy2(__file__,out/"trigger_consistency_probe.py")
    write_json(out/"source.json",{"sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),"no_truth_used_for_constraint":True})
    print((out/"summary.json").read_text(encoding="utf-8"))


if __name__=="__main__":main()
