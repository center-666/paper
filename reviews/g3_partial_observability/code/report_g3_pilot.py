"""Read-only descriptive reporting after the frozen Gate-A pilot stopped."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/"reviews/g3_partial_observability"
PILOT=BASE/"results/2026-11-13_g3_pilot_gate_a_r01"
METHODS=("local","raw_yang_no_cap","cap_only","cap_plus_zhou_random","cap_plus_spatial_hard")
RULES=("fixed_lag8","nearest_current_sender")


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")


def read_csv(path):
    with path.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))


def csv_write(path,rows):
    with path.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def main():
    p=argparse.ArgumentParser();p.add_argument("--run-id",default="2026-11-13_g3_stopped_pilot_report_r01")
    a=p.parse_args()
    if Path(a.run_id).name!=a.run_id:raise ValueError("Run ID must be one directory")
    out=BASE/"results"/a.run_id;out.mkdir(parents=True,exist_ok=False)
    before={f.relative_to(ROOT).as_posix():sha(f) for f in PILOT.rglob("*") if f.is_file()}
    write(out/"source_hashes_before.json",before)
    metric_rows=read_csv(PILOT/"per_seed_metrics.csv")
    lookup={(r["geometry"],r["method"],r["rule"],int(r["seed"])):r for r in metric_rows}
    normal_rows=read_csv(PILOT/"normal_episode_audit_per_seed.csv")
    derived=[];summary=[];normal_summary=[];episodes=[]
    plan=json.loads((BASE/"plan.json").read_text(encoding="utf-8"))
    for geometry in ("partial","full_rank_reference"):
        folder=PILOT/geometry
        cfg=json.loads((folder/"config.json").read_text(encoding="utf-8"))
        edges=np.asarray(cfg["edges_sender_receiver"])
        with np.load(folder/"pilot_inputs.npz") as f:
            x=f["x"];ids=f["seeds"];schedule=f["schedule"]
        for i,seed in enumerate(ids):
            events=np.flatnonzero(schedule[i,:,0])
            for index,start in enumerate(events):
                if start<cfg["warmup"]:continue
                stop=int(events[index+1]) if index+1<len(events) else cfg["T"]
                episodes.append({"geometry":geometry,"seed":int(seed),"start_tick":int(start),
                    "end_tick_exclusive":stop,"length":stop-int(start),"right_censored":index+1==len(events)})
        with np.load(folder/"pilot_trajectories.npz") as f:
            for method in METHODS:
                healthy=f[method+"__clean__estimates"]
                healthy_error=np.sum((healthy-x[:,:,None])**2,axis=-1)
                tolerance=.10*float(healthy_error[:,51:201,1].mean())
                for rule in RULES:
                    prefix=method+"__"+rule
                    estimate=f[prefix+"__estimates"]
                    err=np.sum((estimate-x[:,:,None])**2,axis=-1)
                    sends=f[prefix+"__sends"]
                    injected=f[prefix+"__injected"]
                    weights=f[prefix+"__weights"]
                    clipped=f[prefix+"__clipped"]
                    group=[]
                    for i,seed in enumerate(ids):
                        old=lookup[geometry,method,rule,int(seed)]
                        assert np.isclose(float(old["receiver_attack_mse"]),err[i,201:251,1].mean())
                        hits=np.flatnonzero(injected[i])
                        last=int(hits[-1]) if len(hits) else None
                        following=np.flatnonzero(sends[i,last+1:,0]) if last is not None else []
                        exit_tick=last+1+int(following[0]) if len(following) else None
                        exit_state=exit_tick+1 if exit_tick is not None else None
                        origin=251
                        return_start=None
                        for start in range(origin,len(err[i])-10+1):
                            if np.all(err[i,start:start+10,1] <= healthy_error[i,start:start+10,1]+tolerance):
                                return_start=start;break
                        # Time to the CONFIRMATION of ten-state tolerance return;
                        # administratively censored at final observable state400.
                        duration=(return_start+9-origin) if return_start is not None else 400-origin
                        row={**old,"last_replacement_tick":last,"cache_exit_tick":exit_tick,
                            "cache_exit_state":exit_state,"receiver_post_cache_exit_excess_mse":float((err[i]-healthy_error[i])[exit_state:,1].mean()) if exit_state is not None else None,
                            "receiver_post_cache_exit_cumulative_excess":float((err[i]-healthy_error[i])[exit_state:,1].sum()) if exit_state is not None else None,
                            "receiver_attack_max_error_norm":float(np.sqrt(err[i,201:251,1].max())),
                            "network_attack_max_error_norm":float(np.sqrt(err[i,201:251].max())),
                            "receiver_recovery_positive_part_excess":float(np.maximum(err[i,251:301,1]-healthy_error[i,251:301,1],0).sum()),
                            "recovery_tolerance_sq_error":tolerance,"recovery_origin_state":origin,
                            "first_ten_state_return_start":return_start,"confirmed_return_duration":duration,
                            "recovery_right_censored":return_start is None,
                            "network_receiver_clip_fraction_post_warmup":float(clipped[i,50:].mean()),
                            "target_rejection_fraction_attack_ticks":float(np.mean(weights[i,200:250,0]<=.5)) if method!="local" else None,
                            "trajectory_array_storage_bytes":int(estimate[i].nbytes)}
                        if method=="local":
                            row["first_ten_state_return_start"]=None
                            row["confirmed_return_duration"]=None
                            row["recovery_right_censored"]=None
                        derived.append(row);group.append(row)
                    s={"geometry":geometry,"method":method,"rule":rule,"seed_count":len(ids)}
                    for field in ("receiver_normal_mse","receiver_attack_mse","receiver_attack_excess_mse","receiver_recovery_excess_mse","receiver_recovery_cumulative_excess",
                                  "network_attack_mse","network_recovery_cumulative_excess","receiver_post_cache_exit_excess_mse",
                                  "receiver_post_cache_exit_cumulative_excess","receiver_attack_max_error_norm","actual_replacements","node_broadcasts","edge_messages","payload_bytes"):
                        val=[float(r[field]) for r in group if r[field] is not None]
                        s[field+"_mean"]=float(np.mean(val)) if val else None
                    valid=[r for r in group if r["confirmed_return_duration"] is not None]
                    s["restricted_mean_confirmed_return_duration"]=float(np.mean([r["confirmed_return_duration"] for r in valid])) if valid else None
                    s["return_right_censored_count"]=sum(r["recovery_right_censored"] for r in valid) if valid else None
                    summary.append(s)
                nr=[r for r in normal_rows if r["geometry"]==geometry and r["method"]==method]
                rejected=np.array([int(r["rejected_target_episodes"]) for r in nr])
                total=np.array([int(r["complete_target_episodes"]) for r in nr])
                rng=np.random.default_rng(11999999);idx=rng.integers(0,len(nr),size=(5000,len(nr)))
                bootstrap=rejected[idx].sum(axis=1)/np.maximum(total[idx].sum(axis=1),1)
                lo,hi=np.quantile(bootstrap,[.025,.975])
                normal_summary.append({"geometry":geometry,"method":method,"normal_episode_rejection_rate":float(rejected.sum()/total.sum()) if total.sum() else None,
                    "seed_cluster_ci95_low":float(lo) if total.sum() else None,"seed_cluster_ci95_high":float(hi) if total.sum() else None,
                    "total_rejected_episodes":int(rejected.sum()),"total_complete_episodes":int(total.sum()),
                    "per_method_runtime":"not instrumented in stopped pilot; no runtime superiority claim"})
    csv_write(out/"derived_per_seed_metrics.csv",derived)
    csv_write(out/"descriptive_method_summary.csv",summary)
    csv_write(out/"normal_episode_cluster_audit.csv",normal_summary)
    csv_write(out/"episode_lengths_and_censoring.csv",episodes)
    after={f.relative_to(ROOT).as_posix():sha(f) for f in PILOT.rglob("*") if f.is_file()}
    assert before==after
    write(out/"source_hashes_after.json",after)
    write(out/"validation.json",{"source_pilot_unchanged":True,"simulation_executed":False,
        "all_saved_attack_mse_reconstructed":True,"derived_seed_rows":len(derived),"summary_rows":len(summary),
        "normal_audit_rows":len(normal_summary),"plan_sha256":sha(BASE/"plan.json"),"reporter_sha256":sha(Path(__file__)),
        "gate_A_not_retested_or_retuned":True,"gate_B":"not run","confirm":"not run"})
    write(out/"output_hashes.json",{p.name:sha(p) for p in out.iterdir() if p.is_file()})
    print(json.dumps({"run_id":a.run_id,"source_unchanged":True,"derived_seed_rows":len(derived)}))


if __name__=="__main__":main()
