"""Stage 3 simulation; physics truth is confined to this offline driver."""
from __future__ import annotations

import json
import hashlib
from pathlib import Path
import time
import numpy as np
from core import JointDetectors,NAMES,quant,update_error,log_factors

HERE=Path(__file__).resolve().parent
METHODS=(*NAMES,"oracle_joint")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write(p,data):
    p=Path(p)
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False)+"\n",
                 encoding="utf8",newline="\n")


class Moments:
    def __init__(self):
        self.data={}
    def add(self,name,x):
        x=np.asarray(x,dtype=float).reshape(-1)
        if not np.all(np.isfinite(x)):
            raise FloatingPointError("Nonfinite metric: "+name)
        entry=self.data.setdefault(name,[0,0.,0.])
        entry[0]+=len(x)
        entry[1]+=float(x.sum())
        entry[2]+=float(x@x)
    def report(self):
        out={}
        for name,(n,total,sq) in self.data.items():
            if n==0:
                out[name]={"n":0,"mean":None,"se":None,"sum":0.,"sum_squares":0.}
            else:
                v=max(0.,(sq-total*total/n)/(n-1)) if n>1 else 0.
                out[name]={"n":n,"mean":total/n,"se":float(np.sqrt(v/n)),
                           "sum":total,"sum_squares":sq}
        return out


def detector(count,model,p):
    return JointDetectors(count,model,p["candidate_strengths"],p["candidate_weights"],p["alpha"])


def batch(model,b,onset_kind,count,seed,p,summaries):
    A,Q,R,Z,delta=(model[k] for k in ("A","Q","R","Z","delta"))
    phys,event,phase_rng,schedule=[
        np.random.default_rng(s) for s in np.random.SeedSequence(seed).spawn(4)]
    onset=(schedule.integers(50,201,size=count) if isinstance(onset_kind,str)
           else np.full(count,onset_kind,dtype=int))
    end=int(onset.max())+max(p["horizons_after_onset"])
    eh=np.sqrt(model["P0"])*phys.normal(size=count)
    ea=eh.copy()
    Ph=np.full(count,model["P0"]); Pa=Ph.copy()
    D=np.zeros(count)
    attacked=detector(count,model,p)
    healthy=detector(count,model,p)
    oracle_tau=np.full(count,-1,dtype=np.int32)
    oracle_ll=np.zeros(count)
    oracle_event_ll=np.zeros(count)
    oracle_payload_ll=np.zeros(count)
    total_mse=np.zeros(count); clean_mse=np.zeros(count)
    bias_energy=np.zeros(count); sends=np.zeros(count)
    pre_mse=np.zeros((len(METHODS),count)); pre_bias=np.zeros_like(pre_mse)
    max_error=0.;max_bias=0.
    for t in range(end):
        v=np.sqrt(R)*phys.normal(size=count)
        w=np.sqrt(Q)*phys.normal(size=count)
        phase=delta*(2*phase_rng.random(count)-1) if t else np.zeros(count)
        rh=quant(0.,delta,phase)
        displacement=eh-ea
        ra=quant(displacement,delta,phase)-displacement
        U=event.random(count)
        sh=U>np.exp(-.5*Z*(eh+v-rh)**2)
        sa=U>np.exp(-.5*Z*(ea+v-ra)**2)
        active=t>=onset
        action=np.where(active&sa,b,0.)
        # Only actual received innovations and trusted centers cross the online API.
        uh=np.where(sh,eh+v,0.)
        ua=np.where(sa,ea+v+action,0.)
        healthy.step(t,Ph,rh,sh,uh)
        attacked.step(t,Pa,ra,sa,ua)
        oracle=log_factors(Pa,ra,sa,ua,A*D,np.where(active,b,0.),model)
        oracle_ll+=np.where(active,oracle[-1],0.)
        oracle_event_ll+=np.where(active,oracle[0],0.)
        oracle_payload_ll+=np.where(active,oracle[3],0.)
        new=(oracle_tau<0)&active&(oracle_ll>=np.log(1/p["alpha"]))
        oracle_tau[new]=t
        tau=np.vstack((attacked.tau,oracle_tau))
        eph,Pph,Kh=update_error(eh,Ph,rh,v,sh,0.,model)
        epa,Ppa,Ka=update_error(ea,Pa,ra,v,sa,action,model)
        D=(1-Ka)*A*D-Ka*action
        total_mse+=active*epa**2
        clean_mse+=active*eph**2
        bias_energy+=active*D**2
        sends+=active&sa
        live=(tau<0)&active[None,:]
        pre_mse+=live*epa[None,:]**2
        pre_bias+=live*D[None,:]**2
        for H in p["horizons_after_onset"]:
            selected=t==onset+H-1
            if not np.any(selected):
                continue
            s=summaries[H]
            for name,value in (("monitor_MSE",total_mse),("healthy_MSE",clean_mse),
                               ("MSE_excess",total_mse-clean_mse),("bias_energy",bias_energy),
                               ("sends",sends),("oracle_joint_log_LR",oracle_ll),
                               ("oracle_phase_event_log_LR",oracle_event_ll),
                               ("oracle_conditional_payload_log_LR",oracle_payload_ll)):
                s.add(name,value[selected])
            t0=onset[selected]
            survivors=[]
            detected_all=[]
            delays=[]
            for i,name in enumerate(METHODS):
                tt=tau[i,selected]
                # E0/E1 see only the event at t0, which precedes attack submission.
                cutoff=t0 if i in (0,1) else t0-1
                early=(tt>=0)&(tt<=cutoff)
                eligible=~early
                found=(tt>cutoff)&(tt<=t)
                delay=np.where(found,tt-t0+1,H)
                survivors.append(eligible);detected_all.append(found);delays.append(delay)
                s.add(name+"/pre_attack_alarm",early)
                s.add(name+"/detection_unconditional",found)
                s.add(name+"/detection_eligible",found[eligible])
                s.add(name+"/restricted_delay_eligible",delay[eligible])
                s.add(name+"/delay_detected",delay[found])
                s.add(name+"/pre_MSE_unconditional",pre_mse[i,selected])
                s.add(name+"/pre_MSE_eligible",pre_mse[i,selected][eligible])
                s.add(name+"/pre_bias_eligible",pre_bias[i,selected][eligible])
                if i<len(NAMES):
                    s.add(name+"/healthy_alarm_by_endpoint",healthy.tau[i,selected]>=0)
            joint_index=NAMES.index("J1_joint_mixture")
            for baseline in ("R0_selected_innovation_mixture","R1_biasaware_innovation_mixture",
                             "P1_conditional_payload_mixture","E0_previous_event_mixture"):
                j=NAMES.index(baseline)
                common=survivors[j]&survivors[joint_index]
                for metric,val in (
                    ("detection",detected_all[joint_index].astype(float)-detected_all[j]),
                    ("delay",delays[joint_index]-delays[j]),
                    ("pre_MSE",pre_mse[joint_index,selected]-pre_mse[j,selected])):
                    s.add("J1_minus_"+baseline+"/"+metric+"_common_eligible",val[common])
        healthy.advance(Pph,Kh,sh)
        attacked.advance(Ppa,Ka,sa)
        eh,ea=A*eph+w,A*epa+w
        Ph,Pa=A*A*Pph+Q,A*A*Ppa+Q
        max_error=max(max_error,float(np.max(np.abs(ea))))
        max_bias=max(max_bias,float(np.max(np.abs(D))))
    return {"max_prior_error":max_error,"max_bias":max_bias,
            "oracle_chain_identity_max_error":float(np.max(np.abs(
                oracle_ll-oracle_event_ll-oracle_payload_ll)))}


def health_batch(model,count,seed,p,summaries):
    A,Q,R,Z,delta=(model[k] for k in ("A","Q","R","Z","delta"))
    phys,event,phase_rng=[np.random.default_rng(s) for s in np.random.SeedSequence(seed).spawn(3)]
    e=np.sqrt(model["P0"])*phys.normal(size=count)
    P=np.full(count,model["P0"])
    detectors=detector(count,model,p)
    for t in range(p["health_horizon"]):
        v=np.sqrt(R)*phys.normal(size=count)
        w=np.sqrt(Q)*phys.normal(size=count)
        phase=delta*(2*phase_rng.random(count)-1) if t else np.zeros(count)
        r=quant(0.,delta,phase)
        sent=event.random(count)>np.exp(-.5*Z*(e+v-r)**2)
        detectors.step(t,P,r,sent,np.where(sent,e+v,0.))
        if t+1 in summaries:
            for i,name in enumerate(NAMES):
                summaries[t+1].add(name+"/healthy_alarm",detectors.tau[i]>=0)
        ep,Pp,K=update_error(e,P,r,v,sent,0.,model)
        detectors.advance(Pp,K,sent)
        e,P=A*ep+w,A*A*Pp+Q


def check_frozen():
    frozen=json.loads((HERE/"freeze.json").read_text(encoding="utf8"))
    for name,digest in frozen["input_hashes"].items():
        if sha(HERE/name)!=digest:
            raise RuntimeError("Frozen source changed: "+name)


def run_job(job):
    stage,mi,bi,oi=job
    check_frozen()
    p=json.loads((HERE/"protocol.json").read_text(encoding="utf8"))
    model=p["models"][mi]
    if stage.startswith("health"):
        path=HERE/"results"/stage/(model["id"]+".json")
        n=p[stage+"_episodes"]
        moments={h:Moments() for h in (512,2048,8192)}
        seedkey=stage+"_seed"
    else:
        offgrid=stage=="offgrid"
        b=p["offgrid_strengths" if offgrid else "attack_strengths"][bi]
        onset=p["offgrid_onset"] if offgrid else p["onsets"][oi]
        path=HERE/"results"/stage/f"{model['id']}_b{b:g}_onset{onset}.json"
        n=p[stage+"_episodes"]
        moments={h:Moments() for h in p["horizons_after_onset"]}
        seedkey=stage+"_seed"
    if path.exists():
        raise RuntimeError("Output exists: "+str(path))
    started=time.perf_counter()
    checks=[]
    for batch_index,start in enumerate(range(0,n,p["batch_size"])):
        count=min(n-start,p["batch_size"])
        seed=[p[seedkey],mi,bi,oi,batch_index]
        if stage.startswith("health"):
            health_batch(model,count,seed,p,moments)
        else:
            checks.append(batch(model,b,onset,count,seed,p,moments))
    result={"stage":stage,"model":model,"n":n,
            "statistics":{str(h):v.report() for h,v in moments.items()},
            "frozen_hash":sha(HERE/"freeze.json"),"runtime_checks":checks,
            "seconds":time.perf_counter()-started,"recovery_actions":False}
    if not stage.startswith("health"):
        result.update({"strength":b,"onset":onset})
    write(path,result)
    return str(path.relative_to(HERE)),result["seconds"]
