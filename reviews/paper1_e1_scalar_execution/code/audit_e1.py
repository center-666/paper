"""Independent saved-array audit. Does not import the simulator or generate paths."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import sys

import numpy as np

CODE=Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument("run");args=ap.parse_args()
    run=Path(args.run).resolve()
    if (run/"independent_audit.json").exists():raise SystemExit("Audit output already exists.")
    config=json.loads((run/"protocol_snapshot.json").read_text(encoding="utf-8"))
    freeze=json.loads((run/"code_and_input_contract.json").read_text(encoding="utf-8"))
    cases=json.loads((run/"cases.json").read_text(encoding="utf-8"))
    rows=[];failed={}
    def check(name,good):
        good=np.asarray(good,dtype=bool);loc=np.argwhere(~good)
        row={"name":name,"n_checked":int(good.size),"n_failed":len(loc)}
        if len(loc):
            row["first_failure_indices"]=loc[:25].tolist()
            failed[name.replace("/","_")]=loc
        rows.append(row)
    def close(name,lhs,rhs,atol=1e-10,rtol=1e-8):
        l,r=np.broadcast_arrays(lhs,rhs)
        check(name,np.isclose(l,r,atol=atol,rtol=rtol))
        rows[-1]["max_absolute_error"]=float(np.max(np.abs(l-r)))
        rows[-1]["absolute_tolerance"]=atol;rows[-1]["relative_tolerance"]=rtol
    check("protocol_bytes_frozen",digest(run/"protocol_snapshot.json")==freeze["protocol_snapshot_sha256"])
    for name,h in freeze["code_sha256"].items():check("code_frozen_"+name,digest(CODE/name)==h)
    check("case_count",len(cases)==12)
    check("runner_gate",json.loads((run/"simulation_completion.json").read_text())["status"]=="HARD_CHECKS_PASS")
    check("failure_log_empty",json.loads((run/"failure_records.json").read_text())==[])
    inputs={};model_map={m["id"]:m for m in config["models"]}
    ih=json.loads((run/"input_hashes_before_simulation.json").read_text())
    for model in config["models"]:
        name=model["id"];inputs[name]=dict(np.load(run/(name+"_inputs.npz")))
        z=inputs[name];n,T=z["x"].shape
        check(name+"/sample_count",n==2048);check(name+"/horizon",T==6)
        check(name+"/input_hash",digest(run/(name+"_inputs.npz"))==ih[name+"_inputs.npz"])
        check(name+"/sample_ids",z["base_sample_id"]==np.arange(2048))
        close(name+"/physical_state_recursion",z["x"][:,1:],model["A"]*z["x"][:,:-1]+z["w"],1e-14,1e-13)
        close(name+"/physical_measurement_recursion",z["y"],z["x"]+z["v"],1e-14,1e-13)
        check(name+"/uniform_range",(z["U"]>=0)&(z["U"]<1))
        # Recompute P-label set via precision update, independently of prepare_design.
        priors=[float(model["P0"])]
        for _ in range(4):
            priors=[model["A"]**2/(1/p+1/r)+model["Q"]
                    for p in priors for r in [model["R"]+1/model["Z"],model["R"]]]
        gains=[p/(p+model["R"]) for p in priors]
        alpha_max=abs(model["A"])*max(gains)
        alpha_min=abs(model["A"])*min(gains)
        pstar=min(1-1/math.sqrt(1+model["Z"]*(p+model["R"])) for p in priors)
        Lstar=(math.sqrt(2/(math.pi*(min(priors)+model["R"])))+
               math.sqrt(model["Z"]/math.e))/alpha_min
        cap=min(.1,pstar/Lstar/2,alpha_max*.1/2)
        close(name+"/frozen_delta_grid",model["design_constants"]["delta_grid"],cap*np.array([.25,.5,1]),1e-14,1e-13)
        close(name+"/frozen_eta_grid",model["design_constants"]["eta_grid"],cap*np.array([.25,.5,1])/(2*alpha_max),1e-14,1e-13)
    loaded={}
    for case in cases:
        cid=case["id"];loaded[cid]=tr=dict(np.load(run/case["trace"]))
        m=model_map[case["model"]];z=inputs[m["id"]]
        A,Q,R,Z=(m[k] for k in ("A","Q","R","Z"));delta=case["delta"];eta=case["eta"]
        check(cid+"/trace_hash",digest(run/case["trace"])==case["trace_sha256"])
        check(cid+"/shape",tr["sent"].shape==(2048,3,6))
        for f in ["m_prior","m_post","P_prior","P_post","feedback","action","mu_prior","mu_post"]:
            check(cid+"/finite_"+f,np.isfinite(tr[f]))
        # Independently reconstruct inputs to each transition from stored predecessor.
        prev_mean=np.concatenate([np.zeros((2048,3,1)),A*tr["m_post"][:,:,:-1]],axis=2)
        prev_var=np.concatenate([np.full((2048,3,1),m["P0"]),A*A*tr["P_post"][:,:,:-1]+Q],axis=2)
        close(cid+"/prediction_from_previous",tr["m_prior"],prev_mean)
        close(cid+"/cov_prediction_from_previous",tr["P_prior"],prev_var)
        virtual_idx=np.floor((prev_mean+delta)/(2*delta)).astype(np.int64)
        center=2*delta*virtual_idx if case["protocol"]=="B" else prev_mean
        close(cid+"/actual_center",tr["feedback"],center,0,0)
        check(cid+"/rounded_log_is_view",tr["rounded_log_index"]==virtual_idx)
        close(cid+"/rounded_log_value",tr["rounded_log_feedback"],2*delta*virtual_idx,0,0)
        if case["protocol"]=="B":
            check(cid+"/index_matches_center",tr["feedback_index"]==virtual_idx)
        event=z["U"][:,None,:]>np.exp(-Z*(z["y"][:,None,:]-center)**2/2)
        check(cid+"/event_precedes_payload",tr["sent"]==event)
        check(cid+"/payload_presence",np.isfinite(tr["payload"])==event)
        gain_send=prev_var/(prev_var+R)
        next_without_mod=A*(prev_mean[:,:,4]+gain_send[:,:,4]*(z["y"][:,4,None]-prev_mean[:,:,4]))
        gate_idx=np.floor((next_without_mod+delta)/(2*delta)).astype(np.int64)
        # Distance to nearest boundary; same open central half geometry, independently written.
        dist=delta-np.abs(next_without_mod-2*delta*gate_idx)
        gate=event[:,:,4] & (dist>delta/2)
        check(cid+"/legal_gate_reconstructed",tr["eligible"][:,:,4]==gate)
        close(cid+"/disclosed_gate_M",tr["gate_M"][:,:,4][event[:,:,4]],
              next_without_mod[event[:,:,4]])
        a=np.zeros_like(prev_mean)
        a[:,:,4]=eta*gate*np.array([0,1,-1])[None,:]
        close(cid+"/actions_from_legal_inputs",tr["action"],a,0,0)
        check(cid+"/budget",np.abs(a)<=config["b"])
        received=np.where(event,z["y"][:,None,:]+a,np.nan)
        close(cid+"/payload_values",tr["payload"][event],received[event],0,0)
        Ri=np.where(event,R,R+1/Z)
        # Posterior precision form differs algebraically from the runtime gain form.
        postvar=1/(1/prev_var+1/Ri)
        postmean=postvar*(prev_mean/prev_var+np.where(event,np.nan_to_num(received),center)/Ri)
        close(cid+"/receiver_posterior_independent",tr["m_post"],postmean)
        close(cid+"/receiver_covariance_independent",tr["P_post"],postvar)
        muprior=np.concatenate([np.zeros((2048,3,1)),A*tr["mu_post"][:,:,:-1]],axis=2)
        mupost=postvar*(muprior/prev_var+np.where(event,z["y"][:,None,:],center)/Ri)
        close(cid+"/true_history_posterior_independent",tr["mu_post"],mupost)
        close(cid+"/healthy_conditional_mean",tr["m_post"][:,0],mupost[:,0])
        pset=[m["P0"]]
        for _ in range(4):pset=[A*A/(1/p+1/r)+Q for p in pset for r in [R+1/Z,R]]
        check(cid+"/target_covariance_in_finite_set",
              np.min(abs(prev_var[:,0,4,None]-np.array(pset)),axis=1)<1e-12)
        expected_damage=gain_send[:,0,4]**2*eta**2*gate[:,0]
        squared=(z["x"][:,4,None]-tr["m_post"][:,:,4])**2
        damage=(squared[:,1]+squared[:,2])/2-squared[:,0]
        close(cid+"/paired_target_damage",damage,expected_damage)
        # C contains the same B trajectories with additional observations.
        if case["protocol"]=="B":
            check(cid+"/B_all_events_equal",tr["sent"]==tr["sent"][:,0:1,:])
            check(cid+"/B_all_codes_equal",tr["feedback_index"]==tr["feedback_index"][:,0:1,:])
            check(cid+"/B_all_feedback_equal",tr["feedback"]==tr["feedback"][:,0:1,:])
            check(cid+"/B_target_P_equal",tr["P_post"][:,:,4]==tr["P_post"][:,0:1,4])
        q=np.nan_to_num(received[:,:,4])
        close(cid+"/C_payload_empirical_vs_analytic",
              (q[:,1]**2+q[:,2]**2)/2-q[:,0]**2,eta**2*gate[:,0])
        p=tr["m_prior"][:,:,5]
        close(cid+"/C_predictor_empirical_vs_analytic",
              (p[:,1]**2+p[:,2]**2)/2-p[:,0]**2,A*A*expected_damage)
    for name in model_map:
        ref=loaded[name+"_A_d1"]
        for level in [2,3]:
            tr=loaded[f"{name}_A_d{level}"]
            check(f"{name}/A_healthy_delta_independent_{level}",tr["sent"][:,0]==ref["sent"][:,0])
            close(f"{name}/A_healthy_values_delta_independent_{level}",tr["m_post"][:,0],ref["m_post"][:,0],0,0)
    status="PASS" if not failed else "FAIL"
    result={"status":status,"independence":"Separate algebraic saved-array reconstruction; no import of simulator helpers; no new physical samples.",
            "cases":len(cases),"base_samples":4096,"checks":rows,
            "failed_check_names":list(failed),
            "code_sha256":digest(__file__),"current_code_matches_run_contract":digest(__file__)==freeze["code_sha256"][Path(__file__).name]}
    (run/"independent_audit.json").write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    if failed:
        np.savez_compressed(run/"independent_failed_indices.npz",**failed)
    print(json.dumps({"status":status,"n_checks":len(rows),"failed":list(failed)},indent=2))
    if failed:raise SystemExit(1)


if __name__=="__main__":
    main()
