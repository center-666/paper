"""Equation mapping check, not a Deghat detector or a performance benchmark."""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np
from p0_verified import BRANCH, ROOT, difference, reference, json_out, csv_out, digest, PROTECTED
from minimal_recovery_screen import build_model, common_schedule, TEST, R
from model import generate_data


def step(e, bminus, a, fresh, model, t, w, v):
    bplus=bminus.copy()
    for edge,(j,i) in enumerate(model.edges):
        if fresh[j]: bplus[edge]=e[j]-a[edge]
    innovation=np.einsum("imn,in->im",model.H,e)+v
    disagreement=np.zeros_like(e)
    for edge,(j,i) in enumerate(model.edges):
        disagreement[i]+=e[i]-bplus[edge]
    enext=np.einsum("ab,nb->na",model.A,e)
    enext-=np.einsum("iab,ib->ia",model.gains[t],innovation)
    enext-=model.cfg["epsilon"]*np.einsum("ab,nb->na",model.A,disagreement)
    enext+=w[None]
    bnext=bplus@model.A.T+w[None]
    return enext,bnext,innovation,disagreement


def main():
    out=BRANCH/"results/g1r_p1_structure_20261113_v1"
    assert json.loads((BRANCH/"results/g1r_p0_verified_20261113_v1/acceptance.json").read_text())["status"]=="PASS"
    out.mkdir(exist_ok=False)
    model=build_model(); m=model.cfg
    before={p:digest(ROOT/p) for p in PROTECTED}
    json_out(out/"config.json",{"scope":"exact discrete error/output mapping, no designed detector",
        "model":m,"seeds":TEST,"tolerance":1e-10,"P0_completed_first":True})
    x,y=generate_data(model,TEST); schedule=common_schedule(model,len(TEST))
    rows=[]
    for scn in ("clean","single_step","replay_packet"):
        run,log=reference(model,x,y,TEST,schedule,scn)
        for s,seed in enumerate(TEST):
            e=np.broadcast_to(x[s,0],(m["N"],m["n"])).copy()
            b=np.broadcast_to(x[s,0],(len(model.edges),m["n"])).copy()
            state_err=output_err=cache_err=instant_mismatch=0.
            for t in range(m["T"]):
                w=x[s,t+1]-model.A@x[s,t]
                v=y[s,t]-np.einsum("iab,b->ia",model.H,x[s,t])
                a=np.zeros_like(b)
                if t==R and scn!="clean":
                    edge=0
                    a[edge]=log.raw[s,t,edge]-run.estimates[s,t,0]
                en,bn,inn,dis=step(e,b,a,schedule[s,t],model,t,w,v)
                actual_dis=np.zeros_like(e); instant_dis=np.zeros_like(e)
                for edge,(j,i) in enumerate(model.edges):
                    actual_dis[i]+=log.aligned[s,t,edge]-run.estimates[s,t,i]
                    instant_dis[i]+=run.estimates[s,t,j]-run.estimates[s,t,i]
                actual_inn=y[s,t]-np.einsum("iab,ib->ia",model.H,run.estimates[s,t])
                state_err=max(state_err,float(np.max(np.abs(en-(x[s,t+1]-run.estimates[s,t+1])))))
                cache_err=max(cache_err,float(np.max(np.abs(bn-(x[s,t+1]-log.aligned[s,t]@model.A.T)))))
                output_err=max(output_err,float(np.max(np.abs(inn-actual_inn))),float(np.max(np.abs(dis-actual_dis))))
                if t>=50: instant_mismatch=max(instant_mismatch,float(np.max(np.abs(instant_dis-actual_dis))))
                e,b=en,bn
            assert max(state_err,cache_err,output_err)<1e-10
            rows.append({"scenario":scn,"seed":int(seed),"error_state_recursion_max":state_err,
                "predicted_cache_error_max":cache_err,"output_equation_max":output_err,
                "instantaneous_neighbor_output_mismatch_max_offline":instant_mismatch})
    csv_out(out/"per_seed_mapping.csv",rows)
    summary={}
    for scn in ("clean","single_step","replay_packet"):
        rs=[r for r in rows if r["scenario"]==scn]
        summary[scn]={k:max(r[k] for r in rs) for k in rows[0] if k not in {"scenario","seed"}}
    # Input feedthrough to cache-based disagreement: an on-link replacement
    # changes the detector output at the same iteration.
    zero_e=np.zeros((m["N"],m["n"])); zero_b=np.zeros((len(model.edges),m["n"]))
    aa=zero_b.copy(); aa[0]=[1,0]
    _,_,_,dis=step(zero_e,zero_b,aa,schedule[0,R],model,R,np.zeros(m["n"]),zero_e)
    assert np.array_equal(dis[1],aa[0])
    assert before=={p:digest(ROOT/p) for p in PROTECTED}
    json_out(out/"summary.json",{"PASS_exact_error_mapping":True,"maxima":summary,
        "error_and_pre_receive_cache_state_dimension":(m["N"]+len(model.edges))*m["n"],
        "direct_feedthrough_on_received_disagreement_at_r":dis[1],
        "expected_noise_energy_per_step":float(np.trace(model.Q)+sum(np.trace(r) for r in model.R)),
        "extra_error_estimate_payload_bytes_same_schedule":int(schedule[0,:,model.edges[:,0]].sum())*m["n"]*8,
        "detector_performance_tested":False,"continuous_LMI_transferred":False,
        "protected_unchanged":before})
    json_out(out/"source_hashes.json",{str(p.relative_to(ROOT)):digest(p) for p in
             [Path(__file__),BRANCH/"code/p0_verified.py",ROOT/"simulation/engine.py",ROOT/"simulation/model.py"]})
    print(json.dumps(summary,indent=2))


if __name__=="__main__": main()
