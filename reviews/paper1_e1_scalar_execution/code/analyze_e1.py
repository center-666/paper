"""Read a hard-check-passed run, bootstrap paired base samples, export evidence."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import math

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def json_write(p,obj):
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")


def certificate_constants(m,bref):
    """Original scalar exact-feedback certificate on finite P labels."""
    A,Q,R,Z=(m[k] for k in ("A","Q","R","Z"));ps=[m["P0"]];rad=0
    for t in range(m["k"]+1):
        gains0=[p/(p+R+1/Z) for p in ps];gains1=[p/(p+R) for p in ps]
        rad=max(1-g for g in gains0+gains1)*abs(A)*rad+max(gains1)
        posts=[p-p*p/(p+rr) for p in ps for rr in [R+1/Z,R]]
        ps=[A*A*p+Q for p in posts]
    V=1/Z+A*A*np.array(posts)+Q+R
    h=float(np.min(A*A/(2*V)));M=float(np.max(np.sqrt(Z*V)))
    B=rad*bref;q=-math.expm1(-h*B*B)/(B*B)
    return {"q":q,"M":M,"Omega":max(posts)-min(posts),"C_B":M/q+max(posts)-min(posts),
            "r_k":rad,"p_min":min(posts),"p_max":max(posts)}


def case_samples(tr,inp,case,m):
    k=m["k"];delta=case["delta"];eta=case["eta"];A,R,Z,Q=(m[z] for z in ("A","R","Z","Q"))
    errors=(inp["x"][:,k,None]-tr["m_post"][:,:,k])**2
    def anti(a):return (a[:,1]+a[:,2])/2
    P=tr["P_post"][:,:,k];V=1/Z+A*A*P+Q+R
    W=(~tr["sent"][:,:,k+1])*np.sqrt(Z*V)
    D=tr["mu_post"][:,:,k]-tr["m_post"][:,:,k]
    e=tr["qerror"][:,:,k+1]
    Wcond=np.exp(-(A*D-e)**2/(2*V))
    eligible=tr["eligible"][:,0,k]
    theory=tr["gain"][:,0,k]**2*eta**2*eligible
    payload=np.nan_to_num(tr["payload"][:,:,k])
    pred=tr["m_prior"][:,:,k+1]
    metric={
        "clean_mse":errors[:,0],"plus_mse":errors[:,1],"minus_mse":errors[:,2],
        "attack_mse":anti(errors),"J_paired":anti(errors)-errors[:,0],
        "J_formula":theory,"J_over_delta_squared":(anti(errors)-errors[:,0])/delta**2,
        "action_indicator":(tr["action"][:,1,k]!=0).astype(float),
        "energy_per_episode":tr["action"][:,1,k]**2,
        "clean_send_rate":tr["sent"][:,0,:].mean(axis=1),
        "attack_send_rate":anti(tr["sent"].mean(axis=2)),
        "clean_pre_target_rate":tr["sent"][:,0,:k].mean(axis=1),
        "attack_pre_target_rate":anti(tr["sent"][:,:,:k].mean(axis=2)),
        "clean_target_send":tr["sent"][:,0,k].astype(float),
        "clean_P_target":P[:,0],"attack_P_target":anti(P),
        "W_clean":W[:,0],"W_attack":anti(W),"W_gap":W[:,0]-anti(W),
        "W_cond_clean":Wcond[:,0],"W_cond_attack":anti(Wcond),
        "W_cond_gap":Wcond[:,0]-anti(Wcond),
        "next_event_change_plus":(tr["sent"][:,1,k+1]!=tr["sent"][:,0,k+1]).astype(float),
        "next_event_change_minus":(tr["sent"][:,2,k+1]!=tr["sent"][:,0,k+1]).astype(float),
        "payload_moment_gap":anti(payload**2)-payload[:,0]**2,
        "payload_moment_theory":eta**2*eligible,
        "predictor_moment_gap":anti(pred**2)-pred[:,0]**2,
        "predictor_moment_theory":A*A*theory,
        "payload_mean_gap":anti(payload)-payload[:,0],
        "predictor_mean_gap":anti(pred)-pred[:,0],
    }
    constants=certificate_constants(m,.1)
    if case["protocol"]=="A":
        # Sample plug-in of the existing population certificate, NOT a finite-sample risk bound.
        metric["certificate_plugin"]=metric["W_gap"]/constants["q"]+anti(P)-P[:,0]
        metric["certificate_conditional_diagnostic"]=metric["W_cond_gap"]/constants["q"]+anti(P)-P[:,0]
    return metric,constants


def main():
    ap=argparse.ArgumentParser();ap.add_argument("run");args=ap.parse_args()
    run=Path(args.run).resolve();dest=run/"analysis"
    if dest.exists():raise SystemExit("Analysis directory exists; preserve it and use an explicit revision.")
    audit=json.loads((run/"independent_audit.json").read_text(encoding="utf-8"))
    if audit["status"]!="PASS":raise SystemExit("Independent hard-check gate not passed.")
    freeze=json.loads((run/"code_and_input_contract.json").read_text(encoding="utf-8"))
    if freeze["code_sha256"][Path(__file__).name]!=sha(__file__):raise SystemExit("Analysis source not frozen.")
    dest.mkdir();cfg=json.loads((run/"protocol_snapshot.json").read_text(encoding="utf-8"))
    cases=json.loads((run/"cases.json").read_text(encoding="utf-8"))
    models={m["id"]:m for m in cfg["models"]}
    inputs={mid:dict(np.load(run/(mid+"_inputs.npz"))) for mid in models}
    samples={};traces={};constants={}
    for c in cases:
        tr=dict(np.load(run/c["trace"]));traces[c["id"]]=tr
        samples[c["id"]],constants[c["id"]]=case_samples(tr,inputs[c["model"]],c,models[c["model"]])
    # Physical/trigger samples shared across cells; identical resample indices within model.
    boot={}
    for mid in models:
        rng=np.random.Generator(np.random.PCG64(np.random.SeedSequence(
            [cfg["bootstrap"]["seed"],cfg["rng_plan"]["model_id"][mid]])))
        boot[mid]=rng.integers(0,2048,size=(1000,2048),dtype=np.int32)
    np.savez_compressed(dest/"bootstrap_indices.npz",**boot)
    for c in cases:
        s=samples[c["id"]];a=samples[f"{c['model']}_A_d{c['level']}"]
        s["healthy_mse_cost_vs_exact"]=s["clean_mse"]-a["clean_mse"]
        s["healthy_rate_difference_vs_exact"]=s["clean_send_rate"]-a["clean_send_rate"]
    fieldnames=sorted(set().union(*(s.keys() for s in samples.values())))
    with (dest/"sample_metrics.csv").open("w",newline="",encoding="utf-8") as f:
        wr=csv.DictWriter(f,fieldnames=["case","base_sample_id",*fieldnames]);wr.writeheader()
        for c in cases:
            ss=samples[c["id"]]
            for i in range(2048):
                wr.writerow({"case":c["id"],"base_sample_id":i,**{k:float(v[i]) for k,v in ss.items()}})
    summary=[]
    for c in cases:
        ss=samples[c["id"]];ix=boot[c["model"]];stats={}
        for name,arr in ss.items():
            estimate=float(np.mean(arr))
            ci=np.quantile(arr[ix].mean(axis=1),[.025,.975]).tolist()
            stats[name]={"mean":estimate,"bootstrap_percentile_95":ci}
        tr=traces[c["id"]]
        row={**c,"n_independent":2048,"statistics":stats,
             "max_action":float(np.abs(tr["action"]).max()),
             "nonzero_action_base_samples":int(np.count_nonzero(tr["action"][:,1,4])),
             "event_mismatch_base_samples":int(np.count_nonzero(np.any(tr["sent"]!=tr["sent"][:,0:1,:],axis=(1,2)))),
             "feedback_code_mismatch_base_samples":int(np.count_nonzero(np.any(tr["feedback_index"]!=tr["feedback_index"][:,0:1,:],axis=(1,2)))) if c["protocol"]=="B" else None,
             "target_P_mismatch_base_samples":int(np.count_nonzero(np.any(tr["P_post"][:,:,4]!=tr["P_post"][:,0:1,4],axis=1))),
             "C_payload_changed_base_samples":int(np.count_nonzero(np.any(
                 np.nan_to_num(tr["payload"][:,:,4])!=np.nan_to_num(tr["payload"][:,0:1,4]),axis=1))),
             "C_predictor_changed_base_samples":int(np.count_nonzero(np.any(
                 tr["m_prior"][:,:,5]!=tr["m_prior"][:,0:1,5],axis=1))),
             "certificate_constants_exact_only":constants[c["id"]] if c["protocol"]=="A" else None}
        summary.append(row)
    json_write(dest/"summary.json",{
        "status":"FROZEN_E1_ANALYSIS_COMPLETE","sampling_unit":"base physical and trigger sample, +/- averaged",
        "bootstrap":{"repetitions":1000,"seed":cfg["bootstrap"]["seed"],
                     "substreams":"SeedSequence([seed, model_id]); common indices across all cells within model",
                     "indices_sha256":sha(dest/"bootstrap_indices.npz"),
                     "scope":"exploratory, not simultaneous or rigorous damage-risk coverage"},
        "precision_region_only":True,"histogram_TV_computed":False,
        "cases":summary})
    flat=[]
    for row in summary:
        fs={k:row[k] for k in ["id","model","protocol","level","delta","eta","n_independent",
                                "max_action","nonzero_action_base_samples","event_mismatch_base_samples",
                                "feedback_code_mismatch_base_samples","target_P_mismatch_base_samples"]}
        for key,s in row["statistics"].items():
            fs[key]=s["mean"];fs[key+"_lo95"]=s["bootstrap_percentile_95"][0];fs[key+"_hi95"]=s["bootstrap_percentile_95"][1]
        flat.append(fs)
    with (dest/"summary.csv").open("w",newline="",encoding="utf-8") as f:
        names=list(dict.fromkeys(k for row in flat for k in row));wr=csv.DictWriter(f,fieldnames=names);wr.writeheader();wr.writerows(flat)
    views={
        "C_payload":"B trace: sent, feedback_index/value, P_post_target, plus payload fields. No new run.",
        "C_predictor":"B trace: same plus m_prior. No new run.",
        "A_rounded_log":"A trace: rounded_log_* fields computed passively; never used in actual center/update.",
        "metric_permissions":{"x_and_mu":"evaluation only","payload_and_m_prior":"enhanced C only",
                              "W":"observable score from P and event","W_cond":"oracle/conditional diagnostic, not observable"},
    }
    json_write(dest/"observation_views.json",views)
    make_figures(dest,summary)
    for row in summary:
        s=row["statistics"]
        print(row["id"],"J",s["J_paired"]["mean"],"J/d2",s["J_over_delta_squared"]["mean"],
              "cleanMSE",s["clean_mse"]["mean"],"rate",s["clean_send_rate"]["mean"],
              "event_changed",row["event_mismatch_base_samples"])


def make_figures(dest,summary):
    fig,axes=plt.subplots(2,2,figsize=(9,6.4),layout="constrained")
    colors={"S1":"#2166ac","U1":"#b2182b"}
    for model in ("S1","U1"):
        for protocol in ("A","B"):
            rows=[r for r in summary if r["model"]==model and r["protocol"]==protocol]
            x=[r["delta"] for r in rows];label=f"{model} {protocol}"
            for ax,key in [(axes[0,0],"J_paired"),(axes[0,1],"J_over_delta_squared"),
                           (axes[1,0],"clean_mse"),(axes[1,1],"clean_send_rate")]:
                y=np.array([r["statistics"][key]["mean"] for r in rows])
                ci=np.array([r["statistics"][key]["bootstrap_percentile_95"] for r in rows])
                ax.plot(x,y,marker="o" if protocol=="B" else "s",linestyle="-" if protocol=="B" else "--",
                        color=colors[model],label=label)
                ax.fill_between(x,ci[:,0],ci[:,1],color=colors[model],alpha=.09)
                ax.set_xscale("log");ax.set_xlabel("Feedback precision scale delta (A: dose label)")
                ax.grid(alpha=.22)
    axes[0,0].set_yscale("log");axes[0,0].set_ylabel("Realized witness damage J (not supremum)")
    axes[0,1].set_ylabel("J / delta squared")
    axes[1,0].set_ylabel("Healthy target MSE (own protocol)")
    axes[1,1].set_ylabel("Healthy uplink fraction, t=0..5")
    axes[0,0].legend(fontsize=8)
    fig.suptitle("Frozen scalar E1: k=4, b=0.1, 2048 independent base samples/model\nBands: paired-base bootstrap, 1000 replicates; precision-dominated regime only",fontsize=10)
    fig.savefig(dest/"e1_mechanism.png",dpi=180)
    fig.savefig(dest/"e1_mechanism.pdf")
    plt.close(fig)


if __name__=="__main__":
    main()
