"""Frozen E1 only. Writes a new run; refuses overwrite. No shared engine edits."""
from pathlib import Path
import argparse
import hashlib
import json
import platform
import subprocess
import sys
import traceback
from datetime import datetime, timezone

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
CODE = Path(__file__).resolve().parent
PROTOCOL = ROOT / "reviews/paper1_integration_and_minimal_experiments/experiment_protocol.json"
ATOL, RTOL = 1e-10, 1e-8
BRANCHES = ["healthy", "plus", "minus"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False)+"\n",
                          encoding="utf-8")


def quantize(value, delta):
    value = np.asarray(value, dtype=float)
    if delta == 0:
        return np.zeros(value.shape, dtype=np.int64), value.copy()
    index = np.floor((value+delta)/(2*delta)).astype(np.int64)
    return index, (2*delta)*index


def witness(t, sent, disclosed_y, prior, covariance, A, R, delta, eta, target):
    """Policy has only current disclosed sends, own prior/model, public doses.

    No state, future measurement/uniform, other protocol or healthy reference.
    Independent +/- sign integration is applied by the caller after this gate.
    """
    eligible = np.zeros(sent.shape, dtype=bool)
    next_if_unmodified = np.full(sent.shape, np.nan)
    margin = np.full(sent.shape, np.nan)
    if t != target:
        return eligible, next_if_unmodified, margin
    ix = np.flatnonzero(sent)
    gain = covariance[ix]/(covariance[ix]+R)
    M = A*(prior[ix]+gain*(disclosed_y[ix]-prior[ix]))
    _, center = quantize(M, delta)
    next_if_unmodified[ix] = M
    margin[ix] = delta-np.abs(M-center)
    eligible[ix] = np.abs(M-center) < delta/2
    return eligible, next_if_unmodified, margin


def generate_inputs(model, protocol):
    n = protocol["coupling"]["base_samples_per_model"]
    T = protocol["history_end"]+1
    master = protocol["rng_plan"]["master_seed"]
    mid = protocol["rng_plan"]["model_id"][model["id"]]
    x = np.empty((n,T)); w = np.empty((n,T-1)); v = np.empty((n,T))
    uniforms = np.empty((n,T))
    for i in range(n):
        streams = [np.random.Generator(np.random.PCG64(
            np.random.SeedSequence([master,mid,i,j]))) for j in range(4)]
        x[i,0] = model["m0"]+np.sqrt(model["P0"])*streams[0].standard_normal()
        w[i] = np.sqrt(model["Q"])*streams[1].standard_normal(T-1)
        v[i] = np.sqrt(model["R"])*streams[2].standard_normal(T)
        uniforms[i] = streams[3].random(T)
        for t in range(T-1):
            x[i,t+1] = model["A"]*x[i,t]+w[i,t]
    return dict(x=x,y=x+v,w=w,v=v,U=uniforms,base_sample_id=np.arange(n,dtype=np.int64))


def simulate(model, y, uniforms, kind, delta, eta, target):
    """Vectorized [sample, branch, time], each branch uses only its own history."""
    n,T = y.shape; shape = (n,3,T)
    fields = ["m_prior","P_prior","m_post","P_post","feedback","qerror","gain",
              "payload","action","gate_M","gate_margin","rounded_log_feedback",
              "mu_prior","mu_post","trigger_send_probability",
              "history_send_probability"]
    tr = {f:np.full(shape,np.nan,dtype=np.float64) for f in fields}
    tr.update({f:np.zeros(shape,dtype=bool) for f in ("sent","eligible")})
    tr.update({f:np.zeros(shape,dtype=np.int64)
               for f in ("feedback_index","rounded_log_index")})
    m = np.full((n,3),model["m0"],dtype=float)
    mu=m.copy(); P=np.full_like(m,model["P0"])
    A,Q,R,Z = (model[k] for k in ("A","Q","R","Z"))
    signs=np.array([0.,1.,-1.])[None,:]
    for t in range(T):
        tr["m_prior"][:,:,t]=m
        tr["mu_prior"][:,:,t]=mu
        tr["P_prior"][:,:,t]=P
        idx,rounded = quantize(m,delta)
        center=rounded if kind=="B" else m.copy()
        tr["rounded_log_index"][:,:,t]=idx
        tr["rounded_log_feedback"][:,:,t]=rounded
        tr["feedback_index"][:,:,t]=idx if kind=="B" else 0
        tr["feedback"][:,:,t]=center
        tr["qerror"][:,:,t]=center-m
        measurement=y[:,t,None]
        # First generate event using real measurement and actual feedback center.
        p_silent=np.exp(-.5*Z*(measurement-center)**2)
        sent=uniforms[:,t,None] > p_silent
        tr["sent"][:,:,t]=sent
        tr["trigger_send_probability"][:,:,t]=1-p_silent
        tr["history_send_probability"][:,:,t] = (
            1-np.exp(-.5*(mu-center)**2/(P+R+1/Z))/np.sqrt(1+Z*(P+R)))
        # Only now disclose a real packet; no action can create a transmission.
        disclosed=np.where(sent,measurement,np.nan)
        gates,M,margins=witness(t,sent.ravel(),disclosed.ravel(),m.ravel(),P.ravel(),
                                A,R,delta,eta,target)
        gates=gates.reshape(n,3)
        action=signs*eta*gates
        tr["eligible"][:,:,t]=gates
        tr["gate_M"][:,:,t]=M.reshape(n,3)
        tr["gate_margin"][:,:,t]=margins.reshape(n,3)
        tr["action"][:,:,t]=action
        payload=np.where(sent,measurement+action,np.nan)
        tr["payload"][:,:,t]=payload
        Ri=np.where(sent,R,R+1/Z)
        gain=P/(P+Ri)
        tr["gain"][:,:,t]=gain
        # Correctly use quantized center as virtual measurement on silence.
        mpost=np.where(sent,m+gain*(np.nan_to_num(payload)-m),m+gain*(center-m))
        mupost=np.where(sent,mu+gain*(measurement-mu),mu+gain*(center-mu))
        Ppost=P-P*gain
        tr["m_post"][:,:,t]=mpost;tr["mu_post"][:,:,t]=mupost
        tr["P_post"][:,:,t]=Ppost
        m=A*mpost;mu=A*mupost;P=A*A*Ppost+Q
    return tr


class Checks:
    def __init__(self):
        self.rows=[];self.failures={}

    def test(self,name,mask,detail=None):
        mask=np.asarray(mask,dtype=bool)
        failures=np.argwhere(~mask)
        row=dict(name=name,n_checked=int(mask.size),n_failed=int(len(failures)),
                 passed=not len(failures))
        if detail is not None:row["detail"]=detail
        if len(failures):
            self.failures[name]=failures
            row["first_failures"]=failures[:20].tolist()
        self.rows.append(row)

    def close(self,name,x,y,atol=ATOL,rtol=RTOL):
        x,y=np.broadcast_arrays(x,y)
        diff=np.abs(x-y)
        self.test(name,np.isclose(x,y,atol=atol,rtol=rtol),
                  dict(max_absolute_error=float(np.max(diff)),
                       absolute_tolerance=atol,relative_tolerance=rtol))

    @property
    def passed(self):
        return all(r["passed"] for r in self.rows)


def preflight(protocol):
    ck=Checks()
    idx,val=quantize(np.array([-.75,-.25,.25,.75]),.25)
    ck.test("half_open_quantizer_ties",idx==np.array([-1,0,1,2]))
    for model in protocol["models"]:
        name=model["id"];A,R,Z=(model[z] for z in ("A","R","Z"))
        P=model["P0"]
        # Deterministic target=0 interface: a real send plus a silent sample.
        y=np.array([[.7,-.2],[.0,.1]])
        u=np.array([[.999,.5],[0.,.5]])
        z=simulate(model,y,u,"A",0.,0.,0)
        zq=simulate(model,y,u,"B",0.,0.,0)
        ck.close(name+"_zero_delta_exact_update",z["m_post"],zq["m_post"],0,0)
        ck.test(name+"_zero_delta_exact_events",z["sent"]==zq["sent"])
        # Nonzero c-m tests Gaussian silent posterior, not only zero initialization.
        prior=.19; _,c=quantize(np.array([prior]),.125);R0=R+1/Z
        gain=P/(P+R0)
        numeric=prior+gain*(c[0]-prior)
        precision_mean=(prior/P+c[0]/R0)/(1/P+1/R0)
        ck.close(name+"_nonzero_silent_center",numeric,precision_mean)
        ck.test(name+"_old_silent_rule_differs",abs(numeric-prior)>1e-3)
        for t in (1,5):
            gate,_,_=witness(t,np.array([False]),np.array([np.nan]),
                            np.array([0.]),np.array([P]),A,R,.01,.005,4)
            ck.test(name+"_no_disclosed_measurement_"+str(t),~gate)
    return ck


def verify_case(tr, inp, model, protocol, kind, delta, eta):
    ck=Checks();A,R,Z=(model[z] for z in ("A","R","Z"));k=model["k"]
    sent=tr["sent"];n,_,T=sent.shape
    expected=inp["U"][:,None,:] > np.exp(-.5*Z*(inp["y"][:,None,:]-tr["feedback"])**2)
    ck.test("event_uses_real_measurement_before_modification",sent==expected)
    ck.test("no_forged_packet",np.isfinite(tr["payload"])==sent)
    ck.test("no_action_without_send",sent | (tr["action"]==0))
    ck.test("action_only_at_target",tr["action"][:,:,np.arange(T)!=k]==0)
    ck.test("healthy_branch_no_action",tr["action"][:,0]==0)
    ck.test("peak_budget",np.abs(tr["action"])<=protocol["b"])
    ck.test("positive_covariance",tr["P_prior"]>0)
    ck.test("pretarget_coupling",tr["m_prior"][:,:,:k+1]==tr["m_prior"][:,0:1,:k+1])
    ck.test("target_event_coupling",sent[:,:,k]==sent[:,0:1,k])
    ck.close("healthy_bayes_mean_matches",tr["m_post"][:,0],tr["mu_post"][:,0])
    Ri=np.where(sent,R,R+1/Z)
    ck.close("posterior_covariance_precision_form",tr["P_post"],
             1/(1/tr["P_prior"]+1/Ri))
    expected_mu=tr["P_post"]*(tr["mu_prior"]/tr["P_prior"]+
                  np.where(sent,inp["y"][:,None,:],tr["feedback"])/Ri)
    ck.close("bayes_posterior_precision_form",tr["mu_post"],expected_mu)
    residual_q=tr["feedback"]-tr["m_prior"]
    if kind=="B":
        eps=8*np.finfo(float).eps*np.maximum(1,np.abs(tr["m_prior"]))
        ck.test("quantization_error_bound",np.abs(residual_q)<=delta+eps)
        ck.test("B_full_event_history_pathwise",sent==sent[:,0:1,:])
        ck.test("B_full_feedback_codes_pathwise",tr["feedback_index"]==tr["feedback_index"][:,0:1,:])
        ck.test("B_full_feedback_values_pathwise",tr["feedback"]==tr["feedback"][:,0:1,:])
        ck.test("B_target_covariance_pathwise",tr["P_post"][:,:,k]==tr["P_post"][:,0:1,k])
    else:
        ck.test("A_actual_center_unquantized",tr["feedback"]==tr["m_prior"])
    sq=(inp["x"][:,k,None]-tr["m_post"][:,:,k])**2
    paired=.5*(sq[:,1]+sq[:,2])-sq[:,0]
    theory=tr["gain"][:,0,k]**2*eta**2*tr["eligible"][:,0,k]
    ck.close("paired_damage_equals_theory",paired,theory)
    payload=np.nan_to_num(tr["payload"][:,:,k])
    pm=.5*(payload[:,1]**2+payload[:,2]**2)-payload[:,0]**2
    ck.close("C_payload_moment_identity",pm,eta**2*tr["eligible"][:,0,k])
    mp=tr["m_prior"][:,:,k+1]
    ck.close("C_predictor_moment_identity",.5*(mp[:,1]**2+mp[:,2]**2)-mp[:,0]**2,A*A*theory)
    # Conditional expectation diagnostic: valid analysis information, not online telemetry.
    postP=tr["P_post"][:,:,k];D=tr["mu_post"][:,:,k]-tr["m_post"][:,:,k]
    e=tr["qerror"][:,:,k+1];V=1/Z+A*A*postP+model["Q"]+R
    predicted_silence=np.exp(-(A*D-e)**2/(2*V))/np.sqrt(Z*V)
    ck.close("next_event_conditional_probability",1-tr["history_send_probability"][:,:,k+1],predicted_silence)
    return ck


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--out",required=True);args=ap.parse_args()
    out=Path(args.out).resolve()
    if out.exists():raise SystemExit("Refusing to overwrite an existing run.")
    out.mkdir(parents=True)
    raw=PROTOCOL.read_bytes();protocol=json.loads(raw)
    write_json(out/"protocol_snapshot.json",protocol)
    freeze={
        "code_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        "creation_time_utc":datetime.now(timezone.utc).isoformat(),
        "protocol_source":PROTOCOL.relative_to(ROOT).as_posix(),
        "protocol_source_sha256":sha(PROTOCOL),
        "protocol_snapshot_sha256":sha(out/"protocol_snapshot.json"),
        "code_sha256":{p.name:sha(p) for p in sorted(CODE.glob("*.py"))},
        "environment":{"python":sys.version,"executable":sys.executable,"numpy":np.__version__,
                       "platform":platform.platform(),"float":"float64","rng":"PCG64"},
        "base_commit":"7b14caa54caac116970b3aa0fb1ee2d9224f9d61",
        "stage":"FROZEN_BEFORE_INPUT_GENERATION","branches":BRANCHES,
        "tolerances":{"atol":ATOL,"rtol":RTOL},
    }
    write_json(out/"code_and_input_contract.json",freeze)
    try:
        pre=preflight(protocol)
        write_json(out/"preflight.json",pre.rows)
        if not pre.passed:raise AssertionError("Deterministic preflight failed.")
        inputs={}
        for model in protocol["models"]:
            mid=model["id"];inputs[mid]=generate_inputs(model,protocol)
            np.savez_compressed(out/(mid+"_inputs.npz"),**inputs[mid])
        write_json(out/"input_hashes_before_simulation.json",
                   {mid+"_inputs.npz":sha(out/(mid+"_inputs.npz")) for mid in inputs})
        write_json(out/"start_simulation.json",{
            "time_utc":datetime.now(timezone.utc).isoformat(),
            "input_hashes_recorded":True,"policy_receives_truth":False})
        all_checks=[];cases=[]
        for model in protocol["models"]:
            mid=model["id"];inp=inputs[mid]
            for level,(delta,eta) in enumerate(zip(model["design_constants"]["delta_grid"],
                                                 model["design_constants"]["eta_grid"]),1):
                for kind in ("A","B"):
                    case=f"{mid}_{kind}_d{level}"
                    tr=simulate(model,inp["y"],inp["U"],kind,delta,eta,model["k"])
                    target=out/(case+"_trace.npz")
                    np.savez_compressed(target,**tr)
                    check=verify_case(tr,inp,model,protocol,kind,delta,eta)
                    write_json(out/(case+"_assertions.json"),check.rows)
                    all_checks.extend([dict(case=case,**row) for row in check.rows])
                    cases.append(dict(id=case,model=mid,protocol=kind,level=level,
                                      delta=delta,eta=eta,trace=target.name,trace_sha256=sha(target),
                                      status="PASS" if check.passed else "FAIL"))
                    write_json(out/"cases.json",cases)
                    write_json(out/"all_assertions.json",all_checks)
                    if not check.passed:
                        np.savez_compressed(out/(case+"_failed_indices.npz"),**check.failures)
                        raise AssertionError("Hard consistency failure in "+case)
        write_json(out/"failure_records.json",[])
        write_json(out/"simulation_completion.json",{
            "status":"HARD_CHECKS_PASS","case_count":len(cases),
            "independent_base_samples":4096,"short_branch_paths":73728,
            "time_utc":datetime.now(timezone.utc).isoformat(),
            "assertions":len(all_checks),"code_sha256_after":{p.name:sha(p) for p in CODE.glob("*.py")}})
        print("E1 simulation complete; all runtime hard checks PASS. Independent audit still required.")
    except Exception:
        write_json(out/"failure_records.json",[{"exception":traceback.format_exc(),
                   "time_utc":datetime.now(timezone.utc).isoformat(),
                   "preservation":"All generated inputs and traces remain in this run; no samples deleted."}])
        raise


if __name__=="__main__":
    main()
