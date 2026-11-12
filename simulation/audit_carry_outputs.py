"""Independent stored-output checks for the cross-message CUSUM comparator."""
from __future__ import annotations
import argparse,csv,hashlib,json,shutil
from pathlib import Path
import numpy as np
from scipy import stats
from run_study import write_json


def read(path):
    with Path(path).open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))


def main(folder):
    folder=Path(folder);plan=json.loads((folder/"plan.json").read_text(encoding="utf-8"));registration=json.loads((folder/"registration.json").read_text(encoding="utf-8"))
    assert hashlib.sha256((folder/"registered_plan_original.json").read_bytes()).hexdigest()==registration["plan_sha256"]
    for name,digest in registration["source_sha256"].items():assert hashlib.sha256((folder/"sources"/name).read_bytes()).hexdigest()==digest
    rr=read(folder/"per_seed_metrics.csv");idx={(r["schedule"],r["edge_label"],r["method"],r["scenario"],int(r["seed"])):r for r in rr};assert len(idx)==len(rr)
    primary=read(folder/"primary_tests.csv");checks=0;max_mse=0.;max_weight=0.;independent_updates=0
    for schedule_name in plan["schedules"]:
        sub=folder/schedule_name;cfg=json.loads((sub/"config.json").read_text(encoding="utf-8"));A=np.array(cfg["A"]);H=np.array(cfg["H_matrices"]);edges=np.array(cfg["edges_sender_receiver"])
        controls=json.loads((sub/"controls.json").read_text(encoding="utf-8"))
        with np.load(sub/"test_inputs.npz") as data:x,y,seeds,schedule=(data[k] for k in ("x","y","seeds","schedule"))
        assert np.array_equal(seeds,np.arange(plan["test_seeds"]["start"],plan["test_seeds"]["start"]+plan["test_seeds"]["count"]))
        with np.load(Path(plan["source_run"])/schedule_name/"phase_statistics.npz") as statistics:
            for edge_label,(sender,receiver) in plan["attack_edges"].items():
                for method in plan["methods"]:
                    for scenario in plan["scenarios"]:
                        with np.load(sub/edge_label/(method+"__"+scenario+".npz")) as f:
                            hat=f["estimates"];weight=f["weights"]
                            assert np.array_equal(f["sends"],schedule)
                            assert np.isfinite(hat).all() and np.all((weight>=0)&(weight<=1))
                            a=cfg["attack"];start,end=a["start"]+1,a["end_inclusive"]+2
                            e=np.sum((hat-x[:,:,None,:])**2,axis=-1)
                            for key,value in (("mse_attack_window",e[:,start:end].mean(axis=(1,2))),("receiver_attack_mse",e[:,start:end,receiver].mean(axis=1))):
                                saved=np.array([float(idx[schedule_name,edge_label,method,scenario,int(s)][key]) for s in seeds]);err=float(np.max(np.abs(saved-value)));assert err<1e-12;max_mse=max(max_mse,err)
                            if scenario=="clean":assert not f["injected"].any()
                            for s,t in zip(*np.where(f["injected"])):assert a["start"]<=t<=a["end_inclusive"] and schedule[s,t,sender]
                            checks+=1
                            if scenario=="clean" and edge_label=="primary" and method.startswith("carry"):
                                detector="white_cusum" if method=="carry_energy_cusum" else "white_signed_cusum"
                                for trial in range(3):
                                    for edge,(j,i) in enumerate(edges):
                                        cs=0.;cp=np.zeros(cfg["n"]);cm=cp.copy();last=-1;bad=False;prefix=[]
                                        for t in range(cfg["T"]):
                                            if schedule[trial,t,j]:last=t;bad=False;prefix=[]
                                            age=t-last;L=age+1;phase=0 if last==0 else 1 if last<cfg["warmup"] else 2
                                            prefix.append(y[trial,t,i]-H[i]@np.linalg.matrix_power(A,age)@hat[trial,last,j])
                                            name=f"p{phase}_e{edge}_l{L}_";mu=statistics[name+"mean"];S=statistics[name+"cov"];d=np.asarray(prefix).reshape(-1)-mu;m=cfg["n"]
                                            if L==1:innovation=np.linalg.solve(np.linalg.cholesky(S),d)
                                            else:
                                                coeff=np.linalg.solve(S[:-m,:-m],S[:-m,-m:]).T;V=S[-m:,-m:]-coeff@S[:-m,-m:]
                                                innovation=np.linalg.solve(np.linalg.cholesky(V),d[-m:]-coeff@d[:-m])
                                            cs=max(0,cs+float(innovation@innovation)-m);cp=np.maximum(0,cp+innovation-.5);cm=np.maximum(0,cm-innovation-.5)
                                            score=cs if detector=="white_cusum" else max(cp.max(),cm.max())
                                            alarm=score>statistics["threshold_"+detector][phase,edge]*controls["multipliers"][method][phase]
                                            if alarm:bad=True;cs=0.;cp[:]=0;cm[:]=0
                                            expected=(0 if bad else 1)*np.exp(-np.log(2)*age/controls["half_life"])
                                            diff=abs(expected-weight[trial,t,edge]);max_weight=max(max_weight,float(diff));assert diff<5e-8;independent_updates+=1
        for row in primary:
            if row["schedule"]!=schedule_name:continue
            candidate=np.array([float(idx[schedule_name,"primary","mean","step",int(s)]["receiver_attack_mse"]) for s in seeds])
            baseline=np.array([float(idx[schedule_name,"primary",row["baseline"],"step",int(s)]["receiver_attack_mse"]) for s in seeds])
            p=float(stats.ttest_1samp(candidate-.99*baseline,0,alternative="less").pvalue)
            assert abs(p-float(row["practical_p"]))<1e-12
    result={"passed":True,"cases":checks,"metric_rows":len(rr),"mse_recompute_error":max_mse,"independent_carry_updates_checked":independent_updates,
        "online_weight_max_error":max_weight,"primary_practical_tests_recomputed":len(primary),"source_plan_hashes_match":True,"new_simulations":False}
    write_json(folder/"output_audit.json",result);dest=folder/"post_analysis_sources";dest.mkdir(exist_ok=True);shutil.copy2(__file__,dest/Path(__file__).name)
    print(json.dumps(result))


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("folder");a=p.parse_args();main(a.folder)
