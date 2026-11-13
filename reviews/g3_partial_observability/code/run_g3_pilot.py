"""Frozen G3 normal calibration and 24-seed Gate-A screen.

The accepted simulation modules remain read-only. No test-dependent retuning,
model sweep, extra detector, or changes to preregistered thresholds are used.
Gate B and confirm may run only after applicable prerequisites pass.
"""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "reviews/g3_partial_observability"
SIM = ROOT / "simulation"
sys.path.insert(0, str(SIM))
from calibration import Calibration
from engine import simulate
from g2_replay_runner import ReplaySelector
from model import Model, generate_data
from run_normal_eligibility import schedule_from_plan

METHODS = ("local", "raw_yang_no_cap", "cap_only", "cap_plus_zhou_random", "cap_plus_spatial_hard")
GATES = ("cap_plus_zhou_random", "cap_plus_spatial_hard")
RULES = ("fixed_lag8", "nearest_current_sender")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")


def csv_write(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def seeds(spec):
    return np.arange(spec["start"], spec["start"]+spec["count"])


def run_method(model, data, method, cap, calibration, controls, rule=None):
    x, y, ids, schedule = data
    actual = {"raw_yang_no_cap":"yang", "cap_only":"capped", "cap_plus_zhou_random":"zhou_random",
              "cap_plus_spatial_hard":"spatial_hard", "local":"local"}[method]
    edge = int(np.flatnonzero(np.all(model.edges == [0,1], axis=1))[0])
    selector = None if rule is None else ReplaySelector("fixed_lag8" if rule == "fixed_lag8" else "nearest_current", None, edge, model.cfg)
    return simulate(model, x, y, ids, actual, scenario="clean" if rule is None else "replay_selector",
        schedule=schedule, calibration=calibration if actual=="spatial_hard" else None,
        control=controls.get(method, 1.), cap=np.inf if method in {"local", "raw_yang_no_cap"} else cap,
        replay_selector=selector, collect=False)


def episode_counts(model, run):
    edge = int(np.flatnonzero(np.all(model.edges == [0,1], axis=1))[0])
    counts = []
    for i in range(len(run.sends)):
        events = np.flatnonzero(run.sends[i, :, 0])
        rejected = complete = 0
        for start, stop in zip(events[:-1], events[1:]):
            if start < model.cfg["warmup"]:
                continue
            complete += 1
            rejected += bool(np.any(run.weights[i, start:stop, edge] <= .5))
        counts.append((rejected, complete))
    return np.asarray(counts)


def calibrate_control(model, data, method, cap, fitted, calibration_log):
    # Freeze a broad logarithmic positive-control bracket from NORMAL data.
    # This is routine implementation of the already registered <=12 bisections.
    bounds = [-20., 20.]
    best = None
    for iteration in range(12):
        logcontrol = sum(bounds)/2
        control = float(2**logcontrol)
        run = run_method(model, data, method, cap, fitted, {method:control})
        counts = episode_counts(model, run)
        rate = float(counts[:,0].sum()/counts[:,1].sum())
        calibration_log.append({"method":method, "iteration":iteration,
            "log2_control":logcontrol, "control":control, "normal_episode_rejection_rate":rate,
            "complete_episodes":int(counts[:,1].sum())})
        candidate = (abs(rate-.05), control, rate)
        if best is None or candidate[0] < best[0]:
            best = candidate
        if abs(rate-.05) <= .005:
            return control, rate, True
        # Larger controls increase acceptance for both implemented mechanisms.
        if rate > .05:
            bounds[0] = logcontrol
        else:
            bounds[1] = logcontrol
    return best[1], best[2], False


def errors(run, x):
    return np.sum((run.estimates-x[:,:,None])**2, axis=-1)


def selector_packet_rows(model, run, ids, rule, method):
    rows = []
    for i, seed in enumerate(ids):
        for t in np.flatnonzero(run.sends[i,200:250,0])+200:
            source = int(run.replay_source[i,t])
            attempted = bool(run.injected[i,t])
            assert attempted and 0 <= source < t and run.sends[i,source,0]
            rows.append({"rule":rule,"method":method,"seed":int(seed),"tick":int(t),
                "replaced":attempted,"source_tick":source,"age":int(t-source),
                "source_was_actually_sent":True,
                "payload_changed":bool(np.any(run.estimates[i,source,0] != run.estimates[i,t,0]))})
    return rows


def analyze_gate_A(model, errors_by_key, bootstrap_ids, D, ids):
    raw, cap = "raw_yang_no_cap", "cap_only"
    mean_window = lambda err, a,b: err[:,a:b+1,1].mean(axis=1)
    clean = {m:mean_window(errors_by_key[m,"clean"],51,200) for m in METHODS}
    attack = {(m,r):mean_window(errors_by_key[m,r],201,250) for m in METHODS for r in RULES}
    attack_clean = {m:mean_window(errors_by_key[m,"clean"],201,250) for m in METHODS}
    recovery = {(m,r):mean_window(errors_by_key[m,r],251,300) for m in METHODS for r in RULES}
    recovery_clean = {m:mean_window(errors_by_key[m,"clean"],251,300) for m in METHODS}
    vectors = {"cap_clean_vs_raw":clean[cap]-clean[raw]}
    for r in RULES:
        vectors["cap_attack_excess__"+r] = attack[cap,r]-attack_clean[cap]
    for m in GATES:
        vectors[m+"__clean_vs_raw"] = clean[m]-clean[raw]
        vectors[m+"__clean_vs_cap"] = clean[m]-clean[cap]
        for r in RULES:
            vectors[m+"__attack_reduction_vs_cap__"+r] = attack[cap,r]-attack[m,r]
            vectors[m+"__attack_excess__"+r] = attack[m,r]-attack_clean[m]
            vectors[m+"__recovery_excess__"+r] = recovery[m,r]-recovery_clean[m]
    assert len(vectors) == 19
    denom = D[bootstrap_ids].mean(axis=1)
    alpha_tail = .05/(19*2)
    rows, values = [], {}
    for label, vector in vectors.items():
        stat = vector[bootstrap_ids].mean(axis=1)/denom
        lo, hi = np.quantile(stat,[alpha_tail,1-alpha_tail])
        value = {"statistic":label,"seed_count":len(ids),"mean_ratio":float(vector.mean()/D.mean()),
                 "simultaneous_ci_low":float(lo),"simultaneous_ci_high":float(hi),
                 "family_size":19,"per_interval_level":1-.05/19}
        values[label] = value
        rows.append(value)
    lower = lambda label,threshold: values[label]["simultaneous_ci_low"] >= threshold
    upper = lambda label,threshold: values[label]["simultaneous_ci_high"] <= threshold
    decisions = []
    for r in RULES:
        cap_cost = upper("cap_clean_vs_raw",.05)
        cap_pollution = lower("cap_attack_excess__"+r,.20)
        tradeoff = [m for m in GATES if lower(m+"__clean_vs_cap",.05) and lower(m+"__attack_reduction_vs_cap__"+r,.10)]
        coverage, failures = [], []
        for m in GATES:
            bounds = ((m+"__clean_vs_raw",.05),(m+"__attack_excess__"+r,.10),(m+"__recovery_excess__"+r,.10))
            if all(upper(label,target) for label,target in bounds):
                coverage.append(m)
            if any(values[label]["simultaneous_ci_low"] > target for label,target in bounds):
                failures.append(m)
        passed = cap_cost and cap_pollution and bool(tradeoff) and len(failures)==2 and not coverage
        decisions.append({"rule":r,"cap_clean_cost_upper_le_5pct":cap_cost,
            "cap_attack_excess_lower_ge_20pct":cap_pollution,"gates_with_proved_tradeoff":tradeoff,
            "gates_with_proved_failure":failures,"gates_covering_all_three_bounds":coverage,
            "gate_A_pilot_pass":bool(passed)})
    return rows, decisions


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--run-id", default="2026-11-13_g3_pilot_gate_a_r01")
    args=parser.parse_args()
    if Path(args.run_id).name != args.run_id:
        raise ValueError("One directory name required")
    out=BASE/"results"/args.run_id
    out.mkdir(parents=True,exist_ok=False)
    began=time.perf_counter()
    paths=[BASE/"plan.json",SIM/"model.py",SIM/"engine.py",SIM/"calibration.py",SIM/"g2_replay_runner.py",
        BASE/"code/run_normal_eligibility.py",ROOT/"simulation/g2_runs/2026-11-13_g2_replay_effectiveness_v3/config.json"]
    source_before={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
    write(out/"source_hashes_before.json",source_before)
    plan=json.loads(paths[0].read_text(encoding="utf-8"))
    write(out/"plan_snapshot.json",plan)
    eligible=json.loads((BASE/"results/2026-11-13_g3_normal_eligibility_r01/summary.json").read_text(encoding="utf-8"))
    assert eligible["normal_eligibility"][0]["normal_covariance_eligibility_passed"]
    # All exact counts/thresholds are copied from the frozen preregistration.
    fit_ids=seeds(plan["normal_calibration"]["fit_seeds"])
    threshold_ids=seeds(plan["normal_calibration"]["threshold_seeds"])
    pilot_ids=seeds(plan["future_splits"]["pilot"])
    assert len(fit_ids)==48 and len(threshold_ids)==48 and len(pilot_ids)==24
    write(out/"seeds.json",{"normal_fit":fit_ids.tolist(),"normal_threshold":threshold_ids.tolist(),"pilot":pilot_ids.tolist(),
        "diagnostic_train":pilot_ids[:12].tolist(),"diagnostic_screen":pilot_ids[12:].tolist(),"confirm":"not run"})
    write(out/"execution_config.json",{"run_id":args.run_id,"parent_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        "registered_before_data":True,"plan_sha256":sha(paths[0]),"bootstrap_repetitions":5000,
        "gate_A_family_size":19,"control_bisection_max_iterations":12,
        "control_bracket_log2":[-20,20],"control_target":.05,"control_tolerance":.005,
        "no_parameter_search":True,"no_new_detector":True,"confirm_gated_by_pilot":True})
    basecfg=json.loads(paths[-1].read_text(encoding="utf-8"))
    for k in ("N","n","T","A","Q","P0","R_variances","edges_sender_receiver","epsilon","warmup"):
        basecfg[k]=copy.deepcopy(plan["model"][k])
    metric_rows,packet_rows,normal_rows,all_gate_rows,decisions_by_geometry=[],[],[],[],[]
    for geometry,H in (("partial",plan["model"]["partial_H"]),("full_rank_reference",plan["model"]["full_rank_reference_H"])):
        folder=out/geometry;folder.mkdir()
        cfg=copy.deepcopy(basecfg);cfg["H_matrices"]=copy.deepcopy(H)
        write(folder/"config.json",cfg)
        model=Model.build(cfg)
        schedule=schedule_from_plan(cfg,plan)
        data={}
        for label,s in (("fit",fit_ids),("threshold",threshold_ids),("pilot",pilot_ids)):
            x,y=generate_data(model,s)
            sch=np.broadcast_to(schedule[None],(len(s),)+schedule.shape).copy()
            data[label]=(x,y,s,sch)
        fx,fy,fs,fsc=data["fit"]
        fitrun=simulate(model,fx,fy,fs,"yang",schedule=fsc,collect=True)
        cap=float(np.quantile(fitrun.cap_norms.ravel(),.995,method="higher"))
        # Scale fitting uses only the normal-fit split. Threshold split is
        # reserved for actual closed-loop episode-risk calibration.
        fitted=Calibration.fit(fitrun.observations,fitrun.observations,cfg,"pooled")
        fitted.save(folder/"normal_fit_calibration.npz")
        controls={};log=[];calibration_pass=True
        for method in GATES:
            control,rate,passed=calibrate_control(model,data["threshold"],method,cap,fitted,log)
            controls[method]=control
            calibration_pass &= passed
        csv_write(folder/"normal_control_bisection.csv",log)
        write(folder/"controls.json",{"cap":cap,"controls":controls,"normal_risk_calibration_passed":calibration_pass})
        if not calibration_pass:
            decisions_by_geometry.append({"geometry":geometry,"status":"STOP normal risk calibration not attained within fixed 12 iterations","gate_A":"not run","gate_B":"not run"})
            continue
        x,y,s,sch=data["pilot"]
        np.savez_compressed(folder/"pilot_inputs.npz",x=x,y=y,seeds=s,schedule=sch)
        runs={};err={};archive={}
        for method in METHODS:
            run=run_method(model,data["pilot"],method,cap,fitted,controls)
            runs[method,"clean"]=run;err[method,"clean"]=errors(run,x)
            counts=episode_counts(model,run) if method!="local" else np.zeros((len(s),2),int)
            for i,seed in enumerate(s):
                normal_rows.append({"geometry":geometry,"method":method,"seed":int(seed),
                    "complete_target_episodes":int(counts[i,1]),"rejected_target_episodes":int(counts[i,0]),
                    "receiver_normal_mse":float(err[method,"clean"][i,51:201,1].mean()),
                    "network_normal_mse":float(err[method,"clean"][i,51:201].mean()),
                    "target_clip_fraction":float(run.clipped[i,50:,0].mean()) if method!="local" else 0.})
        rng=np.random.default_rng(plan["inference"]["bootstrap_rng_seed"])
        indices=rng.integers(0,len(s),size=(5000,len(s)))
        D=err["raw_yang_no_cap","clean"][:,51:201,1].mean(axis=1)
        local=err["local","clean"][:,51:201,1].mean(axis=1)
        gain_boot=1-D[indices].mean(axis=1)/local[indices].mean(axis=1)
        gain_ci=np.quantile(gain_boot,[.025,.975])
        cooperation_pass=bool(gain_ci[0]>.10)
        if not cooperation_pass:
            decisions_by_geometry.append({"geometry":geometry,"status":"STOP normal cooperation lower CI did not exceed 10%","cooperation_gain_mean":float(1-D.mean()/local.mean()),"cooperation_ci":gain_ci.tolist(),"gate_A":"not run","gate_B":"not run"})
            continue
        for rule in RULES:
            for method in METHODS:
                run=runs[method,"clean"] if method=="local" else run_method(model,data["pilot"],method,cap,fitted,controls,rule)
                runs[method,rule]=run;err[method,rule]=errors(run,x)
                if method!="local":
                    assert np.array_equal(run.sends,sch)
                    packet_rows.extend({"geometry":geometry,**r} for r in selector_packet_rows(model,run,s,rule,method))
                for i,seed in enumerate(s):
                    clean_error=err[method,"clean"][i]
                    e=err[method,rule][i]
                    metric_rows.append({"geometry":geometry,"rule":rule,"method":method,"seed":int(seed),
                        "receiver_normal_mse":float(clean_error[51:201,1].mean()),
                        "receiver_attack_mse":float(e[201:251,1].mean()),
                        "receiver_attack_excess_mse":float((e-clean_error)[201:251,1].mean()),
                        "receiver_recovery_excess_mse":float((e-clean_error)[251:301,1].mean()),
                        "receiver_recovery_cumulative_excess":float((e-clean_error)[251:301,1].sum()),
                        "network_attack_mse":float(e[201:251].mean()),
                        "network_recovery_cumulative_excess":float((e-clean_error)[251:301].mean(axis=1).sum()),
                        "actual_replacements":int(run.injected[i].sum()) if method!="local" else 0,
                        "node_broadcasts":int(run.sends[i].sum()),"edge_messages":int(run.sends[i,:,model.edges[:,0]].sum()),
                        "payload_bytes":int(run.sends[i,:,model.edges[:,0]].sum()*16)})
        gate_rows,decisions=analyze_gate_A(model,err,indices,D,s)
        all_gate_rows.extend({"geometry":geometry,**r} for r in gate_rows)
        decisions_by_geometry.append({"geometry":geometry,"status":"Gate A pilot pass" if any(d["gate_A_pilot_pass"] for d in decisions) else "STOP Gate A pilot did not pass",
            "cooperation_gain_mean":float(1-D.mean()/local.mean()),"cooperation_ci":gain_ci.tolist(),"rules":decisions,
            "gate_B":"not run","confirm":"not run"})
        for (method,rule),run in runs.items():
            prefix=method+"__"+rule
            archive[prefix+"__estimates"]=run.estimates
            archive[prefix+"__sends"]=run.sends
            archive[prefix+"__weights"]=run.weights
            archive[prefix+"__injected"]=run.injected
            archive[prefix+"__replay_source"]=run.replay_source
            archive[prefix+"__clipped"]=run.clipped
        np.savez_compressed(folder/"pilot_trajectories.npz",**archive)
        # Reference cannot rescue partial-model failure; it is descriptive only.
    if metric_rows:csv_write(out/"per_seed_metrics.csv",metric_rows)
    if normal_rows:csv_write(out/"normal_episode_audit_per_seed.csv",normal_rows)
    if packet_rows:csv_write(out/"replay_packet_records.csv",packet_rows)
    if all_gate_rows:csv_write(out/"gate_A_simultaneous_intervals.csv",all_gate_rows)
    partial=decisions_by_geometry[0]
    write(out/"summary.json",{"run_id":args.run_id,"geometries":decisions_by_geometry,
        "partial_pilot_A_pass":partial["status"]=="Gate A pilot pass",
        "gate_B":"not run; only applicable after partial Gate A prerequisites pass",
        "confirm":"not run; only applicable after pilot prerequisites pass",
        "elapsed_seconds":time.perf_counter()-began,"no_test_retuning":True,
        "preregistered_plan_unchanged":True,"new_defense_developed":False})
    source_after={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
    assert source_before==source_after
    write(out/"source_hashes_after.json",source_after)
    write(out/"source_version.json",{"runner_sha256":sha(Path(__file__)),"numpy":np.__version__,"protected_sources_unchanged":True})
    write(out/"output_hashes.json",{p.relative_to(out).as_posix():sha(p) for p in sorted(out.rglob("*")) if p.is_file()})
    print(json.dumps(decisions_by_geometry,ensure_ascii=False))


if __name__=="__main__":
    main()
