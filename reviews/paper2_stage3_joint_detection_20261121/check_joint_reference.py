"""Independent deterministic joint-kernel/MGF/Fisher reference integrals.

This file intentionally does not import a candidate detector implementation.
No random number generator or performance sample is used.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from scipy.integrate import quad

HERE = Path(__file__).resolve().parent
MODELS = (
    dict(id="S1", A=0.82, Q=0.05, R=0.2, P0=0.8, Z=2.0, delta=0.011628232298833967),
    dict(id="U1", A=1.04, Q=0.05, R=0.2, P0=0.8, Z=2.0, delta=0.022259755314928388),
)


def all_send_riccati(model):
    A, Q, R = (model[k] for k in ("A", "Q", "R"))
    c = R - Q - A * A * R
    return (-c + math.sqrt(c * c + 4 * Q * R)) / 2


def selection(z, Z):
    return -math.expm1(-Z * z * z / 2)


def gaussian(u, S):
    return math.exp(-u * u / (2 * S)) / math.sqrt(2 * math.pi * S)


def silent(P, R, Z, d, r):
    S = P + R
    V = S + 1 / Z
    return math.exp(-(d - r) ** 2 / (2 * V)) / math.sqrt(1 + Z * S)


def subdensity(u, S, Z, d, b, r):
    return gaussian(u - b - d, S) * selection(u - b - r, Z)


def integrate(function, splits):
    nodes = [-math.inf, *sorted(set(float(x) for x in splits)), math.inf]
    total = 0.0
    reported_error = 0.0
    for left, right in zip(nodes[:-1], nodes[1:]):
        value, error = quad(function, left, right, epsabs=2e-12, epsrel=2e-11, limit=300)
        total += value
        reported_error += error
    return total, reported_error


def joint_kl(P, R, Z, r, h, theta):
    S, V = P + R, P + R + 1 / Z
    d, b = h * theta, theta
    p1 = silent(P, R, Z, d, r)
    atom = p1 * (2 * d * r - d * d) / (2 * V)
    def integrand(u):
        w1 = selection(u - b - r, Z)
        if w1 == 0:
            return 0.0
        w0 = selection(u - r, Z)
        if w0 == 0:
            # An integrable log singularity. quad's interior nodes do not hit
            # prescribed split endpoints; this branch documents the value.
            return math.inf
        shift = b + d
        log_ratio = shift * u / S - shift * shift / (2 * S) + math.log(w1) - math.log(w0)
        return gaussian(u - shift, S) * w1 * log_ratio
    cont, error = integrate(integrand, (r, r + b))
    return atom + cont, error


def fisher(P, R, Z, r, h):
    S, V = P + R, P + R + 1 / Z
    p0 = silent(P, R, Z, 0.0, r)
    pprime = p0 * h * r / V
    a = 1 + h
    conditional_shift = pprime / (1 - p0)
    def selected_parts(u, offset=0.0):
        z = u - r
        w = selection(z, Z)
        wp = Z * z * math.exp(-Z * z * z / 2)
        ratio = 2 * Z if z == 0 else wp * wp / w
        score_polynomial = a * u / S + offset
        return gaussian(u, S) * (
            score_polynomial * score_polynomial * w
            - 2 * score_polynomial * wp + ratio)
    sent_fisher, ef = integrate(selected_parts, (r,))
    weighted_conditional, ec = integrate(lambda u:selected_parts(u, conditional_shift), (r,))
    score_integral, es = integrate(
        lambda u:gaussian(u, S) * (a * u / S * selection(u-r,Z) -
                                  Z*(u-r)*math.exp(-Z*(u-r)**2/2)), (r,))
    joint = p0 * (h * r / V) ** 2 + sent_fisher
    event = pprime * pprime / (p0 * (1 - p0))
    return dict(joint_Fisher=joint, event_Fisher=event,
                weighted_payload_Fisher=weighted_conditional,
                fisher_chain_residual=joint-event-weighted_conditional,
                score_mean_residual=score_integral+pprime,
                reported_quad_error=max(ef, ec, es))


def main():
    normalizations, tilts, fishers = [], [], []
    max_mass_error = max_mgf_relative_error = max_mean_error = 0.0
    for model in MODELS:
        R, Z, delta = model["R"], model["Z"], model["delta"]
        for P in (all_send_riccati(model), 0.3, model["P0"]):
            S, V = P + R, P + R + 1 / Z
            for r in (-delta, 0.0, delta):
                p0 = silent(P, R, Z, 0.0, r)
                for d, b in ((0.,0.),(0.,.05),(-.1,.1),(-.25,.25)):
                    p1 = silent(P, R, Z, d, r)
                    mass, err = integrate(lambda u:subdensity(u,S,Z,d,b,r), (r+b,))
                    expected_mean = b+d+p1*S*(d-r)/(V*(1-p1))
                    mean_integral, _ = integrate(lambda u:u*subdensity(u,S,Z,d,b,r), (r+b,))
                    mass_error = abs(mass+p1-1)
                    mean_error = abs(mean_integral/(1-p1)-expected_mean)
                    max_mass_error = max(max_mass_error, mass_error)
                    max_mean_error = max(max_mean_error, mean_error)
                    if mass_error > 5e-11 or mean_error > 5e-10:
                        raise AssertionError("Joint kernel normalization or selected mean failed")
                    # The reference expectation cancels null density a.e.;
                    # core-factor evaluation will be tested independently.
                    joint_factor_mean = p1+mass
                    payload_factor_mean = p0+(1-p0)/(1-p1)*mass
                    normalizations.append(dict(model=model["id"],P=P,r=r,d=d,b=b,
                        total_mass=p1+mass,quad_error=err,
                        joint_factor_null_mean=joint_factor_mean,
                        payload_factor_null_mean=payload_factor_mean,
                        wrong_unnormalized_payload_null_mean=p0+mass,
                        selected_mean_error=mean_error))
                for lam in (-0.8, 0.0, 0.8):
                    s = 1/math.sqrt(1+Z*S)
                    exact = math.exp(S*lam*lam/2)*(1-s*math.exp(-(S*lam-r)**2/(2*V)))/(1-p0)
                    integral, err = integrate(
                        lambda u:math.exp(-u*u/(2*S)+lam*u)/math.sqrt(2*math.pi*S)*selection(u-r,Z),
                        (r,))
                    numeric = integral/(1-p0)
                    relative_error = abs(numeric-exact)/exact
                    max_mgf_relative_error = max(max_mgf_relative_error, relative_error)
                    if relative_error > 5e-11:
                        raise AssertionError("Selected-normal MGF failed")
                    tilts.append(dict(model=model["id"],P=P,r=r,lambda_value=lam,
                                      exact_MGF=exact,quadrature_MGF=numeric,reported_quad_error=err,
                                      relative_error=relative_error))
                if P == all_send_riccati(model):
                    for h in (0.,-.5,-1.):
                        result = fisher(P,R,Z,r,h)
                        if abs(result["score_mean_residual"]) > 5e-10 or abs(result["fisher_chain_residual"]) > 5e-10:
                            raise AssertionError("Score centering or Fisher chain rule failed")
                        local_checks=[]
                        for theta in (.005,.002,.001):
                            kl, error = joint_kl(P,R,Z,r,h,theta)
                            ratio=kl/(.5*theta*theta*result["joint_Fisher"])
                            local_checks.append(dict(theta=theta,joint_KL=kl,
                                                     KL_to_local_Fisher_ratio=ratio,reported_quad_error=error))
                        if abs(local_checks[-1]["KL_to_local_Fisher_ratio"]-1)>0.02:
                            raise AssertionError("Local KL/Fisher consistency failed")
                        fishers.append(dict(model=model["id"],P=P,r=r,h=h,**result,local_KL_checks=local_checks))
    result=dict(status="PASS",performance_random_samples_generated=False,
                reference_imports_candidate_core=False,
                normalization_cases=len(normalizations),tilt_cases=len(tilts),fisher_cases=len(fishers),
                maximum_normalization_error=max_mass_error,
                maximum_selected_mean_error=max_mean_error,
                maximum_MGF_relative_error=max_mgf_relative_error,
                normalization=normalizations,tilt=tilts,fisher=fishers,
                limitations="Deterministic quadrature of listed fixtures, not interval-arithmetic certification or performance data.")
    (HERE/"joint_reference_checks.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf8")
    print(json.dumps({k:result[k] for k in ("status","normalization_cases","tilt_cases","fisher_cases",
                                           "maximum_normalization_error","maximum_MGF_relative_error")}))


if __name__ == "__main__":
    main()
