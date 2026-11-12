"""Audit frozen sequential experiment outputs; no new estimator simulation."""
from __future__ import annotations
import argparse,csv,hashlib,json,shutil
from pathlib import Path
import numpy as np
from run_study import write_json


def rows(path):
    with Path(path).open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))


def phase(start,warmup):return 0 if start==0 else 1 if start<warmup else 2


def independent_scores(prefix,phase_id,e,stat,plan):
    m=prefix.shape[1];cs=0.;cp=np.zeros(m);cm=np.zeros(m);energies=[]
    results={k:[] for k in ("instant","mean","white_window","white_cusum","white_signed_cusum")}
    for L in range(1,len(prefix)+1):
        key=f"p{phase_id}_e{e}_l{L}_";mu=stat[key+"mean"];S=stat[key+"cov"]
        d=prefix[:L].reshape(-1)-mu
        residual=d[-m:]
        if L==1:conditional=residual;V=S
        else:
            coeff=np.linalg.solve(S[:-m,:-m],S[:-m,-m:]).T
            conditional=residual-coeff@d[:-m];V=S[-m:,-m:]-coeff@S[:-m,-m:]
        innovation=np.linalg.solve(np.linalg.cholesky(V),conditional)
        energy=float(innovation@innovation);energies.append(energy)
        cs=max(0,cs+energy-m)
        cp=np.maximum(0,cp+innovation-plan["signed_cusum_reference"])
        cm=np.maximum(0,cm-innovation-plan["signed_cusum_reference"])
        C=np.tile(np.eye(m),(1,L))/L;mean=C@d
        results["instant"].append(float(residual@np.linalg.solve(S[-m:,-m:],residual)))
        results["mean"].append(float(mean@np.linalg.solve(C@S@C.T,mean)))
        results["white_window"].append(float(sum(energies[-plan["window_length"]:])))
        results["white_cusum"].append(cs)
        results["white_signed_cusum"].append(float(max(cp.max(),cm.max())))
    return {k:np.asarray(v) for k,v in results.items()}


def main(folder):
    folder=Path(folder);plan=json.loads((folder/"plan.json").read_text(encoding="utf-8"))
    registration=json.loads((folder/"registration.json").read_text(encoding="utf-8"))
    # plan.json is a reformatted copy, so compare canonical objects with the saved plan hash source when available.
    plan_source=folder/"registered_plan_original.json"
    assert hashlib.sha256(plan_source.read_bytes()).hexdigest()==registration["plan_sha256"]
    assert json.loads(plan_source.read_text(encoding="utf-8-sig"))==plan
    source_count=0
    for filename,digest in registration["source_sha256"].items():
        assert hashlib.sha256((folder/"sources"/filename).read_bytes()).hexdigest()==digest;source_count+=1
    ranges=[]
    for v in plan["splits"].values():ranges.append(set(range(v["start"],v["start"]+v["count"])))
    for i,a in enumerate(ranges):
        for b in ranges[i+1:]:assert not a&b
    metrics=rows(folder/"per_seed_metrics.csv");index={(r["schedule"],r["edge_label"],r["method"],r["scenario"],int(r["seed"])):r for r in metrics}
    assert len(index)==len(metrics)
    expected=len(plan["schedules"])*len(plan["attack_edges"])*len(plan["methods"])*len(plan["scenarios"])
    checks=0;replays=0;max_metric_error=0.;max_stat_error=0.;max_weight_error=0.;episode_checks=0
    for schedule_name in plan["schedules"]:
        sub=folder/schedule_name;cfg=json.loads((sub/"config.json").read_text(encoding="utf-8"))
        A=np.asarray(cfg["A"]);H=np.asarray(cfg["H_matrices"]);edges=np.asarray(cfg["edges_sender_receiver"])
        with np.load(sub/"test_inputs.npz") as inp:x,y,seeds,schedule=(inp[k] for k in ("x","y","seeds","schedule"))
        assert set(map(int,seeds))==ranges[-1]
        controls=json.loads((sub/"frozen_controls.json").read_text(encoding="utf-8"))
        statistics=np.load(sub/"phase_statistics.npz")
        for edge_label,attackedge in plan["attack_edges"].items():
            path=sub/edge_label;sender,receiver=attackedge
            for method in plan["methods"]:
                for scenario in plan["scenarios"]:
                    with np.load(path/(method+"__"+scenario+".npz")) as saved:
                        estimate,weights=saved["estimates"],saved["weights"]
                        assert np.isfinite(estimate).all() and np.all((weights>=0)&(weights<=1))
                        if method!="local":assert np.array_equal(saved["sends"],schedule)
                        else:assert not saved["sends"].any()
                        a=cfg["attack"];start,end=a["start"]+1,a["end_inclusive"]+2
                        error=np.sum((estimate-x[:,:,None,:])**2,axis=-1)
                        recomputed={"mse_attack_window":error[:,start:end].mean(axis=(1,2)),"receiver_attack_mse":error[:,start:end,receiver].mean(axis=1),
                                    "mse_all":error[:,cfg["warmup"]+1:].mean(axis=(1,2))}
                        for name,value in recomputed.items():
                            recorded=np.array([float(index[schedule_name,edge_label,method,scenario,int(seed)][name]) for seed in seeds])
                            delta=float(np.max(np.abs(value-recorded)));max_metric_error=max(max_metric_error,delta);assert delta<1e-12
                        if scenario=="clean":assert not saved["injected"].any()
                        for s,t in zip(*np.where(saved["injected"])):
                            assert a["start"]<=t<=a["end_inclusive"] and saved["sends"][s,t,sender]
                            if scenario=="replay_matched":
                                old=saved["replay_source"][s,t];assert old>=0 and saved["sends"][s,old,sender] and t-old==80;replays+=1
                        checks+=1
                        if scenario=="clean" and edge_label=="primary" and method not in {"local","age_only"}:
                            er=rows(path/(method+"__clean_episodes.csv"))
                            # Independent Schur-complement recomputation for first three trajectories,
                            # all edges and all lifecycle phases, including right-censored episodes.
                            for ep in er:
                                s=int(ep["trajectory"])
                                if s>=3:continue
                                e,t,L=int(ep["edge"]),int(ep["start"]),int(ep["length"])
                                j,i=edges[e];r=np.stack([y[s,t+age,i]-H[i]@np.linalg.matrix_power(A,age)@estimate[s,t,j] for age in range(L)])
                                p=phase(t,cfg["warmup"]);sc=independent_scores(r,p,e,statistics,plan)[method]
                                ratio=sc/statistics["threshold_"+method][p,e]
                                stored=float(ep["maximum_ratio"]);diff=abs(float(ratio.max())-stored);max_stat_error=max(max_stat_error,diff);assert diff<1e-8
                                alarm=np.maximum.accumulate(ratio>controls["multipliers"][method][p])
                                expected_weight=(~alarm)*np.exp(-np.log(2)*np.arange(L)/controls["half_life"])
                                wd=float(np.max(np.abs(expected_weight-weights[s,t:t+L,e])));max_weight_error=max(max_weight_error,wd);assert wd<5e-8
                                assert bool(alarm[-1])==(ep["alarm"]=="True")
                                episode_checks+=1
        statistics.close()
    assert checks==expected and len(metrics)==expected*len(seeds)
    result={"passed":True,"cases":checks,"metric_rows":len(metrics),"independent_test_seeds":len(seeds),"split_ranges_disjoint":True,"registered_plan_hash_matches":True,
            "source_hashes_verified":source_count,"mse_recompute_max_error":max_metric_error,"legal_replay_packets":replays,
            "independent_schur_episode_checks":episode_checks,"maximum_statistic_error":max_stat_error,"maximum_weight_error":max_weight_error,
            "no_new_estimator_simulations":True}
    write_json(folder/"output_audit.json",result);post=folder/"post_analysis_sources";post.mkdir(exist_ok=True)
    shutil.copy2(__file__,post/Path(__file__).name);print(json.dumps(result))


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("folder");a=p.parse_args();main(a.folder)
