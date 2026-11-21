"""Independent deterministic checks of completed-square half moments.

Only fixed numerical quadrature fixtures are used. Continuous-domain rate
certification and random performance experiments are explicitly out of scope.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np

from core import log_factors
from check_joint_reference import MODELS, all_send_riccati, fisher, integrate, silent, selection

HERE=Path(__file__).resolve().parent


def log_gaussian(u,S):
    return -u*u/(2*S)-.5*math.log(2*math.pi*S)


def completed_square_check(model,P,r,b,da,dj):
    R,Z=model["R"],model["Z"]
    S,V=P+R,P+R+1/Z
    G0=silent(P,R,Z,0.,r)
    Ga=silent(P,R,Z,da,r)
    Gj=silent(P,R,Z,dj,r)
    dstar=2*da-dj
    delta=dj-da
    Gstar=silent(P,R,Z,dstar,r)
    candidate_silent_log=log_factors(np.array(P),np.array(r),np.array(False),
                                    np.array(math.nan),np.array(dj),np.array(b),model)[-1]
    atom_direct=Ga*math.exp(-.5*float(candidate_silent_log))
    atom_square=math.exp(delta*delta/(2*V))*math.sqrt(G0*Gstar)
    def direct_integrand(u):
        wt=selection(u-b-r,Z)
        w0=selection(u-r,Z)
        if wt==0. or w0==0.:
            return 0.
        log_density=log_gaussian(u-b-da,S)+math.log(wt)
        candidate_log=float(log_factors(np.array(P),np.array(r),np.array(True),
                            np.array(u),np.array(dj),np.array(b),model)[-1])
        return math.exp(log_density-.5*candidate_log)
    direct_cont,direct_error=integrate(direct_integrand,(r,r+b))
    def affinity_integrand(u):
        w0=selection(u-r,Z)
        wstar=selection(u-b-r,Z)
        if w0==0. or wstar==0.:
            return 0.
        return math.exp(.5*(log_gaussian(u,S)+log_gaussian(u-b-dstar,S))) * math.sqrt(w0*wstar)
    affinity_cont,affinity_error=integrate(affinity_integrand,(r,r+b))
    square_cont=math.exp(delta*delta/(2*S))*affinity_cont
    direct=atom_direct+direct_cont
    square=atom_square+square_cont
    envelope=math.exp(delta*delta/(2*S))*(math.sqrt(G0*Gstar)+affinity_cont)
    error=abs(direct-square)
    if error>3e-10 or direct>envelope+3e-10:
        raise AssertionError("Completed-square half-moment identity/envelope failed")
    return dict(model=model["id"],P=P,r=r,b=b,true_prior_bias=da,candidate_prior_bias=dj,
                transformed_bias=dstar,
                direct_negative_half_moment=direct,
                completed_square_negative_half_moment=square,
                common_exponential_affinity_envelope=envelope,
                absolute_identity_error=error,
                silent_atom_identity_error=abs(atom_direct-atom_square),
                integration_reported_error=direct_error+math.exp(delta*delta/(2*S))*affinity_error)


def affinity_gap(model,P,r,h,b):
    R,Z=model["R"],model["Z"]
    S,V=P+R,P+R+1/Z
    d=h*b
    G0=silent(P,R,Z,0.,r)
    log_silent_ratio=(2*d*r-d*d)/(2*V)
    atom_square_gap=G0*math.expm1(.5*log_silent_ratio)**2
    shift=b+d
    def squared_root_difference(u):
        left=math.exp(.5*log_gaussian(u,S))*math.sqrt(selection(u-r,Z))
        right=math.exp(.5*log_gaussian(u-shift,S))*math.sqrt(selection(u-b-r,Z))
        return (left-right)**2
    integral,error=integrate(squared_root_difference,(r,r+b))
    return .5*(atom_square_gap+integral),.5*error


def main():
    core_hash_before=hashlib.sha256((HERE/"core.py").read_bytes()).hexdigest()
    completed=[]
    local=[]
    for model in MODELS:
        for P in (all_send_riccati(model),.8):
            for r in (-model["delta"],0.,model["delta"]):
                for b in (.05,.1,.25):
                    for ha,hj in ((-.4,-.4),(-.4,-.8),(-1.,0.),(0.,-2.)):
                        completed.append(completed_square_check(model,P,r,b,ha*b,hj*b))
                for h in (-1.,-.5,0.,.5):
                    information=fisher(P,model["R"],model["Z"],r,h)["joint_Fisher"]
                    values=[]
                    for b in (.01,.005,.0025):
                        gap,error=affinity_gap(model,P,r,h,b)
                        scaled=gap/(b*b)
                        ratio=scaled/(information/8)
                        values.append(dict(b=b,affinity_gap=gap,gap_over_b_squared=scaled,
                                           ratio_to_Fisher_over_8=ratio,quad_reported_error=error))
                    if abs(values[-1]["ratio_to_Fisher_over_8"]-1)>0.02:
                        raise AssertionError("Local Hellinger/Fisher numerical limit check failed")
                    local.append(dict(model=model["id"],P=P,r=r,h=h,Fisher=information,
                                      Fisher_over_8=information/8,small_amplitude_checks=values))
    if hashlib.sha256((HERE/"core.py").read_bytes()).hexdigest()!=core_hash_before:
        raise AssertionError("Frozen core changed during deterministic validation")
    result=dict(status="PASS",random_performance_samples_generated=False,
                core_sha256=core_hash_before,
                completed_square_cases=len(completed),local_Fisher_cases=len(local),
                maximum_completed_square_identity_error=max(c["absolute_identity_error"] for c in completed),
                maximum_local_ratio_error_at_b_0025=max(
                    abs(c["small_amplitude_checks"][-1]["ratio_to_Fisher_over_8"]-1) for c in local),
                completed_square=completed,local_Fisher=local,
                limitations=[
                    "The same current attack amplitude b is used in true and candidate kernels.",
                    "Direct expectations call the frozen candidate core; transformed kernels use independent reference integrands.",
                    "Integrals split at both moving density zeros u=r and u=r+b.",
                    "Finite fixtures verify algebra/numerics, not a certified continuous-domain uniform Hellinger rate.",
                    "Small-amplitude checks do not extend the actual three-point detector grid to arbitrary amplitudes."])
    (HERE/"fractional_moment_checks.json").write_text(
        json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf8")
    print(json.dumps({k:result[k] for k in ("status","completed_square_cases","local_Fisher_cases",
        "maximum_completed_square_identity_error","maximum_local_ratio_error_at_b_0025")}))


if __name__=="__main__":
    main()
