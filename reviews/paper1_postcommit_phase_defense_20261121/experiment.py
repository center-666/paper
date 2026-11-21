"""Frozen, independent scalar phase-feedback experiment; refuses overwrite."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
from pathlib import Path
import subprocess
import sys
import traceback

import numpy as np
from scipy.special import ndtr

from core import (attack,constants,conformal_threshold,phase_deficit,phase_response,
                  quantize,quadrature_effect,run_episode_arrays,wilson)

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
RESULT=HERE/"results/run_v1"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path,obj):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+"\n",
                    encoding="utf8",newline="\n")


def preflight():
    protocol=json.loads((HERE/"protocol.json").read_text(encoding="utf8"))
    tests=[]
    def check(name,good,detail=None):
        tests.append({"name":name,"pass":bool(good),"detail":detail})
        if not good:
            write(HERE/"preflight_failure.json",tests)
            raise AssertionError(name)
    check("half_open_quantizer",np.array_equal(quantize(np.array([-.75,-.25,.25,.75]),.25),[-.5,0,.5,1]))
    d=np.linspace(-.2,.2,201)
    f=phase_response(d,.1,.9,64)
    exact=np.sqrt(2*np.pi*.9)/.2*(ndtr((.1-d)/np.sqrt(.9))-ndtr((-.1-d)/np.sqrt(.9)))
    check("phase_integral_vs_gaussian_cdf",np.max(abs(f-exact))<2e-14,float(np.max(abs(f-exact))))
    check("phase_response_maximum",np.all(f<=phase_response(0,.1,.9,64)+1e-15))
    check("stable_deficit_positive",np.all(phase_deficit(np.array([1e-8,1e-5,.01,.1]),.1,.9,64)>0))
    for model in json.loads((HERE/"protocol.json").read_text(encoding="utf8"))["models"]:
        k,lam,var=constants(model)
        u=np.linspace(-3,3,10001)
        sent=np.arange(len(u))%3!=0
        signs=(np.arange(len(u))%2)*.75
        acc=np.full(len(u),.1)
        for kind in ["cell_sign","balanced_reflection","bounded_sign"]:
            a=attack(np.where(sent,u,np.nan),sent,signs,acc,model,.02,.1,kind,np.zeros_like(u))
            check(model["id"]+kind+"_bounded_sent_only",np.all(abs(a)<=.1+1e-12) and np.all(a[~sent]==0))
            if kind!="bounded_sign":
                check(model["id"]+kind+"_fixed_code_invariant",np.array_equal(quantize(lam*(u+a),.02),quantize(lam*u,.02)))
        # Check formula (3) on a conservative compact rectangle.
        V=var+1/model["Z"]
        B=.2
        q=model["A"]**2/(2*V)*np.exp(-(model["A"]**2*B**2+.25**2)/(2*V))
        ds=np.linspace(-B,B,211)
        lhs=phase_deficit(model["A"]*ds,.25,V,64)/phase_response(0,.25,V,64)
        check(model["id"]+"_secant_bound",np.all(lhs+1e-15>=q*ds*ds))
        # Fresh phase is deliberately absent from the attack API inputs.
        check("postcommit_attack_has_no_future_phase_argument", "phase_u" not in attack.__code__.co_varnames)
    # For either target-event covariance branch, averaging the phase-specific
    # healthy Bernoulli probability must equal the analytic event-only baseline.
    model=protocol["models"][0]
    for sent in (False,True):
        P=model["P0"]*model["R"]/(model["P0"]+model["R"]) if sent else model["P0"]*(model["R"]+1/model["Z"])/(model["P0"]+model["R"]+1/model["Z"])
        sig=model["A"]**2*P+model["Q"]+model["R"]
        V=sig+1/model["Z"]
        quad=phase_response(0,.037,V,64)
        exact=np.sqrt(2*np.pi*V)/(2*.037)*(ndtr(.037/np.sqrt(V))-ndtr(-.037/np.sqrt(V)))
        check("event_only_health_center_"+str(sent),abs(quad-exact)<2e-14,float(abs(quad-exact)))
    write(HERE/"preflight.json",{"status":"PASS","checks":tests})
    return tests


def freeze():
    if (HERE/"freeze.json").exists():
        raise SystemExit("Existing freeze: refusing overwrite.")
    preflight()
    paths=subprocess.check_output(["git","ls-files","-co","--exclude-standard","-z"],cwd=REPO).decode("utf8").split("\0")
    protected={p:sha(REPO/p) for p in paths if p and (REPO/p).is_file()
               and not p.startswith(HERE.relative_to(REPO).as_posix()+"/")}
    write(HERE/"protected_before.json",protected)
    write(HERE/"freeze.json",{
        "stage":"FROZEN_BEFORE_RANDOM_INPUTS",
        "head":subprocess.check_output(["git","rev-parse","HEAD"],cwd=REPO,text=True).strip(),
        "protocol_sha256":sha(HERE/"protocol.json"),
        "deterministic_tv_sha256":sha(HERE/"deterministic_tv_checks.json"),
        "code_sha256":{p.name:sha(p) for p in HERE.glob("*.py")},
        "python":sys.version,"numpy":np.__version__,"platform":platform.platform(),
        "samples_generated":False,
    })
    print("Frozen protocol, implementation and existing-file hashes.")


def verify_freeze():
    f=json.loads((HERE/"freeze.json").read_text(encoding="utf8"))
    assert sha(HERE/"protocol.json")==f["protocol_sha256"]
    assert sha(HERE/"deterministic_tv_checks.json")==f["deterministic_tv_sha256"]
    for name,digest in f["code_sha256"].items():
        assert sha(HERE/name)==digest,name


def inputs(model,n,split,seed):
    mid=1 if model["id"]=="S1" else 2
    rngs=[np.random.default_rng(np.random.SeedSequence([seed,mid,split,j])) for j in range(8)]
    x0=np.sqrt(model["P0"])*rngs[0].normal(size=n)
    x1=model["A"]*x0+np.sqrt(model["Q"])*rngs[1].normal(size=n)
    return {"x0":x0,"x1":x1,
            "y0":x0+np.sqrt(model["R"])*rngs[2].normal(size=n),
            "y1":x1+np.sqrt(model["R"])*rngs[3].normal(size=n),
            "u0":rngs[4].random(n),"u1":rngs[5].random(n),
            "phase_u":rngs[6].random(n),"sign_u":rngs[7].random(n),
            "accept_u":rngs[7].random(n)}


def estimate(x):
    x=np.asarray(x,dtype=float)
    return {"mean":float(np.mean(x)),"se":float(np.std(x,ddof=1)/np.sqrt(len(x)))}


def rate(x):
    return {"rate":float(np.mean(x)),"n":len(x),"count":int(np.sum(x)),
            "wilson95":wilson(int(np.sum(x)),len(x))}


def csv_write(path,rows):
    with Path(path).open("w",encoding="utf8",newline="") as f:
        fields=sorted({k for row in rows for k in row})
        w=csv.DictWriter(f,fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in row.items()})


def run():
    verify_freeze()
    if RESULT.exists():
        raise SystemExit("Run directory exists: refusing overwrite.")
    RESULT.mkdir(parents=True)
    protocol=json.loads((HERE/"protocol.json").read_text(encoding="utf8"))
    rows=[];windows=[];plans=[];checks=[];input_hashes={}
    try:
        for model in protocol["models"]:
            m_id=model["id"]
            cal=inputs(model,protocol["calibration_episodes"],0,protocol["master_seed"])
            test=inputs(model,protocol["test_episodes"],1,protocol["master_seed"])
            for split,data in [("cal",cal),("test",test)]:
                p=RESULT/(m_id+"_"+split+"_inputs.npz")
                np.savez_compressed(p,**data)
                input_hashes[p.name]=sha(p)
            write(RESULT/"input_hashes.json",input_hashes)
            deltas=[model["legacy_delta"]*x for x in protocol["delta_multipliers"]]+protocol["stress_delta"]
            for level,delta in enumerate(deltas):
                for setting in protocol["protocols"]:
                    hc=run_episode_arrays(model,cal,delta,protocol["b"],setting,"healthy")
                    ht=run_episode_arrays(model,test,delta,protocol["b"],setting,"healthy")
                    thresholds={"conditional":{},"event_only":{}}
                    thresholds["conditional"]["single"]=conformal_threshold(
                        hc["conditional_score"],protocol["alpha"])
                    if setting!="fixed":
                        thresholds["event_only"]["single"]=conformal_threshold(
                            hc["event_score"],protocol["alpha"])
                    for n in protocol["block_sizes"]:
                        score=hc["conditional_score"].reshape(-1,n).sum(axis=1)
                        thresholds["conditional"][n]=conformal_threshold(score,protocol["alpha"])
                        if setting!="fixed":
                            score=hc["event_score"].reshape(-1,n).sum(axis=1)
                            thresholds["event_only"][n]=conformal_threshold(score,protocol["alpha"])
                    threshold_path=RESULT/(f"{m_id}_{level}_{setting}_thresholds.json")
                    write(threshold_path,{"model":m_id,"delta":delta,"protocol":setting,
                        "alpha":protocol["alpha"],"calibration_episodes":len(cal["x0"]),
                        "single_episode_thresholds":{name:values["single"] for name,values in thresholds.items() if values},
                        "block_thresholds":thresholds,
                        "method":"split conformal order statistic; strict greater-than; independent healthy calibration"})
                    for kind in protocol["attacks"]:
                        attacked=run_episode_arrays(model,test,delta,protocol["b"],setting,kind)
                        check={"model":m_id,"delta":delta,"setting":setting,"attack":kind,
                            "bounded":bool(np.all(abs(attacked["action"])<=protocol["b"]+1e-12)),
                            "only_sent":bool(np.all(attacked["action"][~attacked["send0"]]==0)),
                            "fixed_public_cell_code_invariant":bool(np.all(attacked["same_next_code"])) if kind!="bounded_sign" and setting!="postcommit_phase" else None,
                            "finite_detector":bool(np.all(np.isfinite(attacked["conditional_score"]))) and bool(np.all(np.isfinite(attacked["event_score"])))}
                        assert check["bounded"] and check["only_sent"] and check["finite_detector"]
                        if check["fixed_public_cell_code_invariant"] is not None:
                            assert check["fixed_public_cell_code_invariant"]
                        checks.append(check)
                        row={"model":m_id,"delta":delta,"level":level,"stress":level>=3,
                             "protocol":setting,"attack":kind,"n":len(test["x0"]),
                             "conditional_score":estimate(attacked["conditional_score"]),
                             "healthy_conditional_score":estimate(ht["conditional_score"]),
                             "conditional_single_fpr":rate(ht["conditional_score"]>thresholds["conditional"]["single"]),
                             "conditional_single_detection":rate(attacked["conditional_score"]>thresholds["conditional"]["single"]),
                             "event_only_score":estimate(attacked["event_score"]) if setting!="fixed" else None,
                             "healthy_event_only_score":estimate(ht["event_score"]) if setting!="fixed" else None,
                             "event_only_single_fpr":rate(ht["event_score"]>thresholds["event_only"]["single"]) if setting!="fixed" else None,
                             "event_only_single_detection":rate(attacked["event_score"]>thresholds["event_only"]["single"]) if setting!="fixed" else None,
                             "healthy_target_mse":estimate(ht["healthy_mse"]),
                             "true_paired_target_damage":estimate(attacked["damage_paired"]),
                             "conditional_target_damage":estimate(attacked["damage_conditional"]),
                             "nonzero_action_rate":float(np.mean(attacked["action"]!=0)),
                             "action_energy":float(np.mean(attacked["action"]**2)),
                             "healthy_next_send_rate":float(np.mean(ht["send1"])),
                             "attacked_next_send_rate":float(np.mean(attacked["send1"])),
                             "same_next_code_rate":float(np.mean(attacked["same_next_code"])),
                             "same_next_event_rate":float(np.mean(attacked["same_next_event"])),
                             "score_available_rate":float(np.mean(attacked["send0"])),
                             "phase_draws_per_episode":int(setting!="fixed"),
                             "phase_bits_claimed":False,
                             "phase_visibility":"known before attack" if setting=="public_phase" else
                                 ("drawn after attack; disclosed in next feedback" if setting=="postcommit_phase" else "fixed zero"),
                             "health_next_quantization_error2":float(np.mean((ht["center"]-ht["prior1"])**2)),
                             "healthy_next_mse":None,
                             "next_time_no_payload_attack":True}
                        # Update t=1 only to evaluate each protocol's own healthy cost.
                        p0post=np.where(ht["send0"],model["P0"]*model["R"]/(model["P0"]+model["R"]),
                            model["P0"]*(model["R"]+1/model["Z"])/(model["P0"]+model["R"]+1/model["Z"]))
                        p1=model["A"]**2*p0post+model["Q"]
                        r1=np.where(ht["send1"],model["R"],model["R"]+1/model["Z"])
                        k1=p1/(p1+r1)
                        post1=ht["prior1"]+k1*(np.where(ht["send1"],test["y1"],ht["center"])-ht["prior1"])
                        row["healthy_next_mse"]=estimate((test["x1"]-post1)**2)
                        rows.append(row)
                        detector_fields=[("conditional","conditional_score")]
                        if setting!="fixed":
                            detector_fields.append(("event_only","event_score"))
                        for detector,field in detector_fields:
                            for n in protocol["block_sizes"]:
                                hb=ht[field].reshape(-1,n).sum(axis=1)
                                ab=attacked[field].reshape(-1,n).sum(axis=1)
                                threshold=thresholds[detector][n]
                                windows.append({"model":m_id,"delta":delta,"stress":level>=3,
                                    "protocol":setting,"attack":kind,"detector":detector,
                                    "block_size":n,"threshold":threshold,
                                    "health_fpr":rate(hb>threshold),
                                    "attack_alarm":rate(ab>threshold),
                                    "paired_alarm_difference":estimate((ab>threshold).astype(float)-(hb>threshold).astype(float))})
                # No public-phase planning is fabricated: its attack adapts to s.
                qlow={k:quadrature_effect(model,delta,protocol["b"],k,12,32)
                      for k in ["healthy"]+protocol["attacks"]}
                qhigh={k:quadrature_effect(model,delta,protocol["b"],k,24,64)
                       for k in ["healthy"]+protocol["attacks"]}
                for kind in protocol["attacks"]:
                    for setting in ["fixed","postcommit_phase"]:
                        qa=qhigh[kind][setting];qh=qhigh["healthy"][setting]
                        effect=qa["mean"]-qh["mean"]
                        need=(math.ceil(((2.3263478740408408*np.sqrt(qh["variance"])+
                            .8416212335729143*np.sqrt(qa["variance"]))/effect)**2)
                            if effect>1e-16 else None)
                        plans.append({"model":m_id,"delta":delta,"stress":level>=3,
                            "attack":kind,"protocol":setting,"quadrature_low":qlow[kind][setting],
                            "quadrature_high":qa,"healthy_quadrature":qh,
                            "mean_order_difference":abs(qlow[kind][setting]["mean"]-qa["mean"]),
                            "n_plan_1pct_80pct_clt":need,"power_planning_is_not_guarantee":True})
                        if setting=="postcommit_phase":
                            event_effect=qa["event_mean"]-qh["event_mean"]
                            event_need=(math.ceil(((2.3263478740408408*np.sqrt(qh["event_variance"])+
                                .8416212335729143*np.sqrt(qa["event_variance"]))/event_effect)**2)
                                if event_effect>1e-16 else None)
                            plans.append({"model":m_id,"delta":delta,"stress":level>=3,
                                "attack":kind,"protocol":setting,"detector":"event_only_phase_marginal",
                                "attack_mean":qa["event_mean"],"healthy_mean":qh["event_mean"],
                                "mean_difference":event_effect,
                                "attack_variance":qa["event_variance"],
                                "healthy_variance":qh["event_variance"],
                                "n_plan_1pct_80pct_clt":event_need,
                                "power_planning_is_normal_approximation_not_guarantee":True})
                print(m_id,level,delta,"done",flush=True)
        csv_write(RESULT/"episode_summary.csv",rows)
        csv_write(RESULT/"window_results.csv",windows)
        write(RESULT/"planning.json",plans)
        write(RESULT/"runtime_checks.json",checks)
        write(RESULT/"completion.json",{"status":"PASS","episode_rows":len(rows),
            "window_rows":len(windows),"planning_rows":len(plans),
            "test_parameters_changed":False,"detector_refit_on_attack":False,
            "protected_old_inputs_modified":False,"new_safe_update_module":False})
        protected=json.loads((HERE/"protected_before.json").read_text(encoding="utf8"))
        changed=[p for p,digest in protected.items() if sha(REPO/p)!=digest]
        if changed:
            raise AssertionError("Protected pre-existing files changed: "+", ".join(changed[:10]))
        write(RESULT/"protected_file_check.json",{"checked":len(protected),"changed":changed,"pass":not changed})
        write(RESULT/"result_manifest.json",{p.relative_to(RESULT).as_posix():sha(p)
             for p in sorted(RESULT.iterdir()) if p.is_file() and p.name!="result_manifest.json"})
    except Exception:
        write(RESULT/"failure.json",{"traceback":traceback.format_exc(),"all_inputs_and_partial_results_preserved":True})
        raise


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("command",choices=["preflight","freeze","run"])
    args=parser.parse_args()
    {"preflight":preflight,"freeze":freeze,"run":run}[args.command]()
