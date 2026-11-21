"""Independent deterministic checks of implemented joint observation factors."""
from __future__ import annotations

import hashlib
import itertools
import json
import math
from pathlib import Path

import numpy as np
from scipy.integrate import quad_vec
from scipy.special import logsumexp

from core import JointDetectors, NAMES, log_factors
from check_joint_reference import MODELS, all_send_riccati, silent, selection

HERE = Path(__file__).resolve().parent


def core_factors(P, r, sent, u, d, b, model):
    return np.array(log_factors(np.array(P), np.array(r), np.array(sent),
                               np.array(u), np.array(d), np.array(b), model), dtype=float)


def integral_checks():
    checks = []
    max_expectation_error = max_factorization_error = max_input_mask_error = 0.0
    for model in MODELS:
        R, Z, delta = model["R"], model["Z"], model["delta"]
        for P in (all_send_riccati(model), 0.8):
            S = P+R
            for r in (-delta, 0.0, delta):
                p0 = silent(P,R,Z,0.,r)
                for d,b in ((0.,.05),(-.05,.1),(-.25,.25)):
                    zero_logs=core_factors(P,r,False,math.nan,d,b,model)
                    silent_different=core_factors(P,r,False,1e100,d,b,model)
                    max_input_mask_error=max(max_input_mask_error,float(np.max(np.abs(zero_logs-silent_different))))
                    atom=p0*np.exp(zero_logs)
                    def integrand(u):
                        weight=selection(u-r,Z)
                        if weight==0:
                            # Values at one point do not affect the integral;
                            # isolated endpoint behavior is tested separately.
                            return np.zeros(5)
                        log_null=-u*u/(2*S)-.5*math.log(2*math.pi*S)+math.log(weight)
                        logs=core_factors(P,r,True,u,d,b,model)
                        nonlocal max_factorization_error
                        if np.isfinite(logs).all():
                            max_factorization_error=max(max_factorization_error,
                                                        abs(float(logs[4]-logs[0]-logs[3])))
                        return np.exp(log_null+logs)
                    points=[-math.inf,*sorted(set((r,r+b))),math.inf]
                    cont=np.zeros(5)
                    err=0.
                    for a,z in zip(points[:-1],points[1:]):
                        value,e=quad_vec(integrand,a,z,epsabs=2e-11,epsrel=2e-10,limit=300)
                        cont+=value
                        err+=e
                    totals=atom+cont
                    deviation=float(np.max(np.abs(totals-1)))
                    max_expectation_error=max(max_expectation_error,deviation)
                    if deviation>2e-9:
                        raise AssertionError("Implemented factor has nonunit H0 mean")
                    checks.append(dict(model=model["id"],P=P,r=r,d=d,b=b,
                                       null_means_event_R0_R1_payload_joint=totals.tolist(),
                                       reported_quad_error=err))
    if max_factorization_error>2e-12 or max_input_mask_error !=0:
        raise AssertionError("Factorization or unavailable silent payload masking failed")
    return dict(cases=checks,maximum_null_mean_error=max_expectation_error,
                maximum_joint_minus_event_minus_payload=max_factorization_error,
                maximum_silent_payload_mask_error=max_input_mask_error)


def deterministic_tree_checks():
    # Every history of six chosen event branches. Continuous payload values
    # are deterministic fixtures, so this is not a probability quadrature.
    max_mix_error=max_advance_error=0.
    strengths=(.05,.1,.25)
    weights=np.array((.2,.3,.5))
    log_pi=np.log(weights)
    paths=0
    for model in MODELS:
        for bits in itertools.product((False,True),repeat=6):
            paths+=1
            online=JointDetectors(1,model,strengths,weights,.01)
            P=.8
            d=np.zeros(3)
            log_components=np.zeros((5,6,3))
            logs_all=np.zeros((5,3))
            maximum=np.full(7,-np.inf)
            tau=np.full(7,-1,dtype=int)
            old_components=np.zeros((5,3))
            prev_nu=prev_q=None
            for t,sent in enumerate(bits):
                r=model["delta"]*.73*math.sin(.41*t+.2)
                u=r+.37*math.cos(.43*t+.4)+.0123
                logs=np.asarray(log_factors(np.array([P]),np.array([r]),np.array([sent]),
                            np.array([u if sent else math.nan]),d,np.array(strengths),model))
                log_components[:,:t+1,:]+=logs[:,None,:]
                logs_all+=logs
                start_log_weights=-np.log(np.arange(1,t+2,dtype=float))-np.log(np.arange(2,t+3,dtype=float))
                explicit=np.logaddexp(logsumexp(log_components[:,:t+1,:]+
                                        start_log_weights[None,:,None]+log_pi[None,None,:],axis=(1,2)),
                                     -math.log(t+2))
                zero=logsumexp(logs_all[-1]+log_pi)
                if t:
                    factors=np.log(prev_q/prev_nu) if not sent else np.log((1-prev_q)/(1-prev_nu))
                    old_components[:t]+=factors
                    old_w=-np.log(np.arange(1,t+1,dtype=float))-np.log(np.arange(2,t+2,dtype=float))
                    old=np.logaddexp(logsumexp(old_components[:t]+old_w[:,None]+log_pi[None,:]),
                                     -math.log(t+1))
                else:
                    old=0.
                explicit_stats=np.r_[old,explicit,zero]
                maximum=np.maximum(maximum,explicit_stats)
                tau[(tau<0)&(explicit_stats>=math.log(100))]=t
                online.step(t,np.array([P]),np.array([r]),np.array([sent]),np.array([u if sent else math.nan]))
                max_mix_error=max(max_mix_error,float(np.max(np.abs(online.maximum_log_e[:,0]-maximum))))
                if not np.array_equal(online.tau[:,0],tau):
                    raise AssertionError("Alarm times differ from explicit mixture")
                Ri=model["R"] if sent else model["R"]+1/model["Z"]
                K=P/(P+Ri)
                Ppost=P*(1-K)
                expected=model["A"]*((1-K)*d-int(sent)*K*np.array(strengths))
                online.advance(np.array([Ppost]),np.array([K]),np.array([sent]))
                max_advance_error=max(max_advance_error,float(np.max(np.abs(online.d[:,0]-expected))))
                d=expected
                prev_nu=float(online.prev_nu[0])
                prev_q=online.prev_q[:,0].copy()
                P=model["A"]**2*Ppost+model["Q"]
    if max_mix_error>2e-12 or max_advance_error>1e-14:
        raise AssertionError("Mixture/update recurrence differs from direct calculation")
    return dict(paths=paths,depth=6,maximum_mixture_error=max_mix_error,
                maximum_advance_error=max_advance_error,
                note="Continuous payload fixtures are not sampled or assigned null probabilities.")


def zero_checks():
    model=MODELS[0]
    P,r,d,b=.3,0.,-.05,.1
    at_null_zero=core_factors(P,r,True,r,d,b,model)
    at_alternative_zero=core_factors(P,r,True,r+b,d,b,model)
    if not (np.isposinf(at_null_zero[[3,4]]).all() and
            np.isneginf(at_alternative_zero[[3,4]]).all()):
        raise AssertionError("Isolated density zeros were clipped or mishandled")
    near=[]
    for eps in (1e-4,1e-8,1e-12):
        for u in (r-eps,r+eps,r+b-eps,r+b+eps):
            logs=core_factors(P,r,True,u,d,b,model)
            if not np.isfinite(logs).all():
                raise AssertionError("Near-zero nonzero density factor became nonfinite")
            near.append(dict(received_innovation=u,log_factors=logs.tolist()))
    return dict(null_zero_joint_positive_infinity=True,alternative_zero_joint_negative_infinity=True,
                near_zero_cases=near,
                isolated_zero_cases_are_not_performance_sample_data=True)


def main():
    result=dict(status="PASS",performance_random_samples_generated=False,
                core_sha256=hashlib.sha256((HERE/"core.py").read_bytes()).hexdigest(),
                integration=integral_checks(),recurrences=deterministic_tree_checks(),zeros=zero_checks(),
                channels=list(NAMES),independent_reference_imported="check_joint_reference.py")
    (HERE/"joint_kernel_checks.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf8")
    print(json.dumps(dict(status=result["status"],core_sha256=result["core_sha256"],
        null_mean_max_error=result["integration"]["maximum_null_mean_error"],
        mixture_max_error=result["recurrences"]["maximum_mixture_error"],
        performance_random_samples_generated=False)))


if __name__=="__main__":
    main()
