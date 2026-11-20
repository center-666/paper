"""Separate read-only reconstruction of saved raw arrays. No simulator imports."""
from pathlib import Path
import csv
import hashlib
import json
import math
import sys
import numpy as np

HERE=Path(__file__).resolve().parent
RUN=HERE/"results/run_20261120_v1"


def main():
    cfg=json.loads((HERE/"protocol.json").read_text(encoding="utf-8"))
    checks=[]
    def check(name,passed,**details):
        checks.append(dict(name=name,passed=bool(passed),**details))
    def close(name,actual,expected,atol=1e-11,rtol=1e-10):
        err=float(np.max(np.abs(np.asarray(actual)-np.asarray(expected))))
        check(name,np.allclose(actual,expected,atol=atol,rtol=rtol),max_abs_error=err)
    old=json.loads((HERE/"protected_before.json").read_text(encoding="utf-8"))
    root=HERE.parents[1]
    changed=[n for n,h in old["files"].items() if not (root/n).is_file() or hashlib.sha256((root/n).read_bytes()).hexdigest()!=h]
    check("protected_assets_unchanged",not changed,changed=changed)
    manifest=json.loads((RUN/"result_manifest.json").read_text(encoding="utf-8"))
    for n,h in manifest["files_sha256"].items():
        check("output_hash/"+n,hashlib.sha256((RUN/n).read_bytes()).hexdigest()==h)
    source=json.loads((HERE/"input_manifest.json").read_text(encoding="utf-8"))
    for n,info in source["files"].items():
        check("input_hash/"+n,hashlib.sha256((HERE/"inputs"/n).read_bytes()).hexdigest()==info["sha256"])
    thresholds=json.loads((RUN/"calibration_thresholds.json").read_text(encoding="utf-8"))
    rows=list(csv.DictReader((RUN/"single_test_results.csv").open(encoding="utf-8-sig")))
    windows=list(csv.DictReader((RUN/"window_results.csv").open(encoding="utf-8-sig")))
    auths=list(csv.DictReader((RUN/"full_auth_results.csv").open(encoding="utf-8-sig")))
    for model in cfg["models"]:
        mid=model["id"]; A,R,Q,Z,P=(model[k] for k in ("A","R","Q","Z","P0"))
        K=P/(P+R); lam=A*K; s=A*A*P*R/(P+R)+Q+R
        inp=dict(np.load(HERE/"inputs"/f"test_{mid}.npz"))
        cal_inp=dict(np.load(HERE/"inputs"/f"cal_{mid}.npz"))
        u=inp["x0"]+inp["v0"]
        y=A*inp["x0"]+inp["w0"]+inp["v1"]
        sent0=inp["u0"]>np.exp(-Z*u*u/2)
        clean_sq=(inp["x0"]-K*u*sent0)**2
        def quant(x,delta):
            return 2*delta*np.floor((x+delta)/(2*delta))
        for delta in model["delta_grid"]:
            key=f"{mid}_{delta:.12g}"
            clean=dict(np.load(RUN/"raw"/f"{key}_healthy.npz"))
            cal=dict(np.load(RUN/"calibration"/f"{key}.npz"))
            vals=np.sort(cal["score"][cal["available"]])
            tau=vals[math.ceil(.99*(len(vals)+1))-1]
            close(key+"/health_only_threshold",thresholds[key]["single_threshold"],tau,0,0)
            close(key+"/health_mse",clean["mse"],clean_sq)
            for attack in cfg["attacks"]:
                cid=key+"_"+attack
                tr=dict(np.load(RUN/"raw"/f"{cid}.npz"))
                z=u+tr["action"]
                c=quant(np.where(sent0,lam*z,0),delta)
                next_sent=inp["u1"]>np.exp(-Z*(y-c)**2/2)
                check(cid+"/event0_before_action",np.array_equal(sent0,tr["send0"]))
                check(cid+"/event1_from_actual_center",np.array_equal(next_sent,tr["send1"]))
                check(cid+"/pathwise_event_preservation",np.array_equal(next_sent,clean["send1"]))
                check(cid+"/pathwise_code_preservation",np.array_equal(c,clean["c1"]))
                check(cid+"/pathwise_P1_preservation",np.array_equal(tr["P1_post"],clean["P1_post"]))
                check(cid+"/budget",np.all(np.abs(tr["action"])<=cfg["b"]))
                check(cid+"/silent_zero_action",np.all(tr["action"][~sent0]==0))
                if attack=="cell_sign":
                    gate=sent0 & (np.abs(lam*u-quant(lam*u,delta))<delta/2)
                    expected=np.where(inp["sign_u"]<.5,1,-1)*min(cfg["b"],delta/(2*abs(lam)))*gate
                    close(cid+"/legacy_sign_policy",tr["action"],expected,1e-14,1e-12)
                else:
                    disc=np.where(sent0,u,0)
                    ref=2*quant(lam*disc,delta)/lam-disc
                    ix=(lam*disc+delta)/(2*delta)
                    boundary=sent0&(ix==np.rint(ix))
                    ref=np.where(boundary,disc,ref)
                    f=lambda x:np.exp(-x*x/(2*(P+R)))*(-np.expm1(-Z*x*x/2))/np.sqrt(2*np.pi*(P+R))
                    fu,ft=f(disc),f(ref)
                    alpha=np.zeros_like(fu)
                    ok=sent0&(fu>0)
                    alpha[ok]=np.minimum(1,ft[ok]/fu[ok])
                    accept=ok&(inp["accept_u"]<alpha)
                    expected=np.where(accept,ref-u,0)
                    close(cid+"/reflection_direct_density_reconstruction",tr["action"],expected,1e-14,1e-12)
                    close(cid+"/detailed_balance_flux",fu*alpha,np.minimum(fu,ft),1e-14,1e-12)
                    close(cid+"/next_event_squared_residual_symmetry",
                          ((lam*u-c)**2)[sent0],((lam*z-c)**2)[sent0],1e-12,1e-9)
                sq=(inp["x0"]-np.where(sent0,K*z,0))**2
                close(cid+"/true_mse",tr["mse"],sq)
                close(cid+"/true_damage",tr["damage_paired"],sq-clean_sq)
                # Independence of attack randomization justifies mean J=K²E a²,
                # not a per-sample identity. Check only the algebraic sample decomposition.
                close(cid+"/sample_damage_decomposition",tr["damage_paired"],
                      K*K*tr["action"]**2-2*K*tr["action"]*(inp["x0"]-K*u),1e-12,1e-9)
                p0=np.where(sent0,P*R/(P+R),P*(R+1/Z)/(P+R+1/Z))
                p1=A*A*p0+Q
                gain=p1/(p1+np.where(next_sent,R,R+1/Z))
                close(cid+"/silent_update_uses_code",tr["m1_post"],
                      A*K*z*sent0+gain*(np.where(next_sent,y,c)-A*K*z*sent0))
                # Separate posterior moment reconstruction using precision-product form.
                available=sent0&next_sent
                zz=np.where(sent0,z,0)
                center=quant(lam*zz,delta); d=lam*zz-center
                vt=1/(1/s+Z); mt=vt*d/s
                silent=np.sqrt(vt/s)*np.exp(-(d*d/s-mt*mt/vt)/2)
                probs=1-silent
                m1=(d-silent*mt)/probs
                m2=(s+d*d-silent*(vt+mt*mt))/probs
                m3=(d**3+3*d*s-silent*(mt**3+3*mt*vt))/probs
                m4=(d**4+6*d*d*s+3*s*s-silent*(mt**4+6*mt*mt*vt+3*vt*vt))/probs
                var=m2-m1*m1
                energy_var=m4-4*m1*m3+6*m1*m1*m2-3*m1**4-var*var
                r=y-center-m1
                f1=-np.sign(d)*r/np.sqrt(var)
                f2=(r*r-var)/np.sqrt(energy_var)
                close(cid+"/detector_from_records_only",tr["score"],np.where(available,f1+f2,0))
                for rho in cfg["audit_probabilities"]:
                    audit=inp["audit_u"]<rho
                    eligible=audit&available
                    alarm=eligible&(tr["score"]>tau)
                    row=next(r for r in rows if r["model"]==mid and float(r["delta"])==delta
                             and r["attack"]==attack and float(r["rho"])==rho)
                    close(cid+f"/rho{rho}/auth_count",float(row["auth_packets_random_audit"]),np.mean(audit&next_sent),0,0)
                    close(cid+f"/rho{rho}/base_packet_count",float(row["base_packets"]),
                          np.mean(sent0.astype(int)+next_sent.astype(int)),0,0)
                    check(cid+f"/rho{rho}/alarms",json.loads(row["per_episode_detection"])["events"]==int(alarm.sum()))
                    check(cid+f"/rho{rho}/eligible",json.loads(row["conditional_detection"])["trials"]==int(eligible.sum()))
                    for bsize in cfg["window_sizes"]:
                        cv=np.where(cal["available"]&(cal_inp["audit_u"]<rho),cal["score"],0)
                        cb=cv.reshape(-1,bsize).sum(axis=1)/np.sqrt(bsize)
                        wb_tau=np.sort(cb)[math.ceil(.99*(len(cb)+1))-1]
                        ab=np.where(eligible,tr["score"],0).reshape(-1,bsize).sum(axis=1)/np.sqrt(bsize)
                        wr=next(r for r in windows if r["model"]==mid and float(r["delta"])==delta
                                and r["attack"]==attack and float(r["rho"])==rho
                                and int(r["episodes_per_nonoverlap_block"])==bsize)
                        close(cid+f"/rho{rho}/window{bsize}/threshold",float(wr["threshold_healthy_calibration"]),wb_tau,0,0)
                        check(cid+f"/rho{rho}/window{bsize}/alarms",json.loads(wr["detection_rate"])["events"]==int((ab>wb_tau).sum()))
    status="PASS" if all(c["passed"] for c in checks) else "FAIL"
    result={"status":status,"checks":checks,"failed":[c for c in checks if not c["passed"]],
            "verification":"separate saved-array reconstruction; no import of experimental helpers",
            "random_samples_generated":False,"source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (RUN/"independent_array_audit.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n")
    print(json.dumps({"status":status,"checks":len(checks),"failed":result["failed"]},ensure_ascii=True))
    if status!="PASS": raise SystemExit(1)


if __name__=="__main__":
    main()
