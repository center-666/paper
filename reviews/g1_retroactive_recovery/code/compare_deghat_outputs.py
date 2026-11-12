from __future__ import annotations

import csv
import ast
import hashlib
import inspect
import json
import sys
import time
import textwrap
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[3]
BRANCH = Path(__file__).resolve().parents[1]
SIM = ROOT / "simulation"
OUT = BRANCH / "results" / "g1r_deghat_output_channels_20261112_07"
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


class ReceiverCacheLog:
    def __init__(self, model, batch, horizon):
        self.edges=len(model.edges)
        self.nodes=model.cfg["N"]
        self.n=model.cfg["n"]
        self.dst=model.edges[:,1]
        self.aligned=np.zeros((batch,horizon,self.edges,self.n))
        self.local=np.zeros((batch,horizon,self.nodes,self.n))
        self.fresh=np.zeros((batch,horizon,self.edges),bool)
        self.receive_time=np.full((batch,horizon,self.edges),-1,int)
        self.last_received=np.full((batch,self.edges),-1,int)

    def update(self,t,fresh,age,aligned,measurement,local_hat):
        self.aligned[:,t]=aligned
        self.fresh[:,t]=fresh
        self.local[:,t]=0
        for edge,node in enumerate(self.dst):
            self.local[:,t,node]=local_hat[:,edge]
            self.last_received[:,edge]=np.where(fresh[:,edge],t,self.last_received[:,edge])
            self.receive_time[:,t,edge]=self.last_received[:,edge]
        return np.ones(fresh.shape)


def logged_run(model,x,y,seeds,schedule,scenario="clean"):
    monitor=ReceiverCacheLog(model,len(seeds),model.cfg["T"])
    run=simulate(model,x,y,seeds,"yang",scenario=scenario,schedule=schedule,
                 cache_monitor=monitor,collect=False)
    return run,monitor


def output_features(receiver_log, y, model, trial, times, include_disagreement):
    node = TARGET_NODE
    own=receiver_log.local[trial,times,node]
    innovation = y[trial, times, node] - np.einsum("mn,tn->tm", model.H[node], own)
    if not include_disagreement:
        return innovation.reshape(-1)
    incoming = np.flatnonzero(model.edges[:, 1] == node)
    disagreement = np.zeros_like(innovation)
    for edge in incoming:
        # The log stores only the cache prediction the receiver had at this tick.
        disagreement += receiver_log.aligned[trial,times,edge] - own
    return np.concatenate([innovation, disagreement], axis=1).reshape(-1)


def event_sensitivity(model,schedule,event_edge,event_time):
    """Differentiate the fixed-mode estimator using public model and send times only."""
    T,N,n,p=model.cfg["T"],model.cfg["N"],model.cfg["n"],model.cfg["n"]
    E=len(model.edges);src,dst=model.edges.T
    state=np.zeros((T+1,N,n,p))
    cache=np.zeros((E,n,p))
    last=np.full(E,-1,int)
    aligned_hist=np.zeros((T,E,n,p))
    for t in range(T):
        fresh=schedule[t,src]
        for e,j in enumerate(src):
            if not fresh[e]:
                continue
            cache[e]=np.eye(p) if e==event_edge and t==event_time else state[t,j]
            last[e]=t
        age=np.where(last>=0,t-last,0)
        aligned=np.stack([model.powers[age[e]]@cache[e] for e in range(E)])
        aligned_hist[t]=aligned
        consensus=np.zeros((N,n,p))
        for e,i in enumerate(dst):
            consensus[i]+=aligned[e]-state[t,i]
        # Axes are (node, state_component, attack_component): A acts on the left.
        local=np.einsum("ab,nbp->nap",model.A,state[t])
        for i in range(N):
            innovation=-model.H[i]@state[t,i]
            local[i]+=model.gains[t,i]@innovation
        state[t+1]=local+model.cfg["epsilon"]*np.einsum("ab,nbp->nap",model.A,consensus)
    return state,aligned_hist


def feature_sensitivity(state,aligned,model,times,include_disagreement):
    node=TARGET_NODE
    rows=[]
    incoming=np.flatnonzero(model.edges[:,1]==node)
    for t in times:
        innovation=-model.H[node]@state[t,node]
        if include_disagreement:
            disagreement=np.zeros_like(innovation)
            for edge in incoming:
                disagreement+=aligned[t,edge]-state[t,node]
            rows.append(np.concatenate([innovation,disagreement],axis=0))
        else:
            rows.append(innovation)
    return np.asarray(rows).reshape(-1,model.cfg["n"])


def audit_feature_permissions():
    tree=ast.parse(textwrap.dedent(inspect.getsource(output_features)))
    forbidden={"estimates","true_state","state_truth","replay_source","injected","source_time","x"}
    used={node.attr for node in ast.walk(tree) if isinstance(node,ast.Attribute)}
    leaked=sorted(used & forbidden)
    if leaked:
        raise AssertionError(f"Feature extraction accesses privileged fields: {leaked}")
    return {"passed":True,"forbidden_attributes_absent":sorted(forbidden),
            "allowed_sources":["receiver_log.local","receiver_log.aligned","y","model.H"],
            "source":"AST inspection of online output_features function"}


def audit_receiver_cache(model,run,log,trial,scenario,schedule):
    target=int(np.flatnonzero(np.all(model.edges==TARGET_EDGE_PAIR,axis=1))[0])
    payload=np.zeros((len(model.edges),model.cfg["n"]))
    last=np.full(len(model.edges),-1,int)
    errors=[]
    for t in range(model.cfg["T"]):
        for edge,(sender,receiver) in enumerate(model.edges):
            if not run.sends[trial,t,sender]:
                continue
            if edge==target and run.injected[trial,t]:
                source=int(run.replay_source[trial,t])
                if source>=0:
                    if source>=t or not run.sends[trial,source,sender]:
                        raise AssertionError("Replay audit found a nonhistorical or unsent source")
                    payload[edge]=run.estimates[trial,source,sender]
                else:
                    payload[edge]=run.estimates[trial,t,sender]+np.asarray(model.cfg["attack"]["bias"],float)
            else:
                payload[edge]=run.estimates[trial,t,sender]
            last[edge]=t
        age=np.maximum(t-last,0)
        expected=np.stack([model.powers[age[e]]@payload[e] for e in range(len(model.edges))])
        errors.append(float(np.max(np.abs(expected-log.aligned[trial,t]))))
    return {"scenario":scenario,"trial":int(trial),"max_logged_cache_reconstruction_error":max(errors),
            "source_times_checked":True,"offline_only_uses_simulated_packets_for_audit":True}


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
    permission_audit=audit_feature_permissions()
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
    clean_tr,log_tr=logged_run(model,xtr,ytr,strn,schtr,"clean")
    clean_cal,log_cal=logged_run(model,xcal,ycal,scal,schcal,"clean")
    clean_test,log_test=logged_run(model,xt,yt,st,sch,"clean")
    vanilla_test=simulate(model,xt,yt,st,"yang",schedule=sch,collect=False)
    receiver_logger_equivalence_error=float(np.max(np.abs(clean_test.estimates-vanilla_test.estimates)))
    sensitivity,aligned_sensitivity=event_sensitivity(model,sch[0],target,R)

    # Estimate the injected payload offset by the exact fixed-mode response at this edge/time.
    J_by_window={name:feature_sensitivity(sensitivity,aligned_sensitivity,model,times,include)
                 for name,(times,include) in time_windows.items()}

    train_outputs={};cal_outputs={};mean_cov={};gate={}
    for name,(times,include) in time_windows.items():
        train_outputs[name]=np.asarray([output_features(log_tr,ytr,model,i,times,include) for i in range(ntr)])
        cal_outputs[name]=np.asarray([output_features(log_cal,ycal,model,i,times,include) for i in range(ncal)])
        mu,cov,precision=fit_covariance(train_outputs[name],ridge_fraction=.02)
        mean_cov[name]=(mu,cov,precision)
        scores=[]
        for z0 in cal_outputs[name]:
            _,lr=estimate(z0-mu,J_by_window[name],precision)
            scores.append(lr)
        gate[name]=float(np.quantile(scores,.95,method="higher"))

    per_seed=[];normal_rows=[];packet_permission_audits=[]
    for scenario in ("single_step","replay_packet"):
        attacked,attacked_log=logged_run(model,xt,yt,st,sch,scenario)
        audits=[audit_receiver_cache(model,attacked,attacked_log,i,scenario,sch[i])
                for i in range(len(st))]
        packet_permission_audits.append({
            "scenario":scenario,"trial_count":len(audits),
            "max_logged_cache_reconstruction_error":max(r["max_logged_cache_reconstruction_error"] for r in audits),
            "all_sources_were_prior_transmissions":all(r["source_times_checked"] for r in audits),
            "offline_audit_only_uses_simulated_packets":all(r["offline_only_uses_simulated_packets_for_audit"] for r in audits),
        })
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
                obs=output_features(attacked_log,yt,model,i,times,include)
                mu,cov,precision=mean_cov[name]
                theta,lr=estimate(obs-mu,J_by_window[name],precision)
                trigger=bool(lr>gate[name])
                corrected=attacked.estimates[i].copy()
                if trigger:
                    corrected[D+1:]-=np.einsum("tnip,p->tni",sensitivity[D+1:],theta)
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
            obs=output_features(log_test,yt,model,i,times,include)
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
    sources=[Path(__file__),SIM/"engine.py",SIM/"model.py",BRANCH/"code/minimal_recovery_screen.py",
             SIM/"config.json",SIM/"reference_exploration_plan.json"]
    source_hashes={p.name:sha256(p) for p in sources}
    write_json(OUT/"config.json",{
        "run_id":OUT.name,"parent":"G1-R minimal recovery screen",
        "method":"paired unknown-input GLS using local innovation only or local innovation plus cache-based neighbor disagreement; not Deghat's H-infinity/LMI detector",
        "model":"same Yang-form heterogeneous five-node model, same gap8 exogenous schedule",
        "attacked_edge":[0,1],"event_time":R,"cache_replacement_time":Q,"detection_time":D,
        "windows":{k:{"times":[int(v[0][0]),int(v[0][-1])],"include_neighbor_disagreement":v[1]}
                   for k,v in time_windows.items()},
        "seeds":{"train":TRAIN.tolist(),"calibration":CAL.tolist(),"test":TEST.tolist()},
        "normal_gate":"independent calibration 95th quantile of joint GLS likelihood improvement",
        "correction":"uses oracle-known event edge/time and model-derived fixed-schedule global sensitivity for offline comparison; no communication is charged",
        "information_permissions":"feature extraction uses only local measurement, own estimate, actual cache predictions produced by the receiver protocol, reception times and A^age; it does not read simulator sender trajectories",
        "offline_model_response":"unit response matrix is computed by a public-model/schedule difference recursion, not by reading true state or untransmitted neighbor estimates",
        "permission_audits":{"feature_ast":permission_audit,"receiver_logger_matches_vanilla_yang_max_abs_error":receiver_logger_equivalence_error,
                             "cache_reconstruction":packet_permission_audits},
        "source_hashes":source_hashes,
        "exploratory_only":True
    })
    write_csv(OUT/"per_seed.csv",per_seed)
    write_csv(OUT/"normal_audit.csv",normal_rows)
    write_json(OUT/"summary.json",{
        "run_id":OUT.name,"scenario_summaries":summary,"normal_false_correction_rates":normal_summary,
        "information_permission_audit":permission_audit,
        "receiver_logger_matches_vanilla_yang_max_abs_error":receiver_logger_equivalence_error,
        "offline_cache_reconstruction_audits":packet_permission_audits,
        "source_hashes":source_hashes,
        "scope":"small comparator screen; common seeds, fixed schedule, known event; not method novelty evidence",
        "elapsed_seconds":time.perf_counter()-started
    })
    print(json.dumps(json.loads((OUT/"summary.json").read_text(encoding="utf-8")),ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
