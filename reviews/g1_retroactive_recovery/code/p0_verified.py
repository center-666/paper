"""Final P0 rerun. Protected shared files are read only; no fresh performance claim."""
from __future__ import annotations
import argparse
import copy
import csv
import hashlib
import json
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from scipy import stats
import compare_deghat_outputs as channels
from minimal_recovery_screen import build_model, common_schedule, TRAIN, CAL, TEST, R, Q, D
from model import generate_data
from engine import simulate

BRANCH = Path(__file__).resolve().parents[1]
ROOT = BRANCH.parents[1]
BASE = "db7dabd8cbb9b425482bc9693b065fd25865d720"
PROTECTED = ("simulation/engine.py", "simulation/g2_replay_runner.py",
             "reviews/fdi_replay_20261112/g2_screen_plan.json")


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def json_out(p, x):
    def native(v):
        if isinstance(v, np.ndarray): return v.tolist()
        if isinstance(v, np.generic): return v.item()
        raise TypeError(type(v).__name__)
    Path(p).write_text(json.dumps(x, ensure_ascii=False, indent=2, default=native), encoding="utf-8")


def csv_out(p, rows):
    with Path(p).open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def difference(model, schedule, delta, event_edge):
    """Only public matrices/schedule and the one injected vector enter this function."""
    T, N, n = model.cfg["T"], model.cfg["N"], model.cfg["n"]
    state = np.zeros((T+1, N, n))
    raw = np.zeros((T, len(model.edges), n))
    aligned = np.zeros_like(raw)
    clocks = np.zeros((T, len(model.edges)), int)
    last = np.full(len(model.edges), -1, int)
    cache = np.zeros((len(model.edges), n))
    for t in range(T):
        for e, (j, i) in enumerate(model.edges):
            if schedule[t, j]:
                cache[e] = state[t, j]
                if t == R and e == event_edge:
                    cache[e] += delta
                last[e] = t
            assert last[e] >= 0
            aligned[t, e] = np.linalg.matrix_power(model.A, t-last[e]) @ cache[e]
        raw[t] = cache; clocks[t] = last
        for i in range(N):
            f = model.A - model.gains[t, i] @ model.H[i]
            s = np.zeros(n)
            for e, (j, dest) in enumerate(model.edges):
                if dest == i: s += aligned[t, e] - state[t, i]
            state[t+1, i] = f @ state[t, i] + model.cfg["epsilon"] * model.A @ s
    return state, raw, aligned, clocks


class Log:
    """Callback observations, independent of latent state and attack metadata."""
    def __init__(self, model, count):
        T, E, n = model.cfg["T"], len(model.edges), model.cfg["n"]
        self.dst = model.edges[:, 1]
        self.aligned = np.zeros((count,T,E,n))
        self.raw = np.zeros_like(self.aligned)
        self.cache = np.zeros((count,E,n))
        self.clocks = np.full((count,T,E), -1, int)
        self.last = np.full((count,E), -1, int)
        self.own = np.zeros((count,T,model.cfg["N"],n))
        self.local_y = np.zeros_like(self.own)
    def update(self, t, fresh, age, aligned, measurement, local_hat):
        self.aligned[:,t] = aligned
        self.cache = np.where(fresh[...,None], aligned, self.cache)
        self.last = np.where(fresh, t, self.last)
        self.raw[:,t] = self.cache; self.clocks[:,t] = self.last
        assert np.array_equal(t-self.last, age)
        for e, i in enumerate(self.dst):
            self.own[:,t,i] = local_hat[:,e]
            self.local_y[:,t,i] = measurement[:,e]
        return np.ones(fresh.shape)


def reference(model, x, y, seeds, schedule, scenario):
    log = Log(model,len(seeds))
    run = simulate(model,x,y,seeds,"yang",scenario=scenario,schedule=schedule,
                   collect=False,cache_monitor=log)
    return run, log


def features(local_y, own, received_aligned, H):
    """Receiver-only interface: no run object, scenario labels, or hidden neighbors."""
    innovation = local_y - np.einsum("ab,stb->sta", H, own)
    disagreement = np.sum(received_aligned - own[:,:,None,:], axis=2)
    return innovation, np.concatenate((innovation,disagreement),axis=2)


def ci(v):
    v=np.asarray(v,float); m=float(v.mean())
    d=float(stats.t.ppf(.975,len(v)-1)*v.std(ddof=1)/np.sqrt(len(v)))
    return {"n_seed":len(v),"mean":m,"ci95":[m-d,m+d]}


def main(out):
    out=Path(out); out.mkdir(parents=True,exist_ok=False)
    started=time.perf_counter()
    model=build_model(); T=model.cfg["T"]; N=model.cfg["N"]; n=model.cfg["n"]
    edge=next(e for e,x in enumerate(model.edges) if tuple(x)==(0,1))
    incoming=np.flatnonzero(model.edges[:,1]==1)
    protected={p:digest(ROOT/p) for p in PROTECTED}
    historical={str(p.relative_to(BRANCH)):digest(p)
                for p in (BRANCH/"results").rglob("*") if p.is_file() and out not in p.parents}
    atol=1e-10
    cfg={"run_id":out.name,"baseline_commit":BASE,"created_utc":datetime.now(timezone.utc).isoformat(),
         "scope":"fixed exogenous gap8, same existing seeds; exploratory rerun, not independent confirmation",
         "model":model.cfg,"r":R,"q":Q,"d":D,"recovery_state_indices":[D+1,260],
         "seeds":{"train":TRAIN,"calibration":CAL,"test":TEST},
         "absolute_tolerance":atol,"prior_failed_outputs_seen":True,
         "tolerance_scope":"regression test threshold; registered before this run, not a rigorous roundoff bound",
         "covariance_ridge_relative":.02,"normal_quantile":.95,
         "windows":{"full_prefix":[R,D],"post_cache":[Q+1,D]},
         "protected_sha256_before":protected,
         "correction_mode":"output-only shadow subtraction; no corrected-state write-back or correction broadcast"}
    json_out(out/"config.json",cfg)
    sources=[Path(__file__),BRANCH/"code/compare_deghat_outputs.py",
             BRANCH/"code/minimal_recovery_screen.py",ROOT/"simulation/model.py",ROOT/"simulation/engine.py"]
    json_out(out/"source_hashes.json",{str(p.relative_to(ROOT)):digest(p) for p in sources})
    try:
        test_sch=common_schedule(model,len(TEST))
        base_sch=test_sch[0]
        inputs={}
        clean={}
        for split,seeds in (("train",TRAIN),("calibration",CAL),("test",TEST)):
            x,y=generate_data(model,seeds); sch=common_schedule(model,len(seeds))
            inputs[split]=(x,y,seeds,sch)
            clean[split]=reference(model,x,y,seeds,sch,"clean")
        x,y,seeds,sch=inputs["test"]; c,clog=clean["test"]
        vanilla=simulate(model,x,y,seeds,"yang",schedule=sch,collect=False)
        assert np.array_equal(vanilla.estimates,c.estimates)
        S,Sa=channels.event_sensitivity(model,base_sch,edge,R)
        # Model-only left multiplication must match two independent unit-input simulations.
        unit_checks=[]
        for direction in range(n):
            mc=copy.deepcopy(model); mc.cfg["attack"]["bias"]=np.eye(n)[direction].tolist()
            ur,ul=reference(mc,x[:2],y[:2],seeds[:2],sch[:2],"single_step")
            er=float(np.max(np.abs(ur.estimates-c.estimates[:2]-S[None,...,direction])))
            ec=float(np.max(np.abs(ul.aligned-clog.aligned[:2]-Sa[None,...,direction])))
            unit_checks.append({"direction":direction,"state_max_error":er,"aligned_max_error":ec})
            assert max(er,ec)<atol
        node_rows=[]; cache_rows=[]; send_rows=[]; metrics=[]; nrows=[]; summaries=[]
        attack_refs={}
        windows={"full_prefix":np.arange(R,D+1),"post_cache":np.arange(Q+1,D+1)}
        fit={}; features_all={}
        for split,(run,log) in clean.items():
            features_all[split]=features(log.local_y[:,:,1],log.own[:,:,1],
                                        log.aligned[:,:,incoming],model.H[1])
        for w,times in windows.items():
            for aug in (False,True):
                key=w+("_cache" if aug else "_local")
                J=channels.feature_sensitivity(S,Sa,model,times,aug)
                tr=features_all["train"][int(aug)][:,times].reshape(len(TRAIN),-1)
                ca=features_all["calibration"][int(aug)][:,times].reshape(len(CAL),-1)
                mu,cov,prec=channels.fit_covariance(tr,.02)
                covtheta=np.linalg.inv(J.T@prec@J)
                gain=covtheta@J.T@prec
                values=(ca-mu)@gain.T
                scores=np.einsum("si,ij,sj->s",values,J.T@prec@J,values)
                threshold=float(np.quantile(scores,.95,method="higher"))
                fit[key]=(times,aug,J,mu,prec,gain,threshold)
        np.savez_compressed(out/"model_response_and_fits.npz",state_response=S,cache_response=Sa,
                            **{k+"_gain":v[5] for k,v in fit.items()},
                            **{k+"_mean":v[3] for k,v in fit.items()},
                            **{k+"_precision":v[4] for k,v in fit.items()})
        clean_sq=np.sum((c.estimates-x[:,:,None,:])**2,axis=-1)
        recovery=slice(D+1,261)
        propagation_summary={}
        cache_identity=[]
        for scenario in ("clean","single_step","replay_packet"):
            run,log=clean["test"] if scenario=="clean" else reference(model,x,y,seeds,sch,scenario)
            if scenario!="clean":
                attack_refs[scenario]=(run,log)
                assert np.all(run.injected.sum(axis=1)==1) and np.all(run.injected[:,R])
                max_x=max_raw=max_aligned=0.
                before=after=0.
                for s,seed in enumerate(seeds):
                    src=int(run.replay_source[s,R])
                    delta=np.asarray(model.cfg["attack"]["bias"]) if src<0 else c.estimates[s,src,0]-c.estimates[s,R,0]
                    if src>=0: assert src<R and sch[s,src,0] and src==136
                    # No run/log reference is passed to the predictor.
                    ds,dc,da,clock=difference(model,base_sch,delta,edge)
                    ref_x=run.estimates[s]-c.estimates[s]
                    ref_raw=log.raw[s]-clog.raw[s]
                    ref_al=log.aligned[s]-clog.aligned[s]
                    assert np.array_equal(clock,log.clocks[s])
                    assert np.max(np.abs(ref_x[:R+1]))==0
                    dx=np.abs(ds-ref_x); dr=np.abs(dc-ref_raw); dl=np.abs(da-ref_al)
                    max_x=max(max_x,float(dx.max())); max_raw=max(max_raw,float(dr.max()))
                    max_aligned=max(max_aligned,float(dl.max()))
                    before=max(before,float(dx[R+1:Q+1].max())); after=max(after,float(dx[Q+1:].max()))
                    assert max(dx.max(),dr.max(),dl.max())<atol
                    assert np.max(np.abs(ref_x[R+1,1]-model.cfg["epsilon"]*model.A@delta))<atol
                    for t in range(R,T):
                        for i in range(N):
                            for j in range(n):
                                node_rows.append({"scenario":scenario,"seed":int(seed),"iteration":t,
                                    "state_index":t+1,"node":i,"component":j,"predicted":ds[t+1,i,j],
                                    "reference_offline":ref_x[t+1,i,j],"abs_error":dx[t+1,i,j]})
                        for e,(j,i) in enumerate(model.edges):
                            for z in range(n):
                                cache_rows.append({"scenario":scenario,"seed":int(seed),"iteration":t,
                                    "edge":e,"component":z,"received":bool(sch[s,t,j]),"last_receive":int(clock[t,e]),
                                    "age":int(t-clock[t,e]),"predicted_raw":dc[t,e,z],"reference_raw":ref_raw[t,e,z],
                                    "raw_error":dr[t,e,z],"predicted_aligned":da[t,e,z],
                                    "reference_aligned":ref_al[t,e,z],"aligned_error":dl[t,e,z]})
                        if sch[s,t,0]:
                            send_rows.append({"scenario":scenario,"seed":int(seed),"time":t,
                                "replaced":t==R,"source_time":src if t==R else t,
                                "indirect_sender_norm":float(np.linalg.norm(ds[t,0])),
                                "reference_sender_norm":float(np.linalg.norm(ref_x[t,0])),
                                "sender_error":float(dx[t,0].max())})
                propagation_summary[scenario]={"state_max":max_x,"raw_max":max_raw,"aligned_max":max_aligned,
                    "before_q_state_max":before,"at_after_q_state_max":after}
            # Check all cache clocks/updates using only logged reception values.
            own=log.own[:,:,1]; ly=log.local_y[:,:,1]; rec=log.aligned[:,:,incoming]
            fi,fa=features(ly,own,rec,model.H[1])
            residue=ly-np.einsum("ab,stb->sta",model.H[1],own)
            assert np.max(np.abs(fi-residue))==0
            for t in range(1,T):
                for e,j in enumerate(model.edges[:,0]):
                    held=~sch[:,t,j]
                    if np.any(held):
                        assert np.max(np.abs(log.raw[held,t,e]-log.raw[held,t-1,e]))==0
                        assert np.max(np.abs(log.aligned[held,t,e]-log.aligned[held,t-1,e]@model.A.T))<atol
            cache_identity.append({"scenario":scenario,"seeds":len(seeds),"held_payload_and_age_prediction":"PASS"})
            # Future/other-node observations cannot enter already computed features.
            fy=ly.copy(); fo=own.copy(); fc=rec.copy()
            fy[:,D+1:]=np.nan; fo[:,D+1:]=np.nan; fc[:,D+1:]=np.nan
            ta,tb=features(fy,fo,fc,model.H[1])
            assert np.array_equal(ta[:,:D+1],fi[:,:D+1])
            assert np.array_equal(tb[:,:D+1],fa[:,:D+1])
            for key,(times,aug,J,mu,prec,gain,threshold) in fit.items():
                begin=time.perf_counter()
                v=(fa if aug else fi)[:,times].reshape(len(seeds),-1)-mu
                theta=v@gain.T
                score=np.einsum("si,ij,sj->s",theta,J.T@prec@J,theta)
                flagged=score>threshold
                correction=np.einsum("tncp,sp->stnc",S[D+1:261],theta*flagged[:,None])
                output=run.estimates[:,recovery]-correction
                sq=np.sum((output-x[:,recovery,None,:])**2,axis=-1)
                raw_sq=np.sum((run.estimates[:,recovery]-x[:,recovery,None,:])**2,axis=-1)
                elapsed=time.perf_counter()-begin
                for s,seed in enumerate(seeds):
                    row={"scenario":scenario,"method":key,"seed":int(seed),"flag":bool(flagged[s]),
                        "score":float(score[s]),"threshold":threshold,
                        "receiver_before":float(raw_sq[s,:,1].mean()),"receiver_after":float(sq[s,:,1].mean()),
                        "receiver_excess":float((sq[s,:,1]-clean_sq[s,recovery,1]).mean()),
                        "network_before":float(raw_sq[s].mean()),"network_after":float(sq[s].mean()),
                        "network_excess":float((sq[s]-clean_sq[s,recovery]).mean()),
                        "output_only":True,"new_detector_bytes":0,"batch_compute_seconds":elapsed}
                    metrics.append(row)
                summaries.append({"scenario":scenario,"method":key,"alarm_rate":float(flagged.mean()),
                    "receiver_mse":float(sq[:,:,1].mean()),"network_mse":float(sq.mean()),
                    "receiver_excess":float((sq[:,:,1]-clean_sq[:,recovery,1]).mean()),
                    "network_excess":float((sq-clean_sq[:,recovery]).mean()),
                    "receiver_change_vs_uncorrected":ci((sq[:,:,1]-raw_sq[:,:,1]).mean(axis=1)),
                    "batch_compute_seconds":elapsed,"feature_history_bytes_per_seed":v.shape[1]*8,
                    "fit_numeric_table_bytes":int(mu.nbytes+prec.nbytes+gain.nbytes+J.nbytes)})
        comparisons=[]
        idx={(m["scenario"],m["method"],m["seed"]):m for m in metrics}
        for scn in ("clean","single_step","replay_packet"):
            for w in windows:
                comparisons.append({"scenario":scn,"window":w,"comparison":"cache minus local",
                    "receiver_mse_change":ci([idx[scn,w+"_cache",int(s)]["receiver_after"]-idx[scn,w+"_local",int(s)]["receiver_after"] for s in seeds]),
                    "network_mse_change":ci([idx[scn,w+"_cache",int(s)]["network_after"]-idx[scn,w+"_local",int(s)]["network_after"] for s in seeds])})
        for f,rows in (("network_components.csv",node_rows),("cache_components.csv",cache_rows),
                       ("sender_transmissions.csv",send_rows),("per_seed_metrics.csv",metrics)):
            csv_out(out/f,rows)
        csv_out(out/"method_summary.csv",[{k:v for k,v in z.items() if not isinstance(v,dict)} for z in summaries])
        json_out(out/"comparisons.json",comparisons)
        broadcasts=int(sch[0].sum()); edge_packets=int(sch[0,:,model.edges[:,0]].sum())
        json_out(out/"summary.json",{"propagation":propagation_summary,"methods":summaries,
            "communications":{"node_broadcasts":broadcasts,"edge_packets":edge_packets,"payload_bytes":edge_packets*n*8,
                              "extra_feature_messages":0,"all_node_shadow_output":"offline evaluation only, not a broadcast protocol"},
            "normal_loss":"clean receiver_change_vs_uncorrected is false-correction MSE cost",
            "uncertainty":"paired seed, exploratory CI, conditional on fitted covariance, reused tests, no multiplicity correction",
            "runtime_seconds":time.perf_counter()-started})
        # Preserve every previously saved run and protected G2 file, including ignored artifacts.
        assert protected=={p:digest(ROOT/p) for p in PROTECTED}
        assert all(digest(BRANCH/p)==h for p,h in historical.items())
        json_out(out/"acceptance.json",{"status":"PASS","P0_1":propagation_summary,
            "tolerance":atol,"last_state_checked":T,"first_state_checked":R+1,"seed_count":48,
            "unit_response_checks":unit_checks,"receiver_cache_checks":cache_identity,
            "online_feature_signature":"local_y, own, received_aligned, H",
            "future_values_poisoned_without_prefix_effect":True,
            "feature_labels_and_unsent_neighbor_estimates_not_inputs":True,
            "logger_vs_vanilla":0.0,"shared_files_unchanged":protected,"old_result_file_count_preserved":len(historical),
            "state_component_rows":len(node_rows),"edge_component_rows":len(cache_rows)})
        print(json.dumps({"run":out.name,"propagation":propagation_summary,"unit_checks":unit_checks,
                          "summaries":summaries},ensure_ascii=True,indent=2))
    except Exception as exc:
        json_out(out/"failure.json",{"error":repr(exc),"stage":"P0 final rerun","no_pass_claim":True})
        raise


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--out",default=str(BRANCH/"results/g1r_p0_verified_20261113_v1"))
    main(p.parse_args().out)
