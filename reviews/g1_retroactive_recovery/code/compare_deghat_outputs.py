from __future__ import annotations

import csv
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[3]
BRANCH = Path(__file__).resolve().parents[1]
SIM = ROOT / "simulation"
OUT = BRANCH / "results" / "g1r_deghat_output_channels_20261112_02"
sys.path.insert(0, str(SIM))
sys.path.insert(0, str(BRANCH / "code"))

from engine import simulate
from model import generate_data
from minimal_recovery_screen import ATTACK_BIAS, D, Q, R, TARGET_EDGE_PAIR, TARGET_NODE, TEST, CAL, TRAIN, build_model, common_schedule, innovations

END = 260
CHANNELS = ("local_innovation", "local_innovation_plus_neighbor_disagreement")


def write_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def output_features(run, y, model, trial, times, include_disagreement):
    node = TARGET_NODE
    innovation = y[trial, times, node] - np.einsum("mn,tn->tm", model.H[node], run.estimates[trial, times, node])
    if not include_disagreement:
        return innovation.reshape(-1)
    incoming = np.flatnonzero(model.edges[:, 1] == node)
    disagreement = np.zeros_like(innovation)
    for edge in incoming:
        sender = model.edges[edge, 0]
        disagreement += run.estimates[trial, times, sender] - run.estimates[trial, times, node]
    return np.concatenate([innovation, disagreement], axis=1).reshape(-1)


def fit_covariance(samples, ridge_fraction=0.02):
    mean = samples.mean(axis=0)
    centered = samples - mean
    cov = centered.T @ centered / max(1, len(samples)-1)
    scale = max(float(np.trace(cov)/len(mean)), 1e-8)
    cov = (cov+cov.T)/2 + ridge_fraction*scale*np.eye(len(mean))
    return mean, cov, np.linalg.inv(cov)


def estimate(z, J, precision):
    info = J.T @ precision @ J
    cov = np.linalg.pinv(info, rcond=1e-10)
    theta = cov @ J.T @ precision @ z
    lr = float(z@precision@z-(z-J@theta)@precision@(z-J@theta))
    return theta, max(lr, 0.0)


def paired(values):
    x=np.asarray(values,float)
    mean=float(x.mean())
    half=float(stats.t.ppf(.975,len(x)-1)*x.std(ddof=1)/np.sqrt(len(x)))
    return {"n":len(x),"mean":mean,"ci95":[mean-half,mean+half]}


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    OUT.mkdir(parents=True)
    started=time.perf_counter()
    model=build_model()
    seeds=np.r_[TRAIN,CAL,TEST]
    x,y=generate_data(model,seeds)
    schedule=common_schedule(model,len(seeds))
    ntr,ncal=len(TRAIN),len(CAL)
    xtr,ytr,strn,schtr=x[:ntr],y[:ntr],TRAIN,schedule[:ntr]
    xcal,ycal,scal,schcal=x[ntr:ntr+ncal],y[ntr:ntr+ncal],CAL,schedule[ntr:ntr+ncal]
    xt,yt,st,sch=x[ntr+ncal:],y[ntr+ncal:],TEST,schedule[ntr+ncal:]
    target=int(np.flatnonzero(np.all(model.edges==TARGET_EDGE_PAIR,axis=1))[0])
    base_windows={
        "full_prefix":np.arange(R,D+1),
        "post_cache":np.arange(Q+1,D+1),
    }
    time_windows={f"{window}_{channel}":(times,channel=="augmented")
                  for window,times in base_windows.items()
                  for channel in ("local","augmented")}
    clean_tr=simulate(model,xtr,ytr,strn,"yang",schedule=schtr,collect=False)
    clean_cal=simulate(model,xcal,ycal,scal,"yang",schedule=schcal,collect=False)
    clean_test=simulate(model,xt,yt,st,"yang",schedule=sch,collect=False)

    # Estimate the injected payload offset by the exact fixed-mode response at this edge/time.
    old=model.cfg["attack"]["bias"]
    J_by_window={w:[] for w in time_windows}
    for direction in range(model.cfg["n"]):
        model.cfg["attack"]["bias"]=np.eye(model.cfg["n"])[direction].tolist()
        basis=simulate(model,xtr[:1],ytr[:1],strn[:1],"yang",scenario="single_step",schedule=schtr[:1],collect=False)
        for name,(times,include) in time_windows.items():
            base=output_features(clean_tr,ytr,model,0,times,include)
            attacked=output_features(basis,ytr,model,0,times,include)
            J_by_window[name].append(attacked-base)
    model.cfg["attack"]["bias"]=old
    J_by_window={k:np.column_stack(v) for k,v in J_by_window.items()}

    train_outputs={};cal_outputs={};mean_cov={};gate={}
    for name,(times,include) in time_windows.items():
        train_outputs[name]=np.asarray([output_features(clean_tr,ytr,model,i,times,include) for i in range(ntr)])
        cal_outputs[name]=np.asarray([output_features(clean_cal,ycal,model,i,times,include) for i in range(ncal)])
        mu,cov,precision=fit_covariance(train_outputs[name],ridge_fraction=.02)
        mean_cov[name]=(mu,cov,precision)
        scores=[]
        for z0 in cal_outputs[name]:
            _,lr=estimate(z0-mu,J_by_window[name],precision)
            scores.append(lr)
        gate[name]=float(np.quantile(scores,.95,method="higher"))

    per_seed=[];normal_rows=[]
    for scenario in ("single_step","replay_packet"):
        attacked=simulate(model,xt,yt,st,"yang",scenario=scenario,schedule=sch,collect=False)
        error=np.sum((xt[:,:,None,:]-attacked.estimates)**2,axis=-1)
        clean_error=np.sum((xt[:,:,None,:]-clean_test.estimates)**2,axis=-1)
        for i,seed in enumerate(st):
            if scenario=="replay_packet":
                source=int(attacked.replay_source[i,R])
                truth=clean_test.estimates[i,source,TARGET_EDGE_PAIR[0]]-clean_test.estimates[i,R,TARGET_EDGE_PAIR[0]]
            else:
                source=-1
                truth=ATTACK_BIAS.copy()
            for name,(times,include) in time_windows.items():
                obs=output_features(attacked,yt,model,i,times,include)
                mu,cov,precision=mean_cov[name]
                theta,lr=estimate(obs-mu,J_by_window[name],precision)
                trigger=bool(lr>gate[name])
                corrected=attacked.estimates[i].copy()
                # Sensitivity of all network estimate states to the event offset.
                sensitivity=[]
                for direction in range(model.cfg["n"]):
                    model.cfg["attack"]["bias"]=np.eye(model.cfg["n"])[direction].tolist()
                    basis=simulate(model,xt[i:i+1],yt[i:i+1],st[i:i+1],"yang",scenario="single_step",schedule=sch[i:i+1],collect=False)
                    sensitivity.append(basis.estimates[0]-clean_test.estimates[i])
                model.cfg["attack"]["bias"]=old
                S=np.stack(sensitivity,axis=-1)
                if trigger:
                    corrected[D+1:]-=np.einsum("tnip,p->tni",S[D+1:],theta)
                corrected_error=np.sum((xt[i,:,None,:]-corrected)**2,axis=-1)
                span=slice(D+1,END+1)
                per_seed.append({
                    "scenario":scenario,"window":name,"seed":int(seed),"source_time":source,
                    "source_age":R-source if source>=0 else 0,"replacement_count":int(attacked.injected[i,R]),
                    "feature_dim":len(obs),"ridge_fraction":.02,"gate":gate[name],"lr":lr,"trigger":trigger,
                    "offset_estimate_error_norm":float(np.linalg.norm(theta-truth)),
                    "receiver_excess_before":float((error[i,span,TARGET_NODE]-clean_error[i,span,TARGET_NODE]).mean()),
                    "receiver_excess_after":float((corrected_error[span,TARGET_NODE]-clean_error[i,span,TARGET_NODE]).mean()),
                    "network_excess_before":float((error[i,span]-clean_error[i,span]).mean()),
                    "network_excess_after":float((corrected_error[span]-clean_error[i,span]).mean()),
                })

    for i,seed in enumerate(st):
        for name,(times,include) in time_windows.items():
            obs=output_features(clean_test,yt,model,i,times,include)
            mu,cov,precision=mean_cov[name]
            _,lr=estimate(obs-mu,J_by_window[name],precision)
            normal_rows.append({"window":name,"seed":int(seed),"lr":lr,"gate":gate[name],"false_correction":bool(lr>gate[name])})

    summary=[]
    for scenario in ("single_step","replay_packet"):
        for name in time_windows:
            subset=[r for r in per_seed if r["scenario"]==scenario and r["window"]==name]
            summary.append({
                "scenario":scenario,"window":name,"feature_dim":subset[0]["feature_dim"],"n_seed":len(subset),
                "trigger_rate":float(np.mean([r["trigger"] for r in subset])),
                "mean_receiver_excess_before":float(np.mean([r["receiver_excess_before"] for r in subset])),
                "mean_receiver_excess_after":float(np.mean([r["receiver_excess_after"] for r in subset])),
                "mean_network_excess_after":float(np.mean([r["network_excess_after"] for r in subset])),
                "mean_offset_estimation_error":float(np.mean([r["offset_estimate_error_norm"] for r in subset])),
            })
    normal_summary={name:float(np.mean([r["false_correction"] for r in normal_rows if r["window"]==name])) for name in time_windows}
    write_json(OUT/"config.json",{
        "run_id":OUT.name,"parent":"G1-R minimal recovery screen",
        "method":"paired unknown-input GLS using local innovation only or local innovation plus Deghat-style neighbor disagreement; not Deghat's H-infinity/LMI detector",
        "model":"same Yang-form heterogeneous five-node model, same gap8 exogenous schedule",
        "attacked_edge":[0,1],"event_time":R,"cache_replacement_time":Q,"detection_time":D,
        "windows":{k:{"times":[int(v[0][0]),int(v[0][-1])],"include_neighbor_disagreement":v[1]}
                   for k,v in time_windows.items()},
        "seeds":{"train":TRAIN.tolist(),"calibration":CAL.tolist(),"test":TEST.tolist()},
        "normal_gate":"independent calibration 95th quantile of joint GLS likelihood improvement",
        "correction":"uses oracle-known event edge/time and global sensitivity for offline comparison; no communication is charged",
        "exploratory_only":True
    })
    write_csv(OUT/"per_seed.csv",per_seed)
    write_csv(OUT/"normal_audit.csv",normal_rows)
    write_json(OUT/"summary.json",{
        "run_id":OUT.name,"scenario_summaries":summary,"normal_false_correction_rates":normal_summary,
        "scope":"small comparator screen; common seeds, fixed schedule, known event; not method novelty evidence",
        "elapsed_seconds":time.perf_counter()-started
    })
    print(json.dumps(json.loads((OUT/"summary.json").read_text(encoding="utf-8")),ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
