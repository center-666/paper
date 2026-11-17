"""Task 1: independent CSV re-audit and deterministic formula fixtures.
No simulator, model builder, NPZ trajectory, RNG, optimizer or calibration is used.
python -B reviews/g1_communication_behavior/task1/code/task1_formula_checks.py
python -B reviews/g1_communication_behavior/task1/code/task1_formula_checks.py --verify
"""
from __future__ import annotations
import argparse
import ast
import csv
import hashlib
import io
import itertools
import json
import subprocess
from collections import Counter
from pathlib import Path
import numpy as np

OUT = Path(__file__).resolve().parents[1]
ROOT = OUT.parents[2]
OLD = OUT.parent / "task0_5"
HIST = OUT / "evidence/historical_five_node_v2"
ATOL = 1e-12
BASELINE = "0b50349bd8dcf00195fae9639ee65260251b23ae"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))


def csv_rows(p):
    with Path(p).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def text_json(x):
    return json.dumps(x, ensure_ascii=False, indent=2, allow_nan=False) + "\n"


def csv_text(rows):
    f = io.StringIO(newline="")
    w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return f.getvalue()


def git_state(path):
    def get(*args):
        return subprocess.check_output(["git", "-C", str(path), *args], stderr=subprocess.DEVNULL)
    return (get("rev-parse", "HEAD"), sha_bytes(get("diff", "--binary")), sha_bytes(get("diff", "--cached", "--binary")))


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def require(b, s):
    if not b:
        raise AssertionError(s)


def hist(vals):
    return {str(k): int(v) for k, v in sorted(Counter(vals).items())}


def sources_and_parameters():
    cfg = read_json(HIST / "config.json")
    env = read_json(HIST / "environment.json")
    wanted = {"N": 5, "n": 2, "T": 400, "A": [[1.01, 0.], [0., 1.01]],
              "Q": [[.02, 0.], [0., .02]], "P0": [[1., 0.], [0., 1.]],
              "H_scales": [1., .8, 1.2, .9, 1.1], "R_variances": [.05]*5,
              "epsilon": .08, "send_delta_squared": .12, "max_interval": 10,
              "edges_sender_receiver": [[0,1],[1,0],[1,2],[2,1],[2,3],[3,2],[3,4],[4,3],[4,0],[0,4]]}
    require(all(cfg[k] == v for k, v in wanted.items()), "Historical parameters not frozen Task1 values")
    src = {}
    for n in ["engine.py", "model.py", "run_study.py"]:
        src[n] = sha(HIST/"sources"/n)
        require(src[n] == env["source_sha256"][n], "Historical source SHA mismatch " + n)
    sums = (OLD/"SHA256SUMS.txt").read_text(encoding="utf-8").splitlines()
    for line in sums:
        expected, rel = line.split("  ", 1)
        require(sha(OLD/rel) == expected, "Task0.5 artifact changed " + rel)
    return cfg, {"model": wanted, "config_sha256": sha(HIST/"config.json"),
                 "historical_source_sha256": src, "Task0_5_manifest_entries_verified": len(sums),
                 "task1_single_replay_definition": "one true opportunity 0->1; genuine previous raw sender packet; r/s policy remains unfrozen",
                 "historical_multi_replay_window_not_adopted_as_Task1_protocol": cfg["attack"]}


def reaudit_csv(cfg):
    rows = csv_rows(OLD/"03_seed_level_metrics.csv")
    require([int(r["seed"]) for r in rows] == list(range(40000, 40032)), "Seed order mismatch")
    seeds = {}
    for r in rows:
        seed = int(r["seed"])
        c, a = int(r["node1_clean_send_count"]), int(r["node1_replay_send_count"])
        diff = a-c
        require(diff == int(r["node1_send_count_difference"]), "03 count difference mismatch")
        require(diff == int(r["node1_added_sends"])-int(r["node1_missing_sends"]), "03 event count mismatch")
        first, second, k = map(int, [r["first_replay_time"], r["second_replay_time"], r["first_node1_divergence_time"]])
        require(first < second and k > first and k-first == int(r["first_node1_divergence_delay"]), "03 timing mismatch")
        require((k <= second) == (r["first_node1_event_before_second_replay_update"] == "True"), "03 second-injection cutoff")
        seeds[seed] = {"seed":seed, "clean_sends":c, "replay_sends":a, "count_difference":diff,
                       "first_replay":first, "second_replay":second, "first_node1_divergence":k,
                       "delay":k-first, "strictly_before_second":k<second,
                       "same_tick_as_second_before_payload_replacement":k==second,
                       "before_second_update":k<=second, "node1_first_cause_from_03":r["first_node1_cause"],
                       "node1_total_different_ticks_from_03":int(r["node1_different_event_ticks"]),
                       "first_step_event_changed_from_03":r["first_step_event_changed"] == "True"}
    cause_names = ["Threshold-flag-only", "Timeout-flag-only", "Both-flags-changed"]
    causes = {s: Counter() for s in seeds}
    flips = {s: Counter() for s in seeds}
    first_causes = {}
    events = csv_rows(OLD/"04_event_reconstruction.csv")
    require(len(events) == 32*400*5, "04 event row count")
    seen = set()
    for e in events:
        if int(e["node"]) != 1:
            continue
        seed, t = int(e["seed"]), int(e["time"])
        require((seed,t) not in seen, "Duplicate 04 seed/time")
        seen.add((seed,t))
        csend, asend = int(e["clean_send"]), int(e["replay_send"])
        ct, at, cu, au = [e[f] == "True" for f in ["clean_threshold","replay_threshold","clean_timeout","replay_timeout"]]
        require(csend == int(t == 0 or ct or cu) and asend == int(t == 0 or at or au), "04 OR disagreement")
        dc, du = ct != at, cu != au
        flips[seed]["threshold_flag_changed"] += dc
        flips[seed]["timeout_flag_changed"] += du
        diff = asend-csend
        require(diff == int(e["event_difference"]), "04 difference mismatch")
        if diff:
            key = "Both-flags-changed" if dc and du else "Threshold-flag-only" if dc else "Timeout-flag-only" if du else "INVALID"
            require(key == e["difference_cause_flags"] and key != "INVALID", "04 cause label disagreement")
            causes[seed][key] += 1
            if seed not in first_causes or t < first_causes[seed][0]:
                first_causes[seed] = (t,key)
    for r in rows:
        s = int(r["seed"])
        require(sum(causes[s].values()) == seeds[s]["node1_total_different_ticks_from_03"], "03 vs 04 totals")
        require(first_causes[s] == (seeds[s]["first_node1_divergence"],r["first_node1_cause"]), "03 vs04 first")
        for key in cause_names:
            seeds[s]["event_cause_"+key] = causes[s][key]
        seeds[s].update({key: int(flips[s][key]) for key in ["threshold_flag_changed","timeout_flag_changed"]})
    A = np.asarray(cfg["A"]); eps = cfg["epsilon"]; theta = cfg["send_delta_squared"]
    first_info = read_json(OLD/"01_data_integrity_audit.json")["summary"]["first_replay"]["all_rows"]
    by_seed = {int(r["seed"]):r for r in first_info}
    margins = csv_rows(OLD/"05_trigger_margin_analysis.csv")
    selected = {int(r["seed"]):r for r in margins if int(r["time"]) == seeds[int(r["seed"])]["first_replay"]+1}
    require(len(selected)==32, "Need 32 stored first-Replay rows")
    formula_rows = []
    for seed, row in sorted(seeds.items()):
        e, old = selected[seed], by_seed[seed]
        clean_hat = np.array([float(e[f"clean_hat_{i}"]) for i in range(2)])
        attack_hat = np.array([float(e[f"replay_hat_{i}"]) for i in range(2)])
        cm = np.array([float(e[f"clean_reference_{i}"]) for i in range(2)])
        am = np.array([float(e[f"replay_reference_{i}"]) for i in range(2)])
        require(np.array_equal(cm,am), "First references unequal")
        delta = np.asarray(old["delta"])
        predicted = eps*A@delta
        observed = attack_hat-clean_hat
        e0 = clean_hat-cm
        dg_pred = float(2*e0@predicted + predicted@predicted)
        # independently recompute distances from saved vectors, not saved aggregate errors
        dg_obs = float(np.sum((attack_hat-am)**2)-theta - (np.sum((clean_hat-cm)**2)-theta))
        state_err = float(np.max(np.abs(predicted-observed))); margin_err=abs(dg_obs-dg_pred)
        require(np.allclose(predicted,observed,atol=ATOL,rtol=1e-10), "First state identity")
        require(np.isclose(dg_obs,dg_pred,atol=ATOL,rtol=1e-10), "First margin identity")
        require(np.isclose(dg_obs,float(e["delta_g"]),atol=ATOL,rtol=1e-10), "Saved delta_g")
        formula_rows.append({"seed":seed,"r":row["first_replay"],"r2":row["second_replay"],
                             "source_time":old["source"],"delta0":float(delta[0]),"delta1":float(delta[1]),
                             "predicted_h0":float(predicted[0]),"predicted_h1":float(predicted[1]),
                             "observed_h0":float(observed[0]),"observed_h1":float(observed[1]),
                             "recomputed_delta_g":dg_obs,"predicted_delta_g":dg_pred,
                             "state_max_abs_error":state_err,"margin_abs_error":margin_err})
    counts = Counter(np.sign(r["count_difference"]).item() for r in seeds.values())
    report = {
        "status":"PASS", "n":len(seeds), "increased":counts[1], "decreased":counts[-1], "unchanged":counts[0],
        "delay_histogram":hist(r["delay"] for r in seeds.values()),
        "delay_median":float(np.median([r["delay"] for r in seeds.values()])),
        "first_replay_histogram":hist(r["first_replay"] for r in seeds.values()),
        "second_replay_histogram":hist(r["second_replay"] for r in seeds.values()),
        "strictly_before_second":sum(r["strictly_before_second"] for r in seeds.values()),
        "same_tick_before_second_update":sum(r["same_tick_as_second_before_payload_replacement"] for r in seeds.values()),
        "first_event_before_second_update":sum(r["before_second_update"] for r in seeds.values()),
        "first_cause_counts":hist(r["node1_first_cause_from_03"] for r in seeds.values()),
        "all_event_difference_cause_counts_from_04":{key:sum(causes[s][key] for s in seeds) for key in cause_names},
        "all_flag_flips_including_equal_final_events_from_04":{key:sum(flips[s][key] for s in seeds)
            for key in ["threshold_flag_changed","timeout_flag_changed"]},
        "max_state_formula_abs_error":max(r["state_max_abs_error"] for r in formula_rows),
        "max_margin_formula_abs_error":max(r["margin_abs_error"] for r in formula_rows),
        "report_03_conflict":False,
        "03_missing_columns":"03 contains total event differences and first cause, but not complete cause counts.315/7/2 cannot be derived uniquely from03; read04 separately without changing03.",
        "historical_data_scope":"All 32 first injections from multi-Replay archive; no assertion of full single-Replay trajectory."}
    expected = read_json(OLD/"01_data_integrity_audit.json")["summary"]
    require(report["increased"]==expected["send_count_increased"]["k"] and report["decreased"]==expected["send_count_decreased"]["k"]
            and report["unchanged"]==expected["send_count_unchanged"]["k"], "Report conflicts with 03")
    require(report["all_event_difference_cause_counts_from_04"] == expected["node1_all_cause_tick_counts"],
            "04 vs report conflict")
    return report, list(seeds.values()), formula_rows


def block_diag(blocks):
    n = sum(x.shape[0] for x in blocks)
    m = sum(x.shape[1] for x in blocks)
    out = np.zeros((n,m)); r=c=0
    for b in blocks:
        out[r:r+b.shape[0],c:c+b.shape[1]]=b; r+=b.shape[0];c+=b.shape[1]
    return out


def fixtures(cfg):
    A=np.asarray(cfg["A"]);eps=cfg["epsilon"];theta=cfg["send_delta_squared"]
    edges=np.asarray(cfg["edges_sender_receiver"]);N,n=5,2;E=len(edges)
    H=[s*np.eye(n) for s in cfg["H_scales"]]
    # Algebraic value at k=0 from common Pij=P0; not gains for a newly generated run.
    K=[np.linalg.solve(Hi@np.eye(n)@Hi.T+.05*np.eye(n),
                       (A@Hi.T).T).T for Hi in H]
    degree=np.bincount(edges[:,1],minlength=N)
    F=block_diag([A-K[i]@H[i]-eps*degree[i]*A for i in range(N)])
    J=np.zeros((E*n,N*n));V=np.zeros((N*n,E*n))
    for e,(j,i) in enumerate(edges):
        J[e*n:(e+1)*n,j*n:(j+1)*n]=np.eye(n)
        V[i*n:(i+1)*n,e*n:(e+1)*n]=np.eye(n)
    L=np.kron(np.eye(N),A)@V;AE=np.kron(np.eye(E),A)
    dc=np.arange(40,dtype=float)/50-.25
    h,b,gamma=dc[:10].reshape(5,2),dc[10:20].reshape(5,2),dc[20:].reshape(10,2)
    checks=[]
    def add(name,passed,details):
        require(passed,"Deterministic check failed: "+name)
        checks.append({"name":name,"status":"PASS","scope":"deterministic algebra fixture, NOT a trajectory or research sample",**details})
    max_matrix_err=max_update_err=0.
    matrices=[]
    for bits in itertools.product([0,1],repeat=N):
        sig=np.array(bits);rho=sig[edges[:,0]]
        S=np.kron(np.diag(sig),np.eye(n));R=np.kron(np.diag(rho),np.eye(n))
        M=np.block([[F+eps*L@R@J,np.zeros((10,10)),eps*L@(np.eye(20)-R)],
                    [S,np.eye(10)-S,np.zeros((10,20))],
                    [AE@R@J,np.zeros((20,10)),AE@(np.eye(20)-R)]])
        B=np.vstack([eps*L@R,np.zeros((10,20)),AE@R])
        u=np.zeros((E,n));u[0]=[.2,-.1] if sig[0] else [0.,0.]
        gp=np.empty_like(gamma)
        for e,(j,i) in enumerate(edges):gp[e]=(h[j]+u[e]) if sig[j] else gamma[e]
        hp=np.stack([(A-K[i]@H[i]-eps*degree[i]*A)@h[i] for i in range(N)])
        for e,(j,i) in enumerate(edges):hp[i]+=eps*A@gp[e]
        bp=np.where(sig[:,None].astype(bool),h,b)
        expected=np.concatenate([hp.ravel(),bp.ravel(),(gp@A.T).ravel()])
        result=M@dc+B@u.ravel()
        max_matrix_err=max(max_matrix_err,float(np.max(np.abs(result-expected))))
        # Independently subtract two one-step snapshots; common y cancels.
        x0=np.arange(10,dtype=float).reshape(5,2)/9;m0=x0-.2
        c0=np.arange(20,dtype=float).reshape(10,2)/11;y=np.ones((5,2))*.3
        def step(x,cache):
            cp=np.stack([x[j] if sig[j] else cache[e] for e,(j,i) in enumerate(edges)])
            return cp
        cp0=step(x0,c0)
        cpa=step(x0+h,c0+gamma)+rho[:,None]*u
        def estimate(x,cp):
            out=np.stack([A@x[i]+K[i]@(y[i]-H[i]@x[i]) for i in range(N)])
            for e,(j,i) in enumerate(edges):out[i]+=eps*A@(cp[e]-x[i])
            return out
        diff=estimate(x0+h,cpa)-estimate(x0,cp0)
        max_update_err=max(max_update_err,float(np.max(np.abs(diff-hp))))
        matrices.append(M)
    add("fixed_mode_block_M_B_and_direct_node_difference",max(max_matrix_err,max_update_err)<1e-12,
        {"mode_combinations":32,"max_block_error":max_matrix_err,"max_direct_pair_error":max_update_err,
         "gain_fixture":"k=0 gain algebra only; no Model.build/nominal_gains import; arbitrary states not claimed SoD-reachable"})
    x=matrices[7]@(matrices[12]@dc); y=(matrices[7]@matrices[12])@dc
    add("two_fixed_matrix_composition",np.allclose(x,y,atol=1e-12,rtol=0),
        {"max_abs_error":float(np.max(np.abs(x-y))),"scope":"matrix associativity; not a simulated path"})
    max_split_err=0.
    rows=[]
    for sa,s0 in itertools.product([0,1],repeat=2):
        x0=np.array([.2,-.8]);h1=np.array([-.3,.4]);xa=x0+h1
        q0=np.array([.4,-.2]);qa=np.array([-.1,.7])
        m0=np.array([.1,-.2]);ma=np.array([.2,.3]);k=7
        tau0,taua=1,2;ell0,ella=3,4
        c0=np.linalg.matrix_power(A,k-tau0)@q0
        ca=np.linalg.matrix_power(A,k-taua)@qa
        q0p=s0*x0+(1-s0)*q0;qap=sa*xa+(1-sa)*qa
        tau0p=k if s0 else tau0;tauap=k if sa else taua
        c0p=np.linalg.matrix_power(A,k-tau0p)@q0p
        cap=np.linalg.matrix_power(A,k-tauap)@qap
        predq=sa*h1+(1-sa)*(qa-q0)+(sa-s0)*(x0-q0)
        predc=sa*h1+(1-sa)*(ca-c0)+(sa-s0)*(x0-c0)
        predb=sa*h1+(1-sa)*(ma-m0)+(sa-s0)*(x0-m0)
        bdirect=(sa*xa+(1-sa)*ma)-(s0*x0+(1-s0)*m0)
        predell=(1-sa)*(ella-ell0)+(sa-s0)*(k-ell0)
        elldirect=(k if sa else ella)-(k if s0 else ell0)
        predtau=(1-sa)*(taua-tau0)+(sa-s0)*(k-tau0)
        vals=[np.max(np.abs(qap-q0p-predq)),np.max(np.abs(cap-c0p-predc)),
              np.max(np.abs(bdirect-predb)),abs(elldirect-predell),abs((tauap-tau0p)-predtau)]
        # Verify the split reset's effect on the actual Yang-form fusion algebra.
        xr0=np.array([-.7,.3]);hr=np.array([.1,.2]);yr=np.array([.2,-.4])
        other0=np.array([.05,.09]);otherdiff=np.array([-.03,.04])
        clean_next=A@xr0+K[1]@(yr-H[1]@xr0)+eps*A@(c0p+other0-2*xr0)
        attack_next=A@(xr0+hr)+K[1]@(yr-H[1]@(xr0+hr))+eps*A@(cap+other0+otherdiff-2*(xr0+hr))
        predicted_h=(A-K[1]@H[1]-2*eps*A)@hr+eps*A@(predc+otherdiff)
        vals.append(np.max(np.abs(attack_next-clean_next-predicted_h)))
        max_split_err=max(max_split_err,float(max(vals)))
        rows.append({"Sa":sa,"S0":s0,"raw_difference":(qap-q0p).tolist(),"aligned_difference":(cap-c0p).tolist(),
                     "reference_difference":bdirect.tolist(),"clock_difference":elldirect,
                     "max_error":float(max(vals))})
    add("four_reset_cases_raw_aligned_reference_and_clocks",max_split_err<1e-12,
        {"cases":rows,"max_abs_error":max_split_err})
    # Scalar guard values exercise exact equality branches independently of sqrt rounding.
    cases=[]
    for g0,dg,U0,Ua in itertools.product([-.2,0.,.2],[-.3,0.,.3],[0,1],[0,1]):
        ga=g0+dg;t0=g0>0;ta=ga>0
        up=(g0<=0 and dg>-g0);down=(g0>0 and dg<=-g0)
        require((t0!=ta)==(up or down),"threshold iff")
        if abs(g0)>abs(dg):require(t0==ta,"margin sufficient")
        s0=t0 or bool(U0);sa=ta or bool(Ua)
        upS=(g0<=0 and not U0 and (ga>0 or Ua))
        downS=((g0>0 or U0) and ga<=0 and not Ua)
        require((s0!=sa)==bool(upS or downS),"OR iff")
        cases.append(1)
    add("guard_sign_OR_and_boundary_cases",True,{"cases":len(cases),"threshold_equality_is_not_send":True})
    e=np.array([.4,-.1]);h1=np.array([-.08,.02]);b1=np.array([.03,.04])
    dg=float(np.sum((e+h1-b1)**2)-np.sum(e**2));formula=float(2*e@(h1-b1)+(h1-b1)@(h1-b1))
    add("general_margin_includes_sender_reference",abs(dg-formula)<1e-12,
        {"delta_g":dg,"formula":formula,"abs_error":abs(dg-formula)})
    # h=b != 0 -> no trigger-vector change.
    equal=np.array([.2,-.3])
    add("state_pollution_cancelled_by_reference_pollution",np.allclose(e+equal-equal,e,atol=1e-15,rtol=0),
        {"h":equal.tolist(),"b":equal.tolist(),"delta_trigger_vector":[0,0]})
    # Different local flags, equal OR because both arms timeout.
    e0=np.array([.2,0.]);v=np.array([.2,0.]);g0=float(e0@e0-theta);ga=float((e0+v)@(e0+v)-theta)
    add("timeout_masks_threshold_crossing",g0<=0<ga and ((g0>0 or True)==(ga>0 or True)),
        {"g0":g0,"ga":ga,"U0":1,"Ua":1,"both_send":True})
    add("same_threshold_different_timeout_can_split",g0<=0 and (False or True)!=(False or False),
        {"g0":g0,"ga":g0,"U0":0,"Ua":1})
    # Algebra snapshot with valid nonnegative clocks; no reachability claim.
    k,ell0,ella=17,16,7
    s0=(k-ell0)>=10;sa=(k-ella)>=10
    qzero=np.zeros(2)
    postdiff=sa*qzero+(1-sa)*qzero-(s0*qzero+(1-s0)*qzero)
    add("mode_split_does_not_force_nonzero_cache_or_estimate",sa!=s0 and np.array_equal(postdiff,qzero),
        {"hat_clean":[0,0],"hat_attack":[0,0],"payloads":[0,0],
         "last_send_clean":ell0,"last_send_attack":ella,"k":k,"sigma_clean":int(s0),"sigma_attack":int(sa),
         "actual_sigma_checked":bool(not s0 and sa),
         "post_aligned_difference":postdiff.tolist(),"conclusion":"clock split alone does not algebraically force value pollution",
         "reachability":"snapshot only; not proved reachable from the common initial state by one Replay"})
    # Identical d and mode pair, different healthy baseline gives different reset difference.
    hp=np.array([.3,0.]);outputs=[]
    for a0 in [.1,.2]:
        x0=np.array([a0,0.]);xa=x0+hp
        require(x0@x0<=theta and xa@xa>theta,"same split branch counterexample")
        outputs.append((hp+x0).tolist())  # cache/reference zero; Sa=1, S0=0
    add("difference_state_not_closed_without_healthy_baseline",outputs[0]!=outputs[1],
        {"same_h":hp.tolist(),"same_b_and_gamma":[0,0],"same_Sa_S0":[1,0],
         "two_baseline_reset_differences":outputs,"reachability":"algebra snapshots, not claimed full-network trajectory"})
    q=np.array([.3,-.2]);gamma0=np.linalg.matrix_power(A,2)@q-np.linalg.matrix_power(A,1)@q
    add("raw_zero_difference_with_unequal_ages",np.linalg.norm(gamma0)>0,
        {"raw_difference":[0,0],"ages":[2,1],"aligned_difference":gamma0.tolist()})
    hp=np.array([.1,0.]);risk_rows=[]
    for e0 in [-hp,np.zeros(2),hp]:
        observed=float((e0+hp)@(e0+hp)-e0@e0)
        predicted=float(2*e0@hp+hp@hp)
        require(abs(observed-predicted)<1e-15,"True squared error cross term")
        risk_rows.append({"healthy_error":e0.tolist(),"pollution":hp.tolist(),"loss_change":observed})
    add("pollution_norm_does_not_determine_true_loss_change",risk_rows[0]["loss_change"]<0<risk_rows[1]["loss_change"],
        {"cases":risk_rows,"scope":"algebra loss snapshots; not MSE expectations or new trajectories"})
    return checks


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--verify",action="store_true");args=p.parse_args()
    require(OUT.name=="task1","Run from the Task 1 package")
    source_paths=[HIST/"config.json",HIST/"environment.json"]+[HIST/"sources"/n for n in ["engine.py","model.py","run_study.py"]]
    source_paths += [p for p in OLD.rglob("*") if p.is_file()]
    before={p.relative_to(ROOT).as_posix():sha(p) for p in source_paths};g0=git_state(ROOT)
    cfg,parameter=sources_and_parameters()
    audit,seed_rows,formula_rows=reaudit_csv(cfg)
    cases=fixtures(cfg)
    tree=ast.parse(Path(__file__).read_text(encoding="utf-8-sig"))
    forbidden={"simulate","generate_data","default_rng","random","rand","randn","seed","load"}
    for node in ast.walk(tree):
        if isinstance(node,ast.Call):
            name=node.func.id if isinstance(node.func,ast.Name) else node.func.attr if isinstance(node.func,ast.Attribute) else ""
            require(name not in forbidden,"Disallowed simulation/trajectory/RNG call "+name)
    require(all(sha(ROOT/p)==d for p,d in before.items()),"Protected input changed")
    require(g0==git_state(ROOT),"Tracked state changed")
    report={"classification":"FACT / DERIVED","task":"Task1 deterministic validation","baseline_commit":BASELINE,
            "script_sha256":sha(__file__),"parameters":parameter,"Task0_5_independent_reaudit":audit,
            "deterministic_fixture_groups":cases,"fixture_group_count":len(cases),
            "no_simulation_or_rng_calls_AST":True,"no_new_seeds_trajectories_npz_reads":True,
            "protected_file_count":len(before),"protected_sha256":before,"protected_unchanged":True,
            "tracked_diffs_unchanged_during_execution":True,
            "status":"PASS","scope":"algebra and saved-data consistency only; not innovation, reachability, stochastic stability or detector performance validation"}
    out=OUT/"validation"
    contents={"formula_validation.json":text_json(report),"seed_reaudit.csv":csv_text(seed_rows),
              "first_replay_recheck.csv":csv_text(formula_rows)}
    if args.verify:
        for name,text in contents.items():require((out/name).read_bytes()==text.encode("utf-8"),"Recompute mismatch "+name)
        print("PASS: deterministic recomputation exactly matches all three validation files")
    else:
        out.mkdir(parents=True,exist_ok=True)
        for name,text in contents.items():(out/name).write_bytes(text.encode("utf-8"))
        print(text_json({"status":"PASS","fixture_groups":len(cases),"historical_reaudit":audit}))


if __name__=="__main__":
    main()
