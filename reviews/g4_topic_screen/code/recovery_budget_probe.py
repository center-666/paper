"""Small exhaustive communication-action screen; no new detector or recovery rule.

Only eight already-existing G2 seeds are reused. Enumerated controls share every
random input and attack before tick 250. Oracle choices use offline truth and are
explicitly not implementable policies. New packets contain current, possibly
polluted, sender estimates. No cache/state resetting or authentic-payload oracle.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import subprocess
import sys
import time
import traceback
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "reviews/g4_topic_screen"
SOURCE = ROOT / "simulation/g2_runs/2026-11-13_g2_replay_effectiveness_v3"
sys.path.insert(0, str(ROOT / "simulation"))
from calibration import Calibration
from engine import simulate
from g2_replay_runner import ReplaySelector, repeated_schedule
from model import Model


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8", newline="\n")


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def return_to_tolerance(err, clean, origin=251, tolerance=.1, streak=5):
    durations = np.full(err.shape[:-1], err.shape[-1]-origin, int)
    censored = np.ones(err.shape[:-1], bool)
    for t in range(origin, err.shape[-1]-streak+1):
        qualifies = np.all(np.sqrt(err[..., t:t+streak]) <= np.sqrt(clean[..., t:t+streak])+tolerance, axis=-1)
        hit = qualifies & censored
        durations[hit] = t-origin
        censored[hit] = False
    return durations, censored


def main(out):
    if out.exists():
        raise FileExistsError(out)
    out.mkdir(parents=True)
    started = time.perf_counter()
    cfg = json.loads((SOURCE / "config.json").read_text(encoding="utf-8"))
    controls = json.loads((SOURCE / "controls.json").read_text(encoding="utf-8"))
    model = Model.build(cfg)
    with np.load(SOURCE / "test_inputs.npz") as f:
        seeds, x, y = f["seeds"][:8].astype(int), f["x"][:8].copy(), f["y"][:8].copy()
        common = f["schedule"][0].astype(bool)
        assert np.all(f["schedule"][:8] == common)
    assert np.array_equal(common, repeated_schedule(cfg, 1, cfg["cache_schedule_pattern"], cfg["cache_schedule_phase"])[0])
    slots = [(t,j) for t in (250,254,258) for j in range(cfg["N"]) if not common[t,j]]
    actions = [()]+[(a,) for a in slots]+list(itertools.combinations(slots, 2))
    assert len(slots)==11 and len(actions)==67
    S, C = len(seeds), len(actions)
    schedules = np.broadcast_to(common, (C,S)+common.shape).copy()
    for c, action in enumerate(actions):
        for t,j in action:
            schedules[c,:,t,j] = True
    budgets = np.array([len(a) for a in actions])
    assert np.all(schedules[:,:,:250] == common[None,None,:250])
    fixed_action = ((254,0),(258,0))
    fixed = actions.index(fixed_action)
    two = np.flatnonzero(budgets==2)
    random_ids = np.array([np.random.default_rng(np.random.SeedSequence([int(s),0x473442])).choice(two) for s in seeds])
    source_paths = list(SOURCE.iterdir()) + [ROOT / "simulation" / n for n in ("engine.py","model.py","calibration.py","g2_replay_runner.py")]
    hashes_before = {p.relative_to(ROOT).as_posix(): sha(p) for p in source_paths if p.is_file()}
    prereg = {"run_id": out.name, "baseline_commit": subprocess.check_output(["git","rev-parse","HEAD"], cwd=ROOT,text=True).strip(),
        "registered_before_trajectories": True, "source_run": SOURCE.name,
        "purpose": "Limited recovery-value exploration; not independent confirmation or a new defense algorithm",
        "seeds": seeds.tolist(), "seed_selection": "first eight existing G2 test seeds; already seen, exploratory only",
        "methods": ["raw_yang","cap_only","spatial_hard","zhou_random"],
        "attack_rules": ["fixed_lag8","nearest_current"],
        "known_stop": 249, "first_extra_tick":250, "extra_action_slots":slots,
        "allowed_schedule_count":C, "budget":"at most two EXTRA node broadcasts within these 11 slots; each node has two outgoing edges, 32 payload bytes/broadcast",
        "fixed_frequency_action":fixed_action, "random_seeded_action_ids":random_ids.tolist(),
        "oracle":"exact enumeration in the declared finite action set only; includes empty action; per-seed future true errors permitted ONLY for offline upper envelope",
        "not_global_upper_bound":"Does not upper-bound all schedules/times, budgets>2, changing gains, or new secure messages",
        "primary_loss":"network cumulative squared error, states251..300; receiver cumulative squared error separately",
        "normal_mistrigger_cost":"same extra action applied once to same-seed CLEAN run at tick250; conditional on false activation, no false-activation probability assumed",
        "recovery":"first five states from251 with attacked norm <= passive healthy norm+0.1; finite horizon/right censoring; not permanent recovery",
        "go_threshold":"Exploratory only: on BOTH frozen Replay rules, network-oracle relative reduction >=10% in at least one strong capped baseline, and predeclared fixed or uniform-random mean network gain >=5% with conditional clean cumulative cost <=2%; otherwise do not develop a residual scheduler this round",
        "comparability":"same pre-250 noise/packets/actual attack counts; new sends after250 contain actual polluted states; frozen nominal gains/cap/controls; report shifted normal risk",
        "numerical_tolerance":1e-10,
        "not_executed":"No RL, parameter sweep, new detector, trusted-state reset or receiver-private information in attack selector"}
    write_json(out / "preregistration.json", prereg)
    write_json(out / "config.json", cfg)
    write_json(out / "source_hashes_before.json", hashes_before)
    write_json(out / "actions.json", {"actions":[{"id":c,"extra_broadcasts":a,"extra_payload_bytes":32*len(a)} for c,a in enumerate(actions)]})
    cal = Calibration.load(SOURCE / "interval_scale_calibration.npz")
    expanded_x = np.tile(x,(C,1,1))
    expanded_y = np.tile(y,(C,1,1,1))
    expanded_seeds = np.tile(seeds,C)
    flat_schedule = schedules.reshape(C*S, cfg["T"],cfg["N"])
    edge = int(np.flatnonzero(np.all(model.edges == [0,1],axis=1))[0])
    method_args = {
        "raw_yang":("yang",None,1.,np.inf),
        "cap_only":("capped",None,1.,controls["cap"]),
        "spatial_hard":("spatial_hard",cal,controls["spatial_hard"],controls["cap"]),
        "zhou_random":("zhou_random",None,controls["zhou_random"],controls["cap"])}
    all_rows, summaries, passive_checks = [], [], []
    timeline = {"seeds":seeds,"action_budgets":budgets}
    for label,(method,fit,control,cap) in method_args.items():
        losses = {}
        for selector in ("clean","fixed_lag8","nearest_current"):
            policy = None if selector=="clean" else ReplaySelector(selector,None,edge,cfg)
            run = simulate(model, expanded_x, expanded_y, expanded_seeds, method,
                scenario="clean" if policy is None else "replay_selector", schedule=flat_schedule,
                calibration=fit,control=control,cap=cap,collect=False,replay_selector=policy)
            assert np.array_equal(run.sends,flat_schedule)
            estimate = run.estimates.reshape(C,S,cfg["T"]+1,cfg["N"],cfg["n"])
            assert np.max(np.abs(estimate[:,:,:251]-estimate[0,None,:,:251])) < 1e-10
            err = np.sum((estimate-x[None,:,:,None,:])**2,axis=-1)
            recv, net = err[:,:,:,1], err.mean(axis=-1)
            rec_loss = recv[:,:,251:301].sum(axis=-1)
            net_loss = net[:,:,251:301].sum(axis=-1)
            inj = run.injected.reshape(C,S,cfg["T"])
            assert np.all(inj==inj[0,None])
            if selector!="clean":
                assert np.all(inj.sum(axis=-1)==14)
                assert not inj[:,:,250:].any()
            timelines = {"receiver":recv,"network":net}
            timeline[label+"__"+selector+"__receiver_error_sq"] = recv[:,:,250:]
            timeline[label+"__"+selector+"__network_error_sq"] = net[:,:,250:]
            # Reconstruct saved immutable G2 passive result as an independent checkpoint.
            label_old = {"raw_yang":"raw_yang_no_cap","cap_only":"cap_only","spatial_hard":"spatial_hard","zhou_random":"zhou_random_protection"}[label]
            if selector!="clean":
                with np.load(SOURCE / "mse_timeline_per_seed.npz") as old:
                    old_selector = "nearest_current_sender" if selector=="nearest_current" else selector
                    expected = old[old_selector+"__"+label_old+"__receiver_error_sq"][:8]
                max_error=float(np.max(np.abs(recv[0]-expected)))
                assert max_error<=1e-10
                passive_checks.append({"method":label,"selector":selector,"passive_vs_archived_max_error":max_error})
            losses[selector] = (rec_loss, net_loss, timelines)
            print(json.dumps({"method":label,"selector":selector,"actions":C,"seeds":S,"finished":True}),flush=True)
        clean_r, clean_n, clean_time = losses["clean"]
        for selector in ("fixed_lag8","nearest_current"):
            rloss,nloss,times = losses[selector]
            returns,censored = return_to_tolerance(times["receiver"],clean_time["receiver"][0,None])
            selected = {
                "passive":np.zeros(S,int), "fixed_frequency_2":np.full(S,fixed,int),
                "random_seeded_2":random_ids,
                "oracle_network_at_most_2":np.argmin(nloss,axis=0),
                "oracle_receiver_at_most_2":np.argmin(rloss,axis=0),
                "oracle_network_exactly_2":two[np.argmin(nloss[two],axis=0)],
                "best_fixed_in_sample_network_2":np.full(S,two[np.argmin(nloss[two].mean(axis=1))],int)}
            for c, action in enumerate(actions):
                for s,seed in enumerate(seeds):
                    all_rows.append({"method":label,"selector":selector,"seed":int(seed),"action_id":c,
                        "extra_broadcasts":len(action),"extra_edge_messages":2*len(action),"extra_payload_bytes":32*len(action),
                        "receiver_cumulative_mse":float(rloss[c,s]),"network_cumulative_mse":float(nloss[c,s]),
                        "receiver_excess_vs_passive_healthy":float(rloss[c,s]-clean_r[0,s]),
                        "network_excess_vs_passive_healthy":float(nloss[c,s]-clean_n[0,s]),
                        "clean_receiver_cost":float(clean_r[c,s]-clean_r[0,s]),
                        "clean_network_cost":float(clean_n[c,s]-clean_n[0,s]),
                        "first_tolerance_return_steps":int(returns[c,s]),"return_right_censored":bool(censored[c,s]),
                        "attacks":14})
            for name,ids in selected.items():
                idx=np.arange(S)
                for s,seed in enumerate(seeds):
                    c=int(ids[s]); a=actions[c]
                    summaries.append({"method":label,"selector":selector,"policy":name,"seed":int(seed),
                        "action_id":c,"extra_broadcasts":len(a),"extra_payload_bytes":32*len(a),
                        "receiver_cumulative_mse":float(rloss[c,s]),"network_cumulative_mse":float(nloss[c,s]),
                        "receiver_reduction_vs_passive":float(rloss[0,s]-rloss[c,s]),
                        "network_reduction_vs_passive":float(nloss[0,s]-nloss[c,s]),
                        "normal_false_activation_receiver_cost":float(clean_r[c,s]-clean_r[0,s]),
                        "normal_false_activation_network_cost":float(clean_n[c,s]-clean_n[0,s]),
                        "receiver_passive_healthy_loss":float(clean_r[0,s]),"network_passive_healthy_loss":float(clean_n[0,s]),
                        "first_tolerance_return_steps":float(returns[c,s]),"return_right_censored":float(censored[c,s]),
                        "deployable":name in {"passive","fixed_frequency_2","random_seeded_2"}})
            for s,seed in enumerate(seeds):
                summaries.append({"method":label,"selector":selector,"policy":"uniform_random_2_exact_expectation","seed":int(seed),
                    "action_id":-1,"extra_broadcasts":2,"extra_payload_bytes":64,
                    "receiver_cumulative_mse":float(rloss[two,s].mean()),"network_cumulative_mse":float(nloss[two,s].mean()),
                    "receiver_reduction_vs_passive":float(rloss[0,s]-rloss[two,s].mean()),
                    "network_reduction_vs_passive":float(nloss[0,s]-nloss[two,s].mean()),
                    "normal_false_activation_receiver_cost":float((clean_r[two,s]-clean_r[0,s]).mean()),
                    "normal_false_activation_network_cost":float((clean_n[two,s]-clean_n[0,s]).mean()),
                    "receiver_passive_healthy_loss":float(clean_r[0,s]),"network_passive_healthy_loss":float(clean_n[0,s]),
                    "first_tolerance_return_steps":float(returns[two,s].mean()),"return_right_censored":float(censored[two,s].mean()),
                    "deployable":True})
    write_csv(out / "all_schedule_seed_metrics.csv",all_rows)
    write_csv(out / "selected_policy_seed_metrics.csv",summaries)
    write_csv(out / "passive_archive_checks.csv",passive_checks)
    np.savez_compressed(out / "recovery_timelines.npz",**timeline)
    write_json(out / "source_hashes_after.json",{p:sha(ROOT/p) for p in hashes_before})
    assert hashes_before=={p:sha(ROOT/p) for p in hashes_before}
    write_json(out / "summary.json",{"run_id":out.name,"completed":True,"elapsed_seconds":time.perf_counter()-started,
        "independent_seed_count":S,"allowed_action_count":C,"methods":list(method_args),
        "passive_archive_max_error":max(r["passive_vs_archived_max_error"] for r in passive_checks),
        "source_immutable":True,"raw_schedule_rows":len(all_rows),"selected_policy_rows":len(summaries),
        "claim":"exploratory restricted-grid oracle envelope; no new scheduler, no confidence or publication claim"})
    write_json(out / "provenance.json",{"source_sha256":sha(Path(__file__)),"numpy":np.__version__,"python":sys.version})
    write_json(out / "output_hashes.json",{p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file()})


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--run-id",default="2026-11-13_g4_recovery_budget_r01")
    arg=parser.parse_args()
    if Path(arg.run_id).name!=arg.run_id:
        raise ValueError("Run ID must be a single directory name")
    target=BASE / "results" / arg.run_id
    try:
        main(target)
    except Exception:
        if target.exists():
            (target/"failure.txt").write_text(traceback.format_exc(),encoding="utf-8",newline="\n")
        raise
