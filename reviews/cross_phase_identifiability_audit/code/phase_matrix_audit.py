"""Deterministic cross-phase observation geometry audit; never simulates data.

Run from the repository root using Python with numpy/scipy:
python reviews/cross_phase_identifiability_audit/code/phase_matrix_audit.py

Only Model.build and the existing event_sensitivity pure matrix response are
called from historical code. No simulate/generate_data/random function is called.
Every output directory is new; failures and the frozen pre-computation plan stay.
"""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import platform
import sys
import time
from pathlib import Path
from types import SimpleNamespace

sys.dont_write_bytecode = True
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulation"))
sys.path.insert(0, str(ROOT / "reviews/g1_retroactive_recovery/code"))
from model import Model
from compare_deghat_outputs import event_sensitivity

RUN = "c_phase_geometry_20261114_r01"
RANK_ATOL = 1e-10
RANK_RTOL = 1e-10
ALGEBRA_RTOL = 1e-8


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def native(x):
    if isinstance(x, np.ndarray):
        return native(x.tolist())
    if isinstance(x, np.generic):
        return native(x.item())
    if isinstance(x, float) and not np.isfinite(x):
        return None
    if isinstance(x, dict):
        return {str(k): native(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [native(v) for v in x]
    return x


def write_json(path, obj):
    Path(path).write_text(json.dumps(native(obj), indent=2, ensure_ascii=False,
                                    allow_nan=False) + "\n", encoding="utf-8")


def schedule_for(cfg, name, partial):
    t = np.arange(cfg["T"])
    out = np.zeros((cfg["T"], cfg["N"]), dtype=bool)
    if name == "gap8":
        for i in range(cfg["N"]):
            out[:, i] = t % 8 == i
    else:
        gaps = partial["schedules"]["irregular"]
        pos = np.r_[0, np.cumsum(gaps)[:-1]]
        period = sum(gaps)
        for i in range(cfg["N"]):
            out[:, i] = np.isin(t % period, (pos + i * partial["phase_step"]) % period)
    out[0] = True
    return out


def reset(model, fresh):
    n, N, E = model.cfg["n"], model.cfg["N"], len(model.edges)
    zdim = (N + E) * n
    result = np.eye(zdim)
    for e, (sender, _) in enumerate(model.edges):
        if fresh[sender]:
            sl = slice((N + e) * n, (N + e + 1) * n)
            result[sl] = 0
            result[sl, sender*n:(sender+1)*n] = np.eye(n)
    return result


def transition(model, k):
    """From post-reception error state at k to pre-reception state at k+1."""
    N, n, E = model.cfg["N"], model.cfg["n"], len(model.edges)
    b = N + E
    F = np.zeros((b*n, b*n))
    D = np.zeros((b*n, N*n))
    degree = np.bincount(model.edges[:, 1], minlength=N)
    for i in range(N):
        sl = slice(i*n, (i+1)*n)
        F[sl, sl] = ((1-model.cfg["epsilon"]*degree[i])*model.A
                      - model.gains[k, i] @ model.H[i])
        D[sl, sl] = -model.gains[k, i]
    for e, (_, receiver) in enumerate(model.edges):
        cs = slice((N+e)*n, (N+e+1)*n)
        es = slice(receiver*n, (receiver+1)*n)
        F[es, cs] += model.cfg["epsilon"] * model.A
        F[cs, cs] = model.A
    R = np.zeros((N*n, N*n))
    for i in range(N):
        R[i*n:(i+1)*n, i*n:(i+1)*n] = model.R[i]
    W = np.kron(np.ones((b, b)), model.Q)
    return F, D, W + D @ R @ D.T


def observation_row(model, edge, phase):
    N, n, E = model.cfg["N"], model.cfg["n"], len(model.edges)
    receiver = model.edges[edge, 1]
    row = np.zeros((n, (N+E)*n))
    block = N+edge if phase == "C" else receiver
    row[:, block*n:(block+1)*n] = model.H[receiver]
    return row


def exact_covariance(model, schedule, edge, times_c, times_p):
    """Keep current measurement-noise feedback in future residual covariance.

    z contains current node errors and aligned cache errors after current
    receptions. B=Cov(z,previous observation rows). No state sample is generated.
    """
    N, n, E = model.cfg["N"], model.cfg["n"], len(model.edges)
    receiver = model.edges[edge, 1]
    P = np.kron(np.ones((N+E, N+E)), model.P0)
    B = np.zeros((P.shape[0], 0))
    cov = np.zeros((0, 0))
    obs = {int(t): "C" for t in times_c}
    assert not (set(times_c) & set(times_p))
    obs.update({int(t): "P" for t in times_p})
    if not obs:
        return cov
    for k in range(max(obs)+1):
        fresh_reset = reset(model, schedule[k])
        P = fresh_reset @ P @ fresh_reset.T
        B = fresh_reset @ B
        F, D, noise = transition(model, k)
        if k in obs:
            C = observation_row(model, edge, obs[k])
            cross = C @ B
            variance = C @ P @ C.T + model.R[receiver]
            cov = np.block([[cov, cross.T], [cross, variance]])
            past = F @ B
            feedback = D[:, receiver*n:(receiver+1)*n] @ model.R[receiver]
            next_cross = F @ P @ C.T + feedback
            B = np.concatenate([past, next_cross], axis=1)
        else:
            B = F @ B
        P = F @ P @ F.T + noise
        P = (P+P.T)/2
    return (cov+cov.T)/2


def svd_parts(O, n=2):
    if len(O) == 0:
        return np.zeros(n), 0, np.eye(n)
    _, s, vt = np.linalg.svd(O, full_matrices=True)
    tol = max(RANK_ATOL, RANK_RTOL*(s[0] if len(s) else 0))
    rank = int(np.sum(s > tol))
    pad = np.zeros(n)
    pad[:len(s)] = s
    return pad, rank, vt[rank:].T


def identifiable(O, G):
    _, _, null = svd_parts(O, G.shape[1])
    residue = float(np.linalg.norm(G @ null))
    scale = max(1., float(np.linalg.norm(G)))
    return residue <= RANK_ATOL + RANK_RTOL*scale, residue


def whiten(O, cov):
    if len(O) == 0:
        return O.copy()
    L = np.linalg.cholesky(cov)
    return np.linalg.solve(L, O)


def audit_one(model, sch, case, edge, r, q, d, cohort, out, response_cache):
    N, n = model.cfg["N"], model.cfg["n"]
    sender, receiver = map(int, model.edges[edge])
    assert sch[r, sender] and q > r
    assert sch[q, sender] and not np.any(sch[r+1:q, sender])
    key = (case, edge, r)
    if key not in response_cache:
        response_cache[key] = event_sensitivity(model, sch, edge, r)
    state, aligned = response_cache[key]
    tc = np.arange(r, min(q, d+1))
    tp = np.arange(q+1, d+1) if q+1 <= d else np.empty(0, dtype=int)
    OC = np.asarray([-model.H[receiver] @ aligned[k, edge] for k in tc]).reshape(-1, n)
    OP = np.asarray([-model.H[receiver] @ state[k, receiver] for k in tp]).reshape(-1, n)
    OJ = np.concatenate([OC, OP])
    # During the original cache episode the raw injected packet difference is I.
    direct = np.asarray([-model.H[receiver] @ model.powers[k-r] for k in tc]).reshape(-1, n)
    assert np.max(np.abs(OC-direct), initial=0) < RANK_ATOL
    cov = exact_covariance(model, sch, edge, tc, tp)
    split = len(OC)
    CC, CP, PP = cov[:split, :split], cov[:split, split:], cov[split:, split:]
    W = {"C": whiten(OC, CC), "P": whiten(OP, PP), "J": whiten(OJ, cov)}
    infos = {name: value.T @ value for name, value in W.items()}
    Gd = state[d, receiver]
    Gnext = state[d+1, receiver]
    row = {"case": case, "cohort": cohort, "edge_index": edge,
           "sender": sender, "receiver": receiver, "r": r, "q": q, "d": d,
           "cache_times": len(tc), "post_times": len(tp),
           "right_censored": bool(q > d), "post_not_yet_available": bool(q+1 > d),
           "cross_covariance_norm": float(np.linalg.norm(CP)),
           "joint_noise_min_eigenvalue": float(np.linalg.eigvalsh(cov)[0]),
           "joint_noise_condition": float(np.linalg.cond(cov))}
    arrays = {"O_C": OC, "O_P": OP, "O_J": OJ, "Sigma": cov,
              "Sigma_CC": CC, "Sigma_CP": CP, "Sigma_PP": PP,
              "G_d": Gd, "G_dplus1": Gnext,
              "G_network_d": state[d].reshape(N*n, n),
              "G_network_dplus1": state[d+1].reshape(N*n, n),
              "times_C": tc, "times_P": tp}
    for name, O in (("C", OC), ("P", OP), ("J", OJ)):
        sv, rank, null = svd_parts(O)
        sw, rankw, _ = svd_parts(W[name])
        idd, residuald = identifiable(O, Gd)
        idn, residualn = identifiable(O, Gnext)
        eigen = np.linalg.eigvalsh(infos[name])
        row.update({f"rank_{name}": rank, f"rank_white_{name}": rankw,
                    f"svmax_{name}": sv[0], f"svmin_{name}": sv[-1],
                    f"white_svmax_{name}": sw[0], f"white_svmin_{name}": sw[-1],
                    f"info_min_eigenvalue_{name}": eigen[0],
                    f"info_max_eigenvalue_{name}": eigen[-1],
                    f"target_d_identifiable_{name}": idd,
                    f"target_dplus1_identifiable_{name}": idn,
                    f"kernel_target_residual_d_{name}": residuald,
                    f"kernel_target_residual_dplus1_{name}": residualn})
        arrays["I_"+name] = infos[name]
        arrays["white_"+name] = W[name]
    if len(OP):
        regression = np.linalg.solve(CC, CP).T
        schur = PP - regression @ CP
        tilde = OP - regression @ OC
        info_increment = tilde.T @ np.linalg.solve(schur, tilde)
        residual = np.linalg.norm(infos["J"]-infos["C"]-info_increment)
        scale = max(1., np.linalg.norm(infos["J"]))
        assert residual <= ALGEBRA_RTOL*scale
        arrays.update(Schur_P_given_C=schur, O_P_given_C=tilde,
                      I_P_given_C=info_increment)
        row.update(schur_identity_relative_residual=float(residual/scale),
                   conditional_post_info_min_eigenvalue=float(np.linalg.eigvalsh(info_increment)[0]))
    else:
        row.update(schur_identity_relative_residual=0.,
                   conditional_post_info_min_eigenvalue=0.)
    dc = np.linalg.eigvalsh(infos["J"]-infos["C"])[0]
    dp = np.linalg.eigvalsh(infos["J"]-infos["P"])[0]
    assert min(dc, dp) >= -ALGEBRA_RTOL*max(1., np.linalg.norm(infos["J"]))
    row.update(info_gain_over_C_min_eigenvalue=float(dc),
               info_gain_over_P_min_eigenvalue=float(dp),
               joint_rank_exceeds_both=bool(row["rank_J"]>max(row["rank_C"],row["rank_P"])),
               joint_only_target_d=bool(row["target_d_identifiable_J"] and not row["target_d_identifiable_C"] and not row["target_d_identifiable_P"]),
               joint_only_target_dplus1=bool(row["target_dplus1_identifiable_J"] and not row["target_dplus1_identifiable_C"] and not row["target_dplus1_identifiable_P"]))
    for name in ("C", "P"):
        _, _, null = svd_parts(OC if name=="C" else OP)
        row["joint_response_on_"+name+"_null_norm"] = float(np.linalg.norm(OJ@null))
    b = np.asarray([1.2, -.8])
    for name in ("C", "P", "J"):
        for label, factor in (("strong", 1.), ("half", .5), ("quarter", .25)):
            row[f"fixed_FDI_noncentrality_{name}_{label}"] = float(factor**2*b@infos[name]@b)
    past = np.flatnonzero(sch[:r, sender])
    replay_source = int(past[-8]) if len(past)>=8 else None
    matched = r-80
    row.update(replay_8th_previous_source=replay_source,
               replay_8th_previous_age=r-replay_source if replay_source is not None else None,
               replay_64_source_legal=bool(r>=64 and sch[r-64,sender]),
               matched_gap80_source_legal=bool(matched>=0 and sch[matched,sender]))
    stem=f"{case}_{cohort}_e{edge}_r{r}_d{d}"
    np.savez_compressed(out/(stem+".npz"), **arrays)
    row["matrix_file"] = stem+".npz"
    return row, state, aligned


def pairwise_common_coordinates(model, sch, events, response_cache, out):
    """All hypotheses receive the exact same legal output vector and covariance.

    Reference output coordinates: fixed edge0 cache residual200:207 and receiver1
    innovations209:216, independent of which candidate is being evaluated.
    """
    n = model.cfg["n"]
    tc = np.arange(200,208);tp = np.arange(209,217)
    edge0=0;receiver=1
    assert tuple(model.edges[edge0])==(0,1)
    cov=exact_covariance(model,sch,edge0,tc,tp)
    split=len(tc)*n
    covs={"C":cov[:split,:split],"P":cov[split:,split:],"J":cov}
    obs_c=[];obs_p=[];targets=[];targets_next=[]
    for edge,r in events:
        key=("full_gap8",int(edge),int(r))
        if key not in response_cache:
            response_cache[key]=event_sensitivity(model,sch,int(edge),int(r))
        state,aligned=response_cache[key]
        obs_c.append(np.asarray([-model.H[receiver]@aligned[k,edge0] for k in tc]).reshape(-1,n))
        obs_p.append(np.asarray([-model.H[receiver]@state[k,receiver] for k in tp]).reshape(-1,n))
        targets.append(state[216,receiver])
        targets_next.append(state[217,receiver])
    matrices={"C":np.asarray(obs_c),"P":np.asarray(obs_p)}
    matrices["J"]=np.concatenate([matrices["C"],matrices["P"]],axis=1)
    rows=[]
    for h in range(len(events)):
        for ell in range(h+1,len(events)):
            G=np.concatenate([targets[h],-targets[ell]],axis=1)
            Gn=np.concatenate([targets_next[h],-targets_next[ell]],axis=1)
            row={"candidate_h":h,"edge_h":events[h][0],"time_h":events[h][1],
                 "candidate_l":ell,"edge_l":events[ell][0],"time_l":events[ell][1]}
            for name in ("C","P","J"):
                oh=matrices[name][h];ol=matrices[name][ell]
                O=np.concatenate([oh,-ol],axis=1)
                sw,rank,_=svd_parts(whiten(O,covs[name]),4)
                idd,resd=identifiable(O,G)
                idn,resn=identifiable(O,Gn)
                row.update({f"rank_{name}":rank,f"svmin_white_{name}":sw[-1],
                            f"target_d_identifiable_{name}":idd,
                            f"target_dplus1_identifiable_{name}":idn,
                            f"target_kernel_residual_d_{name}":resd,
                            f"target_kernel_residual_dplus1_{name}":resn})
                row[f"white_singular_values_{name}"]=json.dumps(sw.tolist())
                uh,sh,_=np.linalg.svd(whiten(oh,covs[name]),full_matrices=False)
                ul,sl,_=np.linalg.svd(whiten(ol,covs[name]),full_matrices=False)
                rh=int(np.sum(sh>max(RANK_ATOL,RANK_RTOL*sh[0]))) if len(sh) else 0
                rl=int(np.sum(sl>max(RANK_ATOL,RANK_RTOL*sl[0]))) if len(sl) else 0
                if rh and rl:
                    canonical=np.linalg.svd(uh[:,:rh].T@ul[:,:rl],compute_uv=False)
                    row[f"min_principal_angle_deg_{name}"]=float(np.degrees(np.arccos(np.clip(canonical[0],-1,1))))
                else:
                    row[f"min_principal_angle_deg_{name}"]=None
            row["joint_rank_exceeds_both"]=row["rank_J"]>max(row["rank_C"],row["rank_P"])
            row["joint_only_target_d"]=(row["target_d_identifiable_J"] and
                                        not row["target_d_identifiable_C"] and not row["target_d_identifiable_P"])
            row["joint_only_target_dplus1"]=(row["target_dplus1_identifiable_J"] and
                                            not row["target_dplus1_identifiable_C"] and not row["target_dplus1_identifiable_P"])
            rows.append(row)
    with (out/"pairwise_common_coordinates.csv").open("w",newline="",encoding="utf-8") as stream:
        w=csv.DictWriter(stream,fieldnames=list(rows[0]));w.writeheader();w.writerows(native(rows))
    np.savez_compressed(out/"pairwise_common_coordinates.npz",events=np.asarray(events),
                        O_C=matrices["C"],O_P=matrices["P"],O_J=matrices["J"],
                        Sigma=cov,G_d=np.asarray(targets),G_dplus1=np.asarray(targets_next),
                        times_C=tc,times_P=tp)
    return {"pair_count":len(rows),
            "joint_rank_exceeds_both_count":sum(r["joint_rank_exceeds_both"] for r in rows),
            "joint_only_target_d_count":sum(r["joint_only_target_d"] for r in rows),
            "joint_only_target_dplus1_count":sum(r["joint_only_target_dplus1"] for r in rows),
            "coordinate_scope":"same edge0 cache C200:207 and node1 innovation P209:216 for every candidate; fixed healthy covariance",
            "does_not_claim":"No calibrated detection, localization accuracy or global false alarm comparison"}


def covariance_feedback_identity_check():
    """Two-time scalar algebra check, not a new research network/case.

    With epsilon=0, e1=(1-K)e0+w-Kv0. Cov(g1,g0)=(1-K)P0-KR.
    This negative cross covariance exposes omission of measurement feedback.
    """
    m=SimpleNamespace(cfg={"N":2,"n":1,"T":2,"epsilon":0.},
                      edges=np.asarray([[1,0]]),P0=np.asarray([[2.]]),
                      A=np.asarray([[1.]]),Q=np.asarray([[.1]]),
                      H=np.ones((2,1,1)),R=np.full((2,1,1),3.),
                      gains=np.full((2,2,1,1),.5))
    computed=exact_covariance(m,np.ones((2,2),bool),0,[],[0,1])
    expected=np.asarray([[5.,-.5],[-.5,4.35]])
    error=float(np.max(np.abs(computed-expected)))
    assert error<RANK_ATOL
    return {"expected":expected,"computed":computed,"max_abs_error":error,
            "scope":"two-time scalar identity validating current-v feedback; not Monte Carlo or a new research case"}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,default=HERE/"results"/RUN)
    args=parser.parse_args()
    out=args.out
    out.mkdir(parents=True,exist_ok=False)
    start=time.perf_counter()
    base_path=ROOT/"reviews/g1_retroactive_recovery/results/g1r_p0_verified_20261113_v1/config.json"
    partial_path=ROOT/"simulation/partial_observability_probe_plan.json"
    frozen_path=ROOT/"reviews/g1_retroactive_recovery/results/g1r_final_replay_20261113_v1/frozen_plan.json"
    cfg=json.loads(base_path.read_text(encoding="utf-8"))["model"]
    partial=json.loads(partial_path.read_text(encoding="utf-8"))
    frozen=json.loads(frozen_path.read_text(encoding="utf-8"))
    sources=[Path(__file__),base_path,partial_path,frozen_path,ROOT/"simulation/model.py",
             ROOT/"simulation/engine.py",ROOT/"reviews/g1_retroactive_recovery/code/compare_deghat_outputs.py"]
    sources.append(ROOT/"reviews/g1_retroactive_recovery/results/g1r_p0_verified_20261113_v1/model_response_and_fits.npz")
    hashes={str(p.relative_to(ROOT)):sha(p) for p in sources}
    plan={"run_id":out.name,"baseline_commit":"bee4bbf928602a4e233ef7413f79d5a7b78aac9a",
          "python":sys.version,"python_executable":sys.executable,"numpy_version":np.__version__,
          "scope":"deterministic matrix geometry only; no generated trajectories, no random numbers, no new estimator",
          "models":["existing_full_heterogeneous","existing_rank_one_pressure"],
          "schedules":["gap8 phase1 original G1-R","existing irregular phase1 G1 pressure"],
          "main_events":"all 10 directed edges; first actual sender transmission >=200; q=next sender transmission; d=q+8",
          "frozen_candidates":"all 10 original gap8 candidate events at d=216; right censoring retained",
          "pairwise_extension":"45 full/gap8 frozen candidate pairs in SAME fixed edge0 C200:207 / node1 P209:216 coordinates; kernel target and subspace audit only",
          "covariance_internal_check":"two-time scalar analytic identity including current measurement-noise feedback; no random draw",
          "ranks":{"absolute":RANK_ATOL,"relative":RANK_RTOL},
          "algebra_relative_acceptance":ALGEBRA_RTOL,"covariance_ridge":0,
          "Fisher_label":"O' Sigma^-1 O is Fisher only for deterministic exogenous FDI Gaussian location model; Replay design geometry only",
          "random_seed":None,"new_simulations":0,"source_hashes":hashes}
    write_json(out/"frozen_plan.json",plan)
    try:
        covariance_check=covariance_feedback_identity_check()
        rows=[];response_cache={};response_check={}
        models={}
        for sensing in ("full","rank_one"):
            c=copy.deepcopy(cfg)
            if sensing=="rank_one":
                c.update(A=partial["A"],H_matrices=partial["H_matrices"],R_matrices=partial["R_matrices"])
            model=Model.build(c)
            for sched in ("gap8","irregular"):
                case=sensing+"_"+sched
                sch=schedule_for(c,sched,partial)
                models[case]={"config":c,"schedule":sch.tolist(),"schedule_sha256":hashlib.sha256(sch.tobytes()).hexdigest(),
                              "actual_A":model.A,"actual_H":model.H,"gains":model.gains.tolist()}
                for edge,(sender,receiver) in enumerate(model.edges):
                    tx=np.flatnonzero(sch[:,sender])
                    r=int(tx[tx>=200][0]);q=int(tx[tx>r][0]);d=q+8
                    row,S,Sa=audit_one(model,sch,case,edge,r,q,d,"main",out,response_cache)
                    rows.append(row)
                    if case=="full_gap8" and edge==0:
                        assert (r,q,d)==(200,208,216)
                        old=np.load(ROOT/"reviews/g1_retroactive_recovery/results/g1r_p0_verified_20261113_v1/model_response_and_fits.npz")
                        es=float(np.max(np.abs(S-old["state_response"])))
                        ec=float(np.max(np.abs(Sa-old["cache_response"])))
                        assert max(es,ec)<RANK_ATOL
                        response_check={"old_verified_response_state_max_abs":es,"old_verified_response_cache_max_abs":ec}
                if sched=="gap8":
                    for edge,r in frozen["candidate_events"]["8"]:
                        sender=int(model.edges[edge,0])
                        q=int(np.flatnonzero(sch[:,sender]&(np.arange(c["T"])>r))[0])
                        row,_,_=audit_one(model,sch,case,int(edge),int(r),q,216,"frozen_candidates",out,response_cache)
                        rows.append(row)
                if case=="full_gap8":
                    pairwise=pairwise_common_coordinates(model,sch,frozen["candidate_events"]["8"],response_cache,out)
        write_json(out/"models_and_schedules.json",models)
        with (out/"geometry.csv").open("w",newline="",encoding="utf-8") as stream:
            w=csv.DictWriter(stream,fieldnames=list(rows[0]));w.writeheader()
            w.writerows(native(rows))
        summary={"run_id":out.name,"row_count":len(rows),"main_case_count":4,
                 "main_rows":sum(r["cohort"]=="main" for r in rows),
                 "frozen_candidate_rows":sum(r["cohort"]=="frozen_candidates" for r in rows),
                 "true_joint_rank_complement_count":sum(r["joint_rank_exceeds_both"] for r in rows),
                 "true_joint_only_target_d_count":sum(r["joint_only_target_d"] for r in rows),
                 "true_joint_only_target_dplus1_count":sum(r["joint_only_target_dplus1"] for r in rows),
                 "response_reuse_check":response_check,
                 "covariance_feedback_identity_check":covariance_check,
                 "pairwise_common_coordinate_audit":pairwise,
                 "max_schur_identity_relative_residual":max(r["schur_identity_relative_residual"] for r in rows),
                 "minimum_joint_noise_eigenvalue":min(r["joint_noise_min_eigenvalue"] for r in rows),
                 "runtime_seconds":time.perf_counter()-start,
                 "no_simulate_or_generate_data_called":True,
                 "no_random_draws":True,
                 "source_files_unchanged":all(sha(ROOT/p)==h for p,h in hashes.items())}
        assert summary["source_files_unchanged"]
        write_json(out/"summary.json",summary)
        print(json.dumps(native(summary),indent=2))
    except Exception as exc:
        write_json(out/"failure.json",{"error":repr(exc),"no_success_claim":True,
                                     "runtime_seconds":time.perf_counter()-start})
        raise


if __name__=="__main__":
    main()
