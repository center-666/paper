"""Deterministic finite-precision diagnostics for the frozen joint kernel.

No performance samples, detector tuning, or frozen-input modifications.
Decimal references treat supplied binary64 inputs as exact; separate one-ulp
perturbations measure input sensitivity rather than implementation error.
"""
from __future__ import annotations

from decimal import Decimal, localcontext
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy.integrate import quad

from core import log_factors, phase_mean

HERE=Path(__file__).resolve().parent


def exact_float(value):
    return Decimal.from_float(float(value))


def decimal_logs(P,r,u,d,b,model):
    with localcontext() as ctx:
        ctx.prec=80
        P,r,u,d,b=map(exact_float,(P,r,u,d,b))
        R,Z=map(exact_float,(model["R"],model["Z"]))
        one=Decimal(1)
        S=P+R
        V=S+one/Z
        pref=(one+Z*S).sqrt()
        p0=(-r*r/(2*V)).exp()/pref
        p1=(-(d-r)*(d-r)/(2*V)).exp()/pref
        event=(one-p1).ln()-(one-p0).ln()
        def logW(z):
            if z==0:
                return Decimal("-Infinity")
            return (one-(-Z*z*z/2).exp()).ln()
        joint=(u*(b+d)-(b+d)*(b+d)/2)/S+logW(u-b-r)-logW(u-r)
        payload=joint-event
        def tilt(theta):
            ps=(-(S*theta-r)*(S*theta-r)/(2*V)).exp()/pref
            logmgf=S*theta*theta/2+(one-ps).ln()-(one-p0).ln()
            return theta*u-logmgf
        return np.array([float(x) for x in (event,tilt(b/S),tilt((b+d)/S),payload,joint)])


def implemented_logs(P,r,u,d,b,model):
    return np.array(log_factors(np.array(P),np.array(r),np.array(True),np.array(u),
                               np.array(d),np.array(b),model),dtype=float)


def main():
    protocol=json.loads((HERE/"protocol.json").read_text(encoding="utf8"))
    frozen_before=hashlib.sha256((HERE/"core.py").read_bytes()).hexdigest()
    checks=[]
    largest_error=0.
    largest_ulp_change=0.
    largest_center_sensitivity=0.
    for model in protocol["models"]:
        P=.3
        for r in (-model["delta"],0.,model["delta"]):
            for b in (.05,.1,.25):
                d=-.6*b
                for root_kind,root in (("null_zero",r),("alternative_zero",r+b)):
                    for epsilon in (1e-8,1e-10,1e-12):
                        for sign in (-1,1):
                            u=root+sign*epsilon
                            values=implemented_logs(P,r,u,d,b,model)
                            reference=decimal_logs(P,r,u,d,b,model)
                            error=float(np.max(np.abs(values-reference)))
                            ulp_u=float(np.nextafter(u,math.inf))
                            perturbed=implemented_logs(P,r,ulp_u,d,b,model)
                            ulp_change=float(np.max(np.abs(perturbed-values)))
                            # A deterministic center error is a different
                            # observation model, not a floating-point error.
                            shifted=implemented_logs(P,r+1e-6,u,d,b,model)
                            center_change=float(np.max(np.abs(shifted-values)))
                            largest_error=max(largest_error,error)
                            largest_ulp_change=max(largest_ulp_change,ulp_change)
                            largest_center_sensitivity=max(largest_center_sensitivity,center_change)
                            if not (np.isfinite(values).all() and np.isfinite(reference).all()):
                                raise AssertionError("Nonzero near-root fixture became nonfinite")
                            if error>1e-9:
                                raise AssertionError("Binary64 kernel differs from 80-digit exact-input reference")
                            checks.append(dict(model=model["id"],r=r,b=b,d=d,root_kind=root_kind,
                                requested_distance=sign*epsilon,received_innovation=u,
                                max_log_factor_error_vs_80digit_reference=error,
                                max_log_factor_change_under_one_input_ulp=ulp_change,
                                max_log_factor_change_under_center_error_1e_minus6=center_change,
                                log_joint=float(values[-1])))
    cdf_checks=[]
    for model in protocol["models"]:
        for Ppost in (.06,.16,.35):
            V=1/model["Z"]+model["A"]**2*Ppost+model["Q"]+model["R"]
            pref=1/math.sqrt(model["Z"]*V)
            for D in (0.,-.025,-.1,-.25):
                for delta in (model["delta"],1e-4,1e-6,1e-8):
                    modified=dict(model,delta=delta)
                    coded=float(phase_mean(Ppost,D,modified))
                    numerical,quad_error=quad(
                        lambda z:math.exp(-(model["A"]*D-delta*z)**2/(2*V)),
                        -1.,1.,epsabs=2e-14,epsrel=2e-14)
                    reference=pref*numerical/2
                    error=abs(coded-reference)
                    if delta==model["delta"] and error>2e-13:
                        raise AssertionError("Original frozen phase-CDF precision is insufficient")
                    cdf_checks.append(dict(model=model["id"],Ppost=Ppost,bias=D,delta=delta,
                        frozen_delta=delta==model["delta"],cdf_probability=coded,
                        direct_integral_probability=reference,absolute_error=error,
                        relative_error=error/reference,quad_reported_error=quad_error))
    original=[c for c in cdf_checks if c["frozen_delta"]]
    stress=[c for c in cdf_checks if not c["frozen_delta"]]
    frozen_after=hashlib.sha256((HERE/"core.py").read_bytes()).hexdigest()
    if frozen_after!=frozen_before:
        raise AssertionError("Frozen core changed during independent sensitivity checks")
    result=dict(status="PASS",performance_random_samples_generated=False,
        frozen_core_sha256=frozen_before,
        reference="80-digit Decimal evaluation of exact represented binary64 inputs",
        numpy_float64_epsilon=float(np.finfo(np.float64).eps),
        numpy_longdouble_epsilon=float(np.finfo(np.longdouble).eps),
        near_zero_cases=len(checks),near_zero_max_log_factor_error=largest_error,
        maximum_log_factor_change_under_one_input_ulp=largest_ulp_change,
        maximum_log_factor_change_under_center_error_1e_minus6=largest_center_sensitivity,
        phase_CDF_frozen_delta_max_absolute_error=max(c["absolute_error"] for c in original),
        phase_CDF_smaller_delta_stress_max_absolute_error=max(c["absolute_error"] for c in stress),
        near_zero_checks=checks,phase_CDF_checks=cdf_checks,
        limitations=[
            "Finite deterministic fixtures do not certify all floating-point inputs.",
            "One-ulp and center perturbations are sensitivity probes, not performance experiments.",
            "The current transmitted payload remains ideal continuous-valued; rounded payloads require bin-integrated likelihoods.",
            "The phase-CDF small-delta stress values are not protocol changes or detector tuning.",
            "No empirical Bernstein claim is made for unbounded joint log-likelihood contributions."])
    (HERE/"precision_sensitivity_checks.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf8")
    print(json.dumps({k:result[k] for k in ("status","near_zero_cases","near_zero_max_log_factor_error",
        "maximum_log_factor_change_under_one_input_ulp","maximum_log_factor_change_under_center_error_1e_minus6",
        "phase_CDF_frozen_delta_max_absolute_error","phase_CDF_smaller_delta_stress_max_absolute_error")}))


if __name__=="__main__":
    main()
