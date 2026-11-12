"""Audit saved corrected-ablation artifacts without rerunning or tuning estimators."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
from calibration import interval_bins,quadratic,quantile
from run_study import write_json


def main(folder):
    folder=Path(folder)
    plan=json.loads((folder/"plan.json").read_text(encoding="utf-8"))
    reg=json.loads((folder/"preregistration.json").read_text(encoding="utf-8"))
    assert hashlib.sha256((folder/"plan.json").read_bytes()).hexdigest()==reg["plan_sha256"]
    for name,digest in reg["source_sha256"].items():assert hashlib.sha256((folder/"sources"/name).read_bytes()).hexdigest()==digest
    with (folder/"per_seed_metrics.csv").open(encoding="utf-8-sig",newline="") as f:rows=list(csv.DictReader(f))
    ix={(r["setting"],r["method"],r["scenario"],int(r["seed"])):r for r in rows}
    assert len(ix)==len(rows)
    expected_cases=0;matched_pairs=0;max_difference=0;shared_fields_checked=0
    for setting in [r["id"] for r in plan["regimes"]]:
        path=folder/setting
        cfg=json.loads((path/"config.json").read_text(encoding="utf-8"))
        splitsets=[set(range(s["start"],s["start"]+s["count"])) for s in plan["splits"].values()]
        for i,a in enumerate(splitsets):
            for b in splitsets[i+1:]:assert not a&b
        with np.load(path/"interval_scale_calibration.npz") as a,np.load(path/"tail_shared_scale_calibration.npz") as b,np.load(path/"shared_normal_calibration_residuals.npz") as obs:
            for name in ("space_mu","space_precision","space_q","time_mu","time_precision","train_counts","cal_counts","fallback"):
                assert np.array_equal(a[name],b[name]);shared_fields_checked+=1
            bins=interval_bins(obs["delta"],cfg)
            for e in range(len(cfg["edges_sender_receiver"])):
                selected=(obs["edge"]==e)&obs["time_valid"]
                js=quadratic(obs["temporal"][selected],a["time_mu"][e,bins[selected]],a["time_precision"][e,bins[selected]])
                pooled=max(quantile(js,cfg["marginal_quantile"]),1e-10)
                for group in range(len(cfg["interval_upper_bounds"])):
                    mask=bins[selected]==group
                    q=max(quantile(js[mask],cfg["marginal_quantile"]),1e-10) if mask.sum()>=cfg["minimum_bin_samples"] and not a["fallback"][e,group] else pooled
                    assert np.isclose(a["time_q"][e,group],pooled,rtol=1e-12)
                    assert np.isclose(b["time_q"][e,group],q,rtol=1e-12)
        with np.load(path/"test_inputs.npz") as f:x,seeds,schedule=f["x"],f["seeds"],f["schedule"]
        assert np.array_equal(seeds,np.arange(plan["splits"]["test"]["start"],plan["splits"]["test"]["start"]+plan["splits"]["test"]["count"]))
        scenarios=plan["common_scenarios"]+(plan["extra_repeated_scenarios"] if setting=="repeated_gaps" else [])
        for method in plan["methods"]:
            for scenario in scenarios:
                expected_cases+=1
                with np.load(path/(method+"__"+scenario+".npz")) as f:
                    assert np.array_equal(f["sends"],schedule)
                    assert np.isfinite(f["estimates"]).all()
                    assert np.all((f["weights"]>=0)&(f["weights"]<=1))
                    start,end=cfg["attack"]["start"],cfg["attack"]["end_inclusive"]
                    loss=np.sum((f["estimates"][:,start+1:end+2]-x[:,start+1:end+2,None,:])**2,axis=-1).mean(axis=(1,2))
                    saved=np.asarray([float(ix[setting,method,scenario,int(seed)]["mse_attack_window"]) for seed in seeds])
                    error=float(np.max(np.abs(loss-saved)));max_difference=max(max_difference,error);assert error<1e-12
                    if scenario=="replay_matched":
                        sender=cfg["attack"]["sender"]
                        for s in range(len(seeds)):
                            t=np.flatnonzero(f["injected"][s]);old=f["replay_source"][s,t]
                            assert np.array_equal(t,np.flatnonzero(schedule[s,start:end+1,sender])+start)
                            assert np.all(schedule[s,t,sender]) and np.all(schedule[s,old,sender])
                            assert np.all(t-old==plan["matched_replay_time_lag"])
                            assert np.array_equal(np.diff(t),np.diff(old));matched_pairs+=max(0,len(t)-1)
    assert len(rows)==expected_cases*plan["splits"]["test"]["count"]
    result={"passed":True,"source_hashes_match":True,"plan_hash_matches":True,"method_case_count":expected_cases,"metric_rows":len(rows),
        "identical_calibration_fields_checked":shared_fields_checked,"pooled_and_grouped_q_recomputed_from_same_saved_normal_residuals":True,
        "saved_mse_max_difference":max_difference,"matched_replay_successive_pairs_checked":matched_pairs,"no_new_simulations":True}
    write_json(folder/"output_audit.json",result)
    import shutil
    dest=folder/"post_analysis_sources";dest.mkdir(exist_ok=True)
    shutil.copy2(__file__,dest/Path(__file__).name)
    print(json.dumps(result))


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("folder");args=p.parse_args();main(args.folder)
