"""Post-run paired analysis; reads frozen outputs, never changes fitted parameters."""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
import numpy as np
from run_study import paired_interval, write_csv, write_json


def analyze(folder):
    folder=Path(folder)
    with (folder/"per_seed_metrics.csv").open(encoding="utf-8-sig",newline="") as f:rows=list(csv.DictReader(f))
    lookup={(r["protocol"],r["method"],r["scenario"],int(r["seed"])):r for r in rows}
    seeds=sorted(set(int(r["seed"]) for r in rows))
    contrasts=[]
    for protocol in ("reference_schedule","closed_loop"):
        for scenario in ("step","ramp","replay_packet"):
            for baseline in ("pooled","interval_scale","zhou_random","capped","local"):
                differences=[]
                for seed in seeds:
                    def loss(method,sc):return float(lookup[protocol,method,sc,seed]["mse_attack_window"])
                    candidate=loss("interval_tail",scenario)-loss("interval_tail","clean")
                    reference=loss(baseline,scenario)-loss(baseline,"clean")
                    differences.append(candidate-reference)
                mean,lo,hi=paired_interval(differences)
                contrasts.append({"protocol":protocol,"scenario":scenario,"candidate":"interval_tail","baseline":baseline,
                                  "metric":"paired_attack_excess_difference","mean_difference":mean,"bootstrap95_low":lo,"bootstrap95_high":hi})
    write_csv(folder/"paired_attack_excess_comparisons.csv",contrasts)
    # Artifact consistency checks independent of scientific outcome.
    cfg=json.loads((folder/"config.json").read_text(encoding="utf-8"))
    expected=2*len(cfg["methods"])*len(cfg["test_scenarios"])*len(seeds)
    assert len(rows)==expected
    assert len(lookup)==expected
    split_sets=[]
    for split in ("train","calibration","validation","test"):
        d=cfg[split+"_seeds"];split_sets.append(set(range(d["start"],d["start"]+d["count"])))
    for i,a in enumerate(split_sets):
        for b in split_sets[i+1:]:assert not a&b
    with np.load(folder/"test_inputs.npz") as inputs:
        schedule=inputs["reference_schedule"]
        x=inputs["x"]
    for protocol in ("reference_schedule","closed_loop"):
        for method in cfg["methods"]:
            for scenario in cfg["test_scenarios"]:
                with np.load(folder/protocol/(method+"__"+scenario+".npz")) as r:
                    assert np.isfinite(r["estimates"]).all()
                    assert np.isfinite(r["weights"]).all()
                    assert np.all((r["weights"]>=0)&(r["weights"]<=1))
                    if protocol=="reference_schedule" and method!="local":assert np.array_equal(r["sends"],schedule)
                    if scenario=="clean":assert not r["injected"].any()
                    for s,t in zip(*np.where(r["injected"])):
                        assert cfg["attack"]["start"]<=t<=cfg["attack"]["end_inclusive"]
                        sender=cfg["attack"]["sender"]
                        assert r["sends"][s,t,sender]
                        if scenario=="replay_packet":
                            source=int(r["replay_source"][s,t]);assert 0<=source<t
                            assert r["sends"][s,source,sender]
                    start=cfg["attack"]["start"]+1
                    end=cfg["attack"]["end_inclusive"]+2
                    mse=np.sum((r["estimates"]-x[:,:,None,:])**2,axis=-1)[:,start:end].mean(axis=(1,2))
                    reported=np.asarray([float(lookup[protocol,method,scenario,seed]["mse_attack_window"]) for seed in seeds])
                    assert np.allclose(mse,reported,rtol=1e-12,atol=1e-12)
    report={"passed":True,"unique_metric_rows":len(rows),"test_seeds":len(seeds),"protocol_method_scenario_cases":expected//len(seeds),
            "checks":["disjoint development/test seeds","all stored estimates and weights finite","weights within [0,1]",
                      "identical reference sending schedules","all injections use actual packets in allowed window",
                      "all replay source packets actually transmitted earlier","reported attack MSE agrees with saved trajectories"]}
    write_json(folder/"output_audit.json",report)
    print(json.dumps(report))
    print(json.dumps([r for r in contrasts if r["protocol"]=="reference_schedule" and r["baseline"]=="interval_scale"]))


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("folder");a=p.parse_args();analyze(a.folder)
