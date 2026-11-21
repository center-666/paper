"""Long-horizon scalar monitor/production-track recovery experiment."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import traceback

import numpy as np
from scipy.special import ndtr
import math

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
OUT=HERE/"results/run_v1"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write(p,obj):
    Path(p).parent.mkdir(parents=True,exist_ok=True)
    Path(p).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+"\n",
                         encoding="utf8",newline="\n")


def quant(m,d,s):
    return s+2*d*np.floor((m-s+d)/(2*d))


def nu_silence(P,m,phase,d,model):
    A,Q,R,Z=(model[k] for k in ("A","Q","R","Z"))
    S=A*A*P+Q+R
    V=1/Z+S
    # Current phase-specific silent probability, used only by the receiver.
    p_phase=1/np.sqrt(1+Z*S)*np.exp(-(A*m-phase-quant(A*m,d,phase))**2/(2*V))
    # Audit baseline intentionally averages the next independent phase and
    # therefore uses only the covariance label, not the sampled phase.
    f0=np.sqrt(2*np.pi*V)/(2*d)*(ndtr(d/np.sqrt(V))-ndtr(-d/np.sqrt(V)))
    nu=f0/np.sqrt(Z*V)
    return p_phase,nu


def one_case(model,b,attack_kind,protocol,n,seed):
    A,Q,R,Z=(model[k] for k in ("A","Q","R","Z"))
    d=model["delta"]
    # Score exactly N future events: t0+1,...,t0+N.
    T=protocol["attack_start"]+protocol["audit_horizon"]+1
    t0=protocol["attack_start"]
    alpha=protocol["target_false_alarm"]
    N=protocol["audit_horizon"]
    threshold=float(np.sqrt(N/2*np.log(1/alpha)))
    seq=np.random.SeedSequence(seed)
    ss_phys,ss_event,ss_phase,ss_attack=seq.spawn(4)
    rng_phys=np.random.default_rng(ss_phys)
    rng_event=np.random.default_rng(ss_event)
    rng_phase=np.random.default_rng(ss_phase)
    rng_attack=np.random.default_rng(ss_attack)
    x=np.sqrt(model["P0"])*rng_phys.normal(size=n)
    m_h=np.zeros(n); P_h=np.full(n,model["P0"])
    m_a=m_h.copy(); P_a=P_h.copy()
    phase=np.zeros(n)
    S_h=np.zeros(n); S_a=np.zeros(n)
    alarm_h=np.zeros(n,dtype=bool); alarm_a=np.zeros(n,dtype=bool)
    tau_h=np.full(n,-1,dtype=int); tau_a=np.full(n,-1,dtype=int)
    nu_prev_h=np.zeros(n); nu_prev_a=np.zeros(n)
    pending_h=np.zeros(n,dtype=bool); pending_a=np.zeros(n,dtype=bool)
    D_h=np.zeros(n); D_a=np.zeros(n)
    anchor=m_h.copy()  # episode-start trusted checkpoint, not attack-onset oracle
    anchor_h=m_h.copy()
    mse={k:np.zeros(n) for k in ["clean","monitor","hard","soft","oracle"]}
    audit_sum_a=np.zeros(n); audit_sum_h=np.zeros(n)
    predicted_drift_sum_a=np.zeros(n)
    sent_count=np.zeros(n,dtype=int)

    for t in range(T):
        if t==t0:
            attack_anchor=m_h.copy()  # diagnostic oracle only
        v=np.sqrt(R)*rng_phys.normal(size=n)
        w=np.sqrt(Q)*rng_phys.normal(size=n)
        y=x+v
        u=rng_event.random(n)
        c_h=quant(m_h,d,phase)
        c_a=quant(m_a,d,phase)
        p0_h=np.exp(-.5*Z*(y-c_h)**2)
        p0_a=np.exp(-.5*Z*(y-c_a)**2)
        send_h=u>p0_h
        send_a=u>p0_a

        # Audit the prior action with the event now observed. Score ignores
        # the current phase; its martingale property is pre-phase conditional.
        if t>t0 and pending_h.any():
            z=nu_prev_h-(~send_h).astype(float)
            S_h+=z
            audit_sum_h+=z
            new=(~alarm_h)&(S_h>=threshold)
            tau_h[new]=t-t0
            alarm_h|=new
        if t>t0 and pending_a.any():
            z=nu_prev_a-(~send_a).astype(float)
            S_a+=z
            audit_sum_a+=z
            new=(~alarm_a)&(S_a>=threshold)
            tau_a[new]=t-t0
            alarm_a|=new

        # The trusted checkpoint is pre-attack. Recovery monitor keeps running
        # for audit, while production uses the checkpoint after alarm.
        q=t-t0
        m_ck=anchor*(A**max(t,0)) if t>=t0 else m_h.copy()

        # Apply a causal payload attack only after the true event/measurement.
        action=np.zeros(n)
        if t>=t0:
            if attack_kind=="persistent_positive_send":
                action=np.where(send_a,b,0.0)
            elif attack_kind=="random_sign_send":
                action=np.where(send_a,b*np.where(rng_attack.random(n)<.5,-1.0,1.0),0.0)
            else:
                raise ValueError(attack_kind)
        y_a=y+action

        # Production output at this timestamp: before alarm, nominal monitor;
        # after alarm, an open-loop forecast from the authenticated checkpoint.
        # The current payload is excluded from production once the alarm fires.
        if t>=t0:
            mpost_h,Ppost_h,Kh=_update(m_h,P_h,c_h,y,send_h,A,Q,R,Z)
            mpost_a,Ppost_a,Ka=_update(m_a,P_a,c_a,y_a,send_a,A,Q,R,Z)
            safe=m_ck
            out_monitor=mpost_a
            out_hard=np.where(alarm_a,safe,mpost_a)
            out_soft=np.where(alarm_a,.5*safe+.5*mpost_a,mpost_a)
            out_oracle=attack_anchor*(A**max(q,0))
            mse["clean"]+=(x-mpost_h)**2
            mse["monitor"]+=(x-out_monitor)**2
            mse["hard"]+=(x-out_hard)**2
            mse["soft"]+=(x-out_soft)**2
            mse["oracle"]+=(x-out_oracle)**2
            # Healthy estimator's own false-alarm recovery cost, paired against
            # its no-recovery output on exactly the same path.
            safe_h=anchor_h*(A**max(t,0))
            hard_h=np.where(alarm_h,safe_h,mpost_h)
            soft_h=np.where(alarm_h,.5*safe_h+.5*mpost_h,mpost_h)
            mse.setdefault("healthy_hard",np.zeros(n))[:] += (x-hard_h)**2
            mse.setdefault("healthy_soft",np.zeros(n))[:] += (x-soft_h)**2
            sent_count+=send_a
        else:
            mpost_h,Ppost_h,Kh=_update(m_h,P_h,c_h,y,send_h,A,Q,R,Z)
            mpost_a,Ppost_a,Ka=_update(m_a,P_a,c_a,y_a,send_a,A,Q,R,Z)

        D_h=(1-Kh)*A*D_h-send_h*Kh*0.0
        D_a=(1-Ka)*A*D_a-send_a*Ka*action

        # Compute the phase-marginal healthy probability for the next event.
        # The next phase is drawn only after the current attack action commits.
        nu_prev_h=_nu(Ppost_h,model,d)
        nu_prev_a=_nu(Ppost_a,model,d)
        if t>=t0 and t<T-1:
            predicted_drift_sum_a+=nu_prev_a-_mean_silence(Ppost_a,D_a,model,d)
        pending_h[:]=True
        pending_a[:]=True
        if t<T-1:
            phase=d*(2*rng_phase.random(n)-1)
            x=A*x+w

    denom=protocol["audit_horizon"]+1
    rows={}
    for key in mse:
        rows[key]={"mse":float(np.mean(mse[key]/denom)),
                   "se":float(np.std(mse[key]/denom,ddof=1)/np.sqrt(n))}
    clean_mean=rows["clean"]["mse"]
    for key in ["monitor","hard","soft","oracle","healthy_hard","healthy_soft"]:
        rows[key]["paired_excess_vs_clean"]=float(np.mean((mse[key]-mse["clean"])/denom))
        rows[key]["paired_excess_se"]=float(np.std((mse[key]-mse["clean"])/denom,ddof=1)/np.sqrt(n))
    return {
        "model":model["id"],"attack_bound":b,"attack":attack_kind,
        "protocol":protocol["phase_protocol"],"n_episodes":n,"attack_start":t0,
        "audit_horizon":N,"threshold":threshold,
        "healthy_false_alarm_rate":float(np.mean(alarm_h)),
        "attack_alarm_rate":float(np.mean(alarm_a)),
        "attack_detection_delay_mean_conditional":float(np.mean(tau_a[tau_a>=0])) if np.any(tau_a>=0) else None,
        "attack_detection_delay_median_conditional":float(np.median(tau_a[tau_a>=0])) if np.any(tau_a>=0) else None,
        "average_audit_score_healthy":float(np.mean(audit_sum_h)),
        "average_audit_score_attack":float(np.mean(audit_sum_a)),
        "average_predicted_audit_drift_attack":float(np.mean(predicted_drift_sum_a)),
        "score_minus_predicted_drift_attack":float(np.mean(audit_sum_a-predicted_drift_sum_a)),
        "maximum_abs_analysis_bias":float(np.max(np.abs(D_a))),
        "mean_target_attack_sends_per_episode":float(np.mean(sent_count)),
        "mse_metrics":rows,
        "checkpoint_assumption":"episode-start authenticated snapshot; hard/soft recovery uses this potentially stale anchor",
        "feedback_source":"provisional monitor drives event trigger; production output does not feed back to sensor",
        "recovery":"hard rollback=open-loop checkpoint after first alarm; soft=50/50 monitor-checkpoint after first alarm; monitor continues only for audit",
        "warning":"oracle reference assumes attack-onset knowledge; implementable rollback uses only episode-start authenticated checkpoint; no post-attack packet is called authenticated",
    }


def _nu(P,model,d):
    A,Q,R,Z=(model[k] for k in ("A","Q","R","Z"))
    V=1/Z+A*A*P+Q+R
    return _phase_nu(V,d,Z)


def _mean_silence(P,D,model,d):
    A,Q,R,Z=(model[k] for k in ("A","Q","R","Z"))
    V=1/Z+A*A*P+Q+R
    return (1/np.sqrt(Z*V))*np.sqrt(2*np.pi*V)/(2*d)*(
        ndtr((d-A*D)/np.sqrt(V))-ndtr((-d-A*D)/np.sqrt(V)))


def _phase_nu(V,d,Z):
    # Accurate enough for score simulation; phase integral is subsequently
    # checked against Gauss quadrature in deterministic tests.
    from scipy.special import ndtr
    return (1/np.sqrt(Z*V))*np.sqrt(2*np.pi*V)/(2*d)*(ndtr(d/np.sqrt(V))-ndtr(-d/np.sqrt(V)))


def _update(m,P,c,y,sent,A,Q,R,Z):
    R0=R+1/Z
    Ri=np.where(sent,R,R0)
    K=P/(P+Ri)
    mpost=np.where(sent,m+K*(y-m),m+K*(c-m))
    Ppost=P*(1-K)
    m[:]=A*mpost
    P[:]=A*A*Ppost+Q
    return mpost,Ppost,K


def preflight():
    protocol=json.loads((HERE/"protocol.json").read_text(encoding="utf8"))
    checks=[]
    def check(name,ok,detail=None):
        checks.append({"name":name,"pass":bool(ok),"detail":detail})
        if not ok: raise AssertionError(name)
    alpha=protocol["target_false_alarm"]
    N=protocol["audit_horizon"]
    h=np.sqrt(N/2*np.log(1/alpha))
    check("finite_horizon_false_alarm_bound",math.exp(-2*h*h/N)<=alpha*(1+1e-12),float(math.exp(-2*h*h/N)))
    model=protocol["models"][0]
    V=1/model["Z"]+model["A"]**2*model["P0"]*model["R"]/(model["P0"]+model["R"])+model["Q"]+model["R"]
    for d in [-.2,-.05,0,.05,.2]:
        phase=np.linspace(-model["delta"],model["delta"],200001,endpoint=False)
        f=np.mean(np.exp(-(d-phase)**2/(2*V)))
        check("phase_average_center_maximum_"+str(d),f<=np.mean(np.exp(-phase**2/(2*V)))+1e-12)
    P=np.array([model["P0"]]);m=np.array([0.]);y=np.array([.2]);sent=np.array([True]);center=np.array([0.])
    mpost,Ppost,K=_update(m,P,center,y,sent,model["A"],model["Q"],model["R"],model["Z"])
    check("kalman_covariance_positive",bool(Ppost[0]>0),float(Ppost[0]))
    check("gain_in_unit_interval",bool(0<K[0]<1),float(K[0]))
    result={"status":"PASS","checks":checks,"horizon":N,"alpha":alpha,
            "audit_threshold":float(h),"random_samples_generated":False}
    write(HERE/"preflight.json",result)
    return result


def freeze():
    path=HERE/"freeze.json"
    if path.exists(): raise SystemExit("Recovery trial already frozen; refusing overwrite.")
    preflight()
    tracked=subprocess.check_output(["git","ls-files","-co","--exclude-standard","-z"],cwd=REPO).decode("utf8").split("\0")
    protected={p:sha(REPO/p) for p in tracked if p and (REPO/p).is_file()
        and not p.startswith(HERE.relative_to(REPO).as_posix()+"/")}
    write(HERE/"protected_before.json",protected)
    result={"stage":"FROZEN_BEFORE_RECOVERY_TRIAL_INPUTS",
        "base_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=REPO,text=True).strip(),
        "protocol_sha256":sha(HERE/"protocol.json"),
        "recovery_trial_code_sha256":sha(Path(__file__)),
        "python":sys.version,"numpy":np.__version__,"platform":platform.platform(),
        "preflight_sha256":sha(HERE/"preflight.json"),"protected_file_count":len(protected),
        "episodes":json.loads((HERE/"protocol.json").read_text(encoding="utf8"))["episodes"],
        "random_samples_generated":False}
    write(path,result)
    print(json.dumps(result,indent=2))


def main():
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("command",choices=["preflight","freeze","run"])
    args=parser.parse_args()
    if args.command=="preflight":
        print(json.dumps(preflight(),indent=2));return
    if args.command=="freeze":
        freeze();return
    protocol=json.loads((HERE/"protocol.json").read_text(encoding="utf8"))
    frozen=json.loads((HERE/"freeze.json").read_text(encoding="utf8"))
    codehash=sha(Path(__file__))
    if codehash!=frozen["recovery_trial_code_sha256"]:
        raise SystemExit("Recovery trial code differs from pre-sampling freeze")
    if sha(HERE/"protocol.json")!=frozen["protocol_sha256"]:
        raise SystemExit("Recovery trial protocol differs from pre-sampling freeze")
    if OUT.exists(): raise SystemExit("Trial output exists; refusing overwrite")
    OUT.mkdir(parents=True)
    n=protocol["episodes"]
    results=[]
    for i,model in enumerate(protocol["models"]):
        for b in protocol["attack_bounds"]:
            for attack in protocol["attack_policies"]:
                # Use separate, predeclared streams per model/severity/policy.
                seed=protocol["master_seed"]+10000*i+int(b*10000)+(1 if attack.startswith("random") else 0)
                rows=one_case(model,b,attack,protocol,n,seed)
                results.append(rows)
                print(model["id"],b,attack,"done",flush=True)
    write(OUT/"summary.json",results)
    protected=json.loads((HERE/"protected_before.json").read_text(encoding="utf8"))
    changed=[p for p,digest in protected.items() if sha(REPO/p)!=digest]
    write(OUT/"protected_file_check.json",{"checked":len(protected),"changed":changed,"pass":not changed})
    if changed:
        raise AssertionError("Pre-existing files changed during recovery trial: "+", ".join(changed[:10]))
    write(OUT/"manifest.json",{
        "protocol_sha256":sha(HERE/"protocol.json"),"script_sha256":codehash,
        "summary_sha256":sha(OUT/"summary.json"),"episodes_per_case":n,
        "random_simulation_run":True,"model_runs":len(results),
        "fixed_test_parameters":True,"source_manuscript_modified":False})


if __name__=="__main__":
    main()
