from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from model import Model
from calibration import Calibration,quadratic,reference_evidence


@dataclass
class Run:
    estimates: np.ndarray
    sends: np.ndarray
    weights: np.ndarray
    observations: dict
    clipped: np.ndarray
    cache_bad: np.ndarray
    injected: np.ndarray
    replay_source: np.ndarray
    cap_norms: np.ndarray


def simulate(model: Model, x, y, seeds, method="yang", scenario="clean", schedule=None,
             calibration: Calibration|None=None, control=1.0, cap=np.inf,
             collect=True, cache_monitor=None) -> Run:
    cfg=model.cfg
    S,T,N,n = len(seeds),cfg["T"],cfg["N"],cfg["n"]
    E=len(model.edges)
    src,dst=model.edges.T
    edge_target=np.flatnonzero((src==cfg["attack"]["sender"]) & (dst==cfg["attack"]["receiver"]))[0]
    ah=cfg["attack"]
    estimates=np.zeros((S,T+1,N,n))
    sends=np.zeros((S,T,N),bool)
    weights=np.ones((S,T,E),np.float32)
    clipped=np.zeros((S,T,E),bool)
    cache_bad=np.zeros((S,T,E),bool)
    injected=np.zeros((S,T),bool)
    replay_source=np.full((S,T),-1,int)
    last_send_time=np.full((S,N),-cfg["max_interval"],int)
    last_send_value=np.zeros((S,N,n))
    last_receive=np.full((S,E),-1,int)
    payload=np.zeros((S,E,n))
    last_space=np.zeros((S,E,n))
    weight=np.ones((S,E))
    bad=np.zeros((S,E),bool)
    rngs=[np.random.default_rng(int(seed)+9100000) for seed in seeds]
    # Zhou 2022 draws one random threshold per RECEIVING NODE and time,
    # shared across its incoming edges. Independent edge coins would preserve
    # marginal acceptance rates but change the joint protection mechanism.
    coins=np.stack([r.random((T,N)) for r in rngs])
    data={k:[] for k in ("trajectory","time","edge","delta","reason","space","previous_space","temporal","time_valid","distance_squared","weight","combined_score","spatial_ratio","temporal_ratio","injected")}
    cap_samples=[]
    gains=model.local_gains if method=="local" else model.gains
    for t in range(T):
        hat=estimates[:,t]
        innovation=y[:,t]-np.einsum("imn,sin->sim",model.H,hat)
        local_update=np.einsum("imn,sin->sim",gains[t],innovation)
        base=hat @ model.A.T + local_update
        if method=="local":
            estimates[:,t+1]=base
            continue
        if schedule is None:
            crossed=np.sum((hat-last_send_value)**2,axis=-1)>cfg["send_delta_squared"]
            timeout=(t-last_send_time)>=cfg["max_interval"]
            transmit=crossed|timeout
            reason=np.where(crossed,1,np.where(timeout,2,0))
        else:
            transmit=schedule[:,t].copy()
            reason=np.where(transmit,4,0)
        if t==0:
            transmit[:]=True
            reason[:]=3
        sends[:,t]=transmit
        last_send_value=np.where(transmit[...,None],hat,last_send_value)
        last_send_time=np.where(transmit,t,last_send_time)
        fresh=transmit[:,src]
        incoming=hat[:,src].copy()
        injected_now=np.zeros((S,E),bool)
        if scenario!="clean" and ah["start"]<=t<=ah["end_inclusive"]:
            selected=np.flatnonzero(fresh[:,edge_target])
            for s in selected:
                if scenario in {"single_step","alternating"}:
                    index=int(sends[s,ah["start"]:t+1,src[edge_target]].sum())-1
                    fraction=(1.0 if index==0 else 0.0) if scenario=="single_step" else (1.0 if index%2==0 else .25)
                    incoming[s,edge_target]+=fraction*np.asarray(ah["bias"])
                    injected_now[s,edge_target]=fraction>0
                elif scenario in {"step","ramp","low_step","half_step"}:
                    fraction=(t-ah["start"])/max(1,ah["end_inclusive"]-ah["start"]) if scenario=="ramp" else ah.get("low_bias_factor",.25) if scenario=="low_step" else .5 if scenario=="half_step" else 1.0
                    incoming[s,edge_target]+=fraction*np.asarray(ah["bias"])
                    injected_now[s,edge_target]=fraction>0
                elif scenario=="replay_packet":
                    previous=np.flatnonzero(sends[s,:t,src[edge_target]])
                    lag=ah["replay_packet_lag"]
                    if len(previous)>=lag:
                        source=int(previous[-lag])
                        incoming[s,edge_target]=estimates[s,source,src[edge_target]]
                        replay_source[s,t]=source
                        injected_now[s,edge_target]=True
                elif scenario=="replay_matched":
                    source=t-ah["matched_replay_time_lag"]
                    if source>=0 and sends[s,source,src[edge_target]]:
                        incoming[s,edge_target]=estimates[s,source,src[edge_target]]
                        replay_source[s,t]=source
                        injected_now[s,edge_target]=True
                else:
                    raise ValueError(scenario)
        injected[:,t]=injected_now[:,edge_target]
        delta=np.where(last_receive>=0,t-last_receive,1)
        time_valid=last_receive>=0
        temporal=incoming-np.einsum("seij,sej->sei",model.powers[delta],payload)
        space=y[:,t,dst]-np.einsum("emn,sen->sem",model.H[dst],incoming)
        distance_squared=np.sum((incoming-hat[:,dst])**2,axis=-1)
        combined=np.zeros((S,E));js=np.zeros((S,E));jt=np.zeros((S,E))
        if method in {"pooled","interval_scale","interval_tail","tail_shared_scale","spatial_hard","spatial_soft","reference_reset","reference_soft"}:
            if calibration is None: raise ValueError("Missing normal calibration")
            combined,js,jt=calibration.scores(space,temporal,delta,time_valid,cfg)
            if method in {"spatial_soft","reference_reset","reference_soft"}:
                previous_ratio=quadratic(last_space,calibration.space_mu,calibration.space_precision)/calibration.space_q
                combined=reference_evidence(js,jt,previous_ratio,time_valid,method,cfg)
            proposed=np.exp(-control*combined) if method!="spatial_hard" else (js<=control).astype(float)
        elif method=="zhou_random":
            # Conditional acceptance probability matches Zhou's exponential threshold mechanism.
            proposed=(coins[:,t,dst]<=np.exp(-distance_squared/control)).astype(float)
        else:
            proposed=np.ones((S,E))
        weight=np.where(fresh,proposed,weight)
        if method=="fresh_only_cap":weight=fresh.astype(float)
        payload=np.where(fresh[...,None],incoming,payload)
        last_receive=np.where(fresh,t,last_receive)
        bad=np.where(fresh,injected_now,bad)
        age=np.maximum(t-last_receive,0)
        aligned=np.einsum("seij,sej->sei",model.powers[age],payload)
        if cache_monitor is not None:
            # The monitor sees only legal received cache, own measurements/estimate,
            # local reception age and whether a new packet arrived. Never incoming.
            weight=cache_monitor.update(t,fresh,age,aligned,y[:,t,dst],hat[:,dst])
        difference=aligned-hat[:,dst]
        norms=np.linalg.norm(difference,axis=-1)
        if method!="yang":
            ratio=np.minimum(1.0,cap/np.maximum(norms,1e-15))
        else:
            ratio=np.ones_like(norms)
        clipped[:,t]=(ratio<1)
        terms=weight[...,None]*ratio[...,None]*difference
        consensus=np.zeros((S,N,n))
        for e,i in enumerate(dst): consensus[:,i]+=terms[:,e]
        estimates[:,t+1]=base+cfg["epsilon"]*(consensus @ model.A.T)
        weights[:,t]=weight
        cache_bad[:,t]=bad
        if collect and t>=cfg["warmup"]:
            s,e=np.where(fresh)
            arrays={"trajectory":s,"time":np.full(len(s),t),"edge":e,"delta":delta[s,e],
                    "reason":reason[s,src[e]],"space":space[s,e],"previous_space":last_space[s,e].copy(),"temporal":temporal[s,e],
                    "time_valid":time_valid[s,e],"distance_squared":distance_squared[s,e],
                    "weight":weight[s,e],"combined_score":combined[s,e],
                    "spatial_ratio":js[s,e],"temporal_ratio":jt[s,e],"injected":injected_now[s,e]}
            for k,v in arrays.items():data[k].append(v)
            cap_samples.append(norms.copy())
        last_space=np.where(fresh[...,None],space,last_space)
    observations={k:np.concatenate(v,axis=0) if v else np.empty((0,n)) if k in {"space","previous_space","temporal"} else np.empty(0) for k,v in data.items()}
    return Run(estimates,sends,weights,observations,clipped,cache_bad,injected,replay_source,
               np.stack(cap_samples,axis=1) if cap_samples else np.empty(0))


def subset_observations(obs, lower, upper):
    keep=(obs["trajectory"]>=lower)&(obs["trajectory"]<upper)
    return {k:v[keep] for k,v in obs.items()}


def basic_metrics(model, run, x):
    cfg=model.cfg
    sq=np.sum((run.estimates-x[:,:,None,:])**2,axis=-1)
    a=cfg["attack"]
    # Injection at t affects estimate at t+1.
    attack_slice=slice(a["start"]+1,a["end_inclusive"]+2)
    recovery_slice=slice(a["end_inclusive"]+2,min(cfg["T"]+1,a["end_inclusive"]+2+a["recovery_steps"]))
    out={"mse_all":sq[:,cfg["warmup"]+1:].mean(axis=(1,2)),
         "mse_attack_window":sq[:,attack_slice].mean(axis=(1,2)),
         "mse_recovery":sq[:,recovery_slice].mean(axis=(1,2)),
         "node_broadcasts":run.sends.sum(axis=(1,2)),
         "edge_messages":run.sends[:,:,model.edges[:,0]].sum(axis=(1,2)),
         "injected_packets":run.injected.sum(axis=1),
         "clip_fraction":run.clipped[:,cfg["warmup"]:].mean(axis=(1,2))}
    out["payload_bytes"]=out["edge_messages"]*cfg["n"]*8
    S=len(x)
    obs=run.observations
    for name in ("received_low_weight_rate","mean_received_weight","direct_attack_low_weight_rate"):
        out[name]=np.full(S,np.nan)
    for s in range(S):
        mask=obs["trajectory"]==s
        if np.any(mask):
            out["received_low_weight_rate"][s]=np.mean(obs["weight"][mask]<cfg["low_weight_threshold"])
            out["mean_received_weight"][s]=np.mean(obs["weight"][mask])
        mask=mask & obs["injected"].astype(bool)
        if np.any(mask):out["direct_attack_low_weight_rate"][s]=np.mean(obs["weight"][mask]<cfg["low_weight_threshold"])
    return out,sq
