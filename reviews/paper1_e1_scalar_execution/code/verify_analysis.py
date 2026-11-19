"""Recompute reported means and selected paired intervals from published artifacts."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import numpy as np


def main():
    ap=argparse.ArgumentParser();ap.add_argument("run");args=ap.parse_args()
    run=Path(args.run).resolve();dest=run/"analysis"
    if (dest/"analysis_validation.json").exists():raise SystemExit("Do not overwrite prior validation.")
    report=json.loads((dest/"summary.json").read_text(encoding="utf-8"))
    config=json.loads((run/"protocol_snapshot.json").read_text(encoding="utf-8"))
    models={m["id"]:m for m in config["models"]};indices=dict(np.load(dest/"bootstrap_indices.npz"))
    checks=[]
    def close(case,name,lhs,rhs):
        good=bool(np.allclose(lhs,rhs,atol=1e-12,rtol=1e-9))
        checks.append(dict(case=case,metric=name,passed=good,
                           max_error=float(np.max(np.abs(np.asarray(lhs)-np.asarray(rhs))))))
    with (dest/"sample_metrics.csv").open(encoding="utf-8",newline="") as f:
        csvrows=list(csv.DictReader(f))
    for entry in report["cases"]:
        cid=entry["id"];m=models[entry["model"]];tr=dict(np.load(run/entry["trace"]))
        inp=dict(np.load(run/(entry["model"]+"_inputs.npz")))
        sq=(inp["x"][:,4,None]-tr["m_post"][:,:,4])**2
        J=(sq[:,1]+sq[:,2])/2-sq[:,0]
        if entry["protocol"]=="B":
            aref=dict(np.load(run/f"{entry['model']}_A_d{entry['level']}_trace.npz"))
            base=(inp["x"][:,4]-aref["m_post"][:,0,4])**2
        else:base=sq[:,0]
        payload=np.nan_to_num(tr["payload"][:,:,4]);pred=tr["m_prior"][:,:,5]
        energy=tr["action"][:,1,4]**2
        expected={
            "clean_mse":sq[:,0],"plus_mse":sq[:,1],"minus_mse":sq[:,2],
            "attack_mse":(sq[:,1]+sq[:,2])/2,"J_paired":J,
            "J_formula":tr["gain"][:,0,4]**2*energy,
            "J_over_delta_squared":J/entry["delta"]**2,
            "clean_send_rate":np.sum(tr["sent"][:,0],axis=1)/6,
            "attack_send_rate":(np.sum(tr["sent"][:,1],axis=1)+np.sum(tr["sent"][:,2],axis=1))/12,
            "action_indicator":(energy>0).astype(float),"energy_per_episode":energy,
            "healthy_mse_cost_vs_exact":sq[:,0]-base,
            "payload_moment_gap":(payload[:,1]**2+payload[:,2]**2)/2-payload[:,0]**2,
            "payload_moment_theory":energy,
            "predictor_moment_gap":(pred[:,1]**2+pred[:,2]**2)/2-pred[:,0]**2,
            "predictor_moment_theory":m["A"]**2*tr["gain"][:,0,4]**2*energy,
        }
        subset=[x for x in csvrows if x["case"]==cid]
        assert len(subset)==2048 and [int(x["base_sample_id"]) for x in subset]==list(range(2048))
        for metric,arr in expected.items():
            close(cid,metric+"_csv",np.array([float(x[metric]) for x in subset]),arr)
            saved=entry["statistics"][metric]
            close(cid,metric+"_mean",saved["mean"],arr.mean())
            if metric in ("J_paired","J_over_delta_squared","healthy_mse_cost_vs_exact",
                          "payload_moment_gap","predictor_moment_gap"):
                replicate_means=arr[indices[entry["model"]]].mean(axis=1)
                close(cid,metric+"_bootstrap",saved["bootstrap_percentile_95"],
                      np.percentile(replicate_means,[2.5,97.5]))
    assert len(csvrows)==12*2048
    results={"status":"PASS" if all(x["passed"] for x in checks) else "FAIL",
             "checks":checks,"sample_summary_rows":len(csvrows),
             "bootstrap_unit":"2048 base samples per model; saved common indices; no independent sign counting",
             "reads_only_saved_raw":True,
             "raw_inputs_verified_in":"../independent_audit.json",
             "source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (dest/"analysis_validation.json").write_text(json.dumps(results,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in results.items() if k!="checks"},indent=2))
    if results["status"]!="PASS":raise SystemExit(1)


if __name__=="__main__":
    main()
