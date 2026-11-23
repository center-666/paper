"""Deterministic arithmetic and coordinate checks for the N01 contract."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
import hashlib
from itertools import product
import json
import math
from pathlib import Path
import sys

import numpy as np
import scipy
from scipy.integrate import quad

from numerical_record import (
    NumericalLikelihoodRecord, binary64_rounding_cell, binary64_value, effective_risk_lower,
    exact_matvec, exact_value, finite_decimal, interval_fraction,
)
from exact_linear import add, asfloat, matmul, matrix, transpose, update
from interval_arithmetic import Interval as I
from interval_observation import center_contract, selection_log_ratio

HERE = Path(__file__).resolve().parent
REVIEWS = HERE.parent
STAGE6 = REVIEWS / "paper2_stage6_vector_correction_20261122"


def decimal(value):
    return D(value.numerator) / D(value.denominator)


def log_trigger_point(value, Z):
    if not value:
        return D("-Infinity")
    return (1 - (-decimal(Z * value * value / 2)).exp()).ln()


def main():
    model = json.loads((STAGE6 / "model.json").read_text(encoding="utf8"))
    A, C = matrix(model["A"]), matrix(model["C"])
    Afloat, Cfloat = np.array(model["A"], float), np.array(model["C"], float)
    Z, R = F(model["Z"]), F(model["R"])
    counts = Counter()
    examples = {}
    maximum = {"monitor_error": F(0), "prior_width": F(0), "posterior_width": F(0)}
    positives = 0

    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        counts[name] += 1

    def contains(box, value):
        return F(box.lo) <= value <= F(box.hi)

    check("binary64_and_decimal_input_semantics_differ",
          binary64_value(.1) != exact_value(".1"))
    check("subnormal_binary64_value_is_exact", binary64_value(math.ulp(0.0)) == F(1, 2**1074))
    check("subnormal_finite_decimal_roundtrip",
          F(finite_decimal(binary64_value(math.ulp(0.0)))) == binary64_value(math.ulp(0.0)))
    for value in (.1, -.1, 0.0, -0.0, math.ulp(0.0), -math.ulp(0.0),
                  float.fromhex("0x1.fffffffffffffp+1023"),
                  -float.fromhex("0x1.fffffffffffffp+1023")):
        lo, hi = binary64_rounding_cell(value)
        point = binary64_value(value)
        check("rounding_cell_contains_represented_value", lo < point < hi)
        check("rounding_cell_interior_roundtrips", float((lo+point)/2)==value and float((point+hi)/2)==value)
    lo, hi = binary64_rounding_cell(.1)
    check("rounding_cell_contains_original_decimal_value", lo <= F(".1") <= hi)
    rejected = False
    try:
        exact_value(.1)
    except TypeError:
        rejected = True
    check("implicit_float_observation_rejected", rejected)
    # Check the actual, rather than nominal, quantizer coordinates on both
    # event branches. Failed appends must leave every cache available for retry.
    delta = F(model["quantization_half_width"])
    for sent in (False, True):
        for sign in (-1, 1):
            for seeded in (False, True):
                record = NumericalLikelihoodRecord(model)
                prior = (0.0, 0.0)
                if seeded:
                    record.append(False, None, F(0), prior=prior, posterior=prior)
                center = sign * delta
                payload = F(".5") if sent else None
                before = deepcopy((record.monitor.__dict__, record.core.__dict__))
                try:
                    record.append(sent, payload, center + sign * F(1, 10**18),
                                  prior=prior, posterior=prior)
                except ValueError as exc:
                    check("illegal_actual_center_rejected", "quantization contract" in str(exc))
                else:
                    raise AssertionError("illegal_actual_center_accepted")
                check("illegal_center_commits_nothing", before == (record.monitor.__dict__, record.core.__dict__))
                frame = record.append(sent, payload, center, prior=prior, posterior=prior)
                check("actual_center_boundary_accepted", frame.actual_center_residual == center)
                check("valid_center_retry_advances_once", record.core.n == before[1]["n"] + 1)
    record = NumericalLikelihoodRecord(model, [F(1), F(0)])
    frame = record.append(False, None, F(0), prior=(0.0, 0.0), posterior=(0.0, 0.0))
    check("nominal_center_can_exceed_half_width", frame.nominal_center_residual.hi < -D(str(float(delta))))
    check("actual_center_still_legal", frame.actual_center_residual == 0)
    check("interval_center_legal_at_boundaries",
          center_contract((-delta, delta), (0, 0), delta) == "legal")
    check("interval_center_outside_is_illegal",
          center_contract((delta + F(1, 10**18), delta + 1), (0, 0), delta) == "illegal")
    check("interval_center_overlap_is_unresolved",
          center_contract((delta, delta + F(1, 10**18)), (0, 0), delta) == "unresolved")
    for amp in ((F(".19"), F(".21")), (F(".2"), F(".21")),
                (F(".21"), F(".22"))):
        ratio = selection_log_ratio((F(".2"), F(".2")), (0, 0), amp, Z)
        check("interval_selection_upper_is_finite", ratio.hi.is_finite())
        if amp[0] <= F(".2") <= amp[1]:
            check("moving_zero_has_negative_infinity_lower", ratio.lo == D("-Infinity"))
        for b in (amp[0], (amp[0]+amp[1])/2, amp[1]):
            with localcontext() as context:
                context.prec = 100
                value = log_trigger_point(F(".2")-b, Z)-log_trigger_point(F(".2"), Z)
                check("interval_selection_contains_point_diagnostic", ratio.lo <= value <= ratio.hi)
    check("healthy_zero_returns_unresolved",
          selection_log_ratio((F("-.01"), F(".01")), (0, 0), (0, F(".1")), Z) is None)
    check("near_zero_denominator_returns_unresolved",
          selection_log_ratio((F(1, 10**100), F(1, 10**100)), (0, 0), (0, 0), Z) is None)
    fixtures = [("switch_" + "".join(map(str, events)), events, (F(0), F(0)), "raw")
                for events in product((False, True), repeat=5)]
    fixtures += [
        ("long_silence", (True,) + (False,) * 15 + (True,), (F(".1"), F("-.2")), "raw"),
        ("large_state", (True, False, True, True, False, True),
         (F(10**16), F(-3 * 10**15)), "raw"),
        ("innovation_stream", (True, False, True, False, True, True),
         (F(".3"), F("-.1")), "innovation"),
    ]
    for name, events, initial, mode in fixtures:
        record = NumericalLikelihoodRecord(model, initial)
        nominal_post = None
        actual_post = np.array([float(x) for x in initial])
        response = {}
        candidate_mean = {}
        accumulated_loglik = {}
        history = []
        last_frame = None
        for t, sent in enumerate(events):
            sent = bool(sent)
            nominal_prior = initial if t == 0 else exact_matvec(A, nominal_post)
            actual_prior = actual_post.copy() if t == 0 else Afloat @ actual_post
            prior_exact = tuple(binary64_value(x) for x in actual_prior)
            measured_actual = exact_matvec(C, prior_exact)[0]
            offset = F(1, 500)
            raw_center = measured_actual + offset
            raw_payload = measured_actual + F(17 + 3*t, 100) if sent else None
            posterior_covariance, Kmat, Tmat = update(
                record.core.P, C, R + (0 if sent else 1 / Z))
            K = tuple(row[0] for row in Kmat)
            Kfloat = np.asarray(asfloat(Kmat)).ravel()
            if mode == "innovation":
                residual_float = float(F(17 + 3*t, 100) if sent else offset)
                observed = measured_actual + binary64_value(residual_float)
                if sent:
                    raw_payload = observed
                else:
                    raw_center = observed
            else:
                observed = raw_payload if sent else raw_center
                residual_float = float(observed) - float((Cfloat @ actual_prior).item())
            actual_post = actual_prior + Kfloat * residual_float
            observation = raw_payload if sent else raw_center
            exact_nominal_update = exact_matvec(Tmat, nominal_prior)
            nominal_post = tuple(x + k * observation for x, k in zip(exact_nominal_update, K))
            frame = record.append(sent, raw_payload, raw_center,
                                  prior=actual_prior, posterior=actual_post)
            last_frame = frame
            history.append(frame)
            xi_prior = tuple(x - y for x, y in zip(frame.actual_prior, nominal_prior))
            xi_post = tuple(x - y for x, y in zip(frame.actual_posterior, nominal_post))
            for j in range(2):
                check("prior_error_contains_exact_reference", contains(frame.prior_error[j], xi_prior[j]))
                check("posterior_error_contains_exact_reference", contains(frame.posterior_error[j], xi_post[j]))
                check("nominal_prior_contains_exact_reference", contains(frame.nominal_prior[j], nominal_prior[j]))
                check("nominal_posterior_contains_exact_reference", contains(frame.nominal_posterior[j], nominal_post[j]))
                maximum["monitor_error"] = max(maximum["monitor_error"], abs(xi_post[j]))
                maximum["prior_width"] = max(maximum["prior_width"], F(frame.prior_error[j].hi)-F(frame.prior_error[j].lo))
                maximum["posterior_width"] = max(maximum["posterior_width"], F(frame.posterior_error[j].hi)-F(frame.posterior_error[j].lo))
            shift = exact_matvec(C, xi_prior)[0]
            nominal_r = raw_center - exact_matvec(C, nominal_prior)[0]
            check("nominal_center_contains_exact_transform", contains(frame.nominal_center_residual, nominal_r))
            check("center_coordinate_translation", nominal_r == frame.actual_center_residual + shift)
            S = matmul(matmul(C, [list(row) for row in frame.prior_covariance]), transpose(C))[0][0] + R
            V = S + 1 / Z
            for k in range(t + 1):
                old_response = response.get(k, (F(0), F(0)))
                prior_response = exact_matvec(A, old_response)
                eta = exact_matvec(C, prior_response)[0]
                transported = exact_matvec(Tmat, prior_response)
                response[k] = tuple(x + (gain if sent else 0) for x, gain in zip(transported, K))
                for j in range(2):
                    check("response_contains_exact_rational_reference",
                          contains(record.core.candidates[k]["H"][j], response[k][j]))
                for b in (F(0), F(".07"), F(".2")):
                    key = (k, b)
                    mean_prior = nominal_prior if k == t else exact_matvec(A, candidate_mean[key])
                    exact_update = exact_matvec(Tmat, mean_prior)
                    candidate_mean[key] = tuple(x + gain * (observation - (b if sent else 0))
                                                for x, gain in zip(exact_update, K))
                    ideal_bias = tuple(b * h for h in response[k])
                    check("nominal_pollution_identity",
                          tuple(x-y for x,y in zip(nominal_post,candidate_mean[key])) == ideal_bias)
                    check("represented_pollution_identity",
                          tuple(x-y for x,y in zip(frame.actual_posterior,candidate_mean[key])) ==
                          tuple(x+y for x,y in zip(xi_post,ideal_bias)))
                    d_actual = -exact_matvec(C, tuple(x+b*h for x,h in zip(xi_prior,prior_response)))[0]
                    check("silent_kernel_coordinate_identity",
                          d_actual-frame.actual_center_residual == -b*eta-nominal_r)
                    with localcontext() as context:
                        context.prec = 100
                        if sent:
                            nominal_u = raw_payload - exact_matvec(C, nominal_prior)[0]
                            check("nominal_innovation_contains_exact_transform", contains(frame.nominal_innovation, nominal_u))
                            check("sent_gaussian_coordinate_identity",
                                  frame.actual_innovation-b-d_actual == nominal_u-(1-eta)*b)
                            v = raw_payload-raw_center
                            check("selection_zero_is_translation_invariant",
                                  frame.actual_innovation-frame.actual_center_residual == v)
                            residual_candidate = raw_payload-b-exact_matvec(C,mean_prior)[0]
                            increment = decimal((nominal_u**2-residual_candidate**2)/(2*S))
                            increment += log_trigger_point(v-b,Z)-log_trigger_point(v,Z)
                        else:
                            residual_candidate = raw_center-exact_matvec(C,mean_prior)[0]
                            increment = decimal((nominal_r**2-residual_candidate**2)/(2*V))
                        accumulated_loglik[key] = accumulated_loglik.get(key,D(0)) + increment
                        box = record.core.likelihood(k,interval_fraction(b))
                        check("likelihood_contains_independent_100_digit_value",
                              box.lo <= accumulated_loglik[key] <= box.hi)
            if shift and abs(shift)>F(".00000001") and "required_mean_shift" not in examples:
                examples["required_mean_shift"] = {
                    "fixture":name,"time":t,"C_xi_prior":str(float(shift)),
                    "actual_center_residual":str(float(frame.actual_center_residual)),
                    "nominal_center_residual":str(float(nominal_r))}
        # A supplied interval fixture checks the output risk identity algebraically.
        published = np.array([float(x) for x in last_frame.actual_posterior])
        published[0] -= .01
        action = tuple(last_frame.actual_posterior[j]-binary64_value(published[j]) for j in range(2))
        if sum(map(abs,action)) <= 1:
            bound = effective_risk_lower(last_frame,
                {0:record.core.candidates[0]["H"]},{0:[(F(".07"),F(".2"))]},
                published,model["W"],F(1))
            for b in (F(".07"),F(".1"),F(".2")):
                true_bias = tuple(x + b * h for x, h in zip(xi_post, response[0]))
                exact_risk = 2*sum((x*a for x,a in zip(true_bias,action)),F(0))-sum((a*a for a in action),F(0))
                check("effective_risk_lower_is_conservative",bound["risk_lower"]<=exact_risk)
            positives += int(bound["risk_lower"]>0)
        # Every zero-free segment uses the inherited strong-concavity bound.
        k = 0
        cuts = sorted({D(".05"), D(".24"), *[
            mark[0] for mark in record.core.marks if mark is not None and D(".05") < mark[0] < D(".24")]})
        for lo, hi in zip(cuts, cuts[1:]):
            b = (F(lo) + F(hi)) / 2
            upper = record.core.tangent_upper(k, I(lo, hi))
            # Independent closed-form physical likelihood, using exact cached
            # covariance/gain trajectory reconstructed in a fresh rational pass.
            P = matrix(model["P0_prior"])
            mean = initial
            replay_nominal = initial
            ll = D(0)
            with localcontext() as context:
                context.prec = 100
                for i, saved in enumerate(history):
                    S = matmul(matmul(C,P),transpose(C))[0][0] + R
                    V = S + 1/Z
                    mu_prior = mean if i==0 else exact_matvec(A,mean)
                    m_prior = replay_nominal if i==0 else exact_matvec(A,replay_nominal)
                    Ppost, Kmat, Tmat = update(P,C,R+(0 if saved.sent else 1/Z))
                    kval = tuple(row[0] for row in Kmat)
                    obs = saved.payload if saved.sent else saved.center
                    if saved.sent:
                        u = saved.payload-exact_matvec(C,m_prior)[0]
                        shifted = saved.payload-b-exact_matvec(C,mu_prior)[0]
                        v = saved.payload-saved.center
                        ll += decimal((u*u-shifted*shifted)/(2*S))
                        ll += log_trigger_point(v-b,Z)-log_trigger_point(v,Z)
                    else:
                        r = saved.center-exact_matvec(C,m_prior)[0]
                        shifted = saved.center-exact_matvec(C,mu_prior)[0]
                        ll += decimal((r*r-shifted*shifted)/(2*V))
                    mean = tuple(x+gain*(obs-(b if saved.sent else 0))
                                 for x,gain in zip(exact_matvec(Tmat,mu_prior),kval))
                    replay_nominal = tuple(x+gain*obs for x,gain in zip(exact_matvec(Tmat,m_prior),kval))
                    P = add(matmul(matmul(A,Ppost),transpose(A)),matrix(model["Q"]))
                check("tangent_upper_dominates_independent_value",ll<=upper)
        # Null healthy density and invalid input leave both states available for retry.
        before = deepcopy((record.core.n, record.monitor.time, record.core.ref,
                           record.monitor.actual_posterior, record.core.P,
                           record.monitor.P, record.monitor.posterior_error,
                           record.core.candidates, record.core.warm, record.core.marks,
                           record.core.stats))
        failed=False
        try:
            zero_center = exact_matvec(C, tuple(binary64_value(x) for x in actual_post))[0] + F(".002")
            record.append(True,zero_center,zero_center,prior=actual_post,posterior=actual_post)
        except ArithmeticError:
            failed=True
        check("null_density_returns_unresolved",failed)
        check("failed_append_does_not_commit_state",
              before == (record.core.n, record.monitor.time, record.core.ref,
                         record.monitor.actual_posterior, record.core.P,
                         record.monitor.P, record.monitor.posterior_error,
                         record.core.candidates, record.core.warm, record.core.marks,
                         record.core.stats))
        retry_prior = Afloat @ actual_post
        retry_center = exact_matvec(C, tuple(binary64_value(x) for x in retry_prior))[0] + F(".002")
        _, retry_Kmat, _ = update(record.core.P, C, R + 1 / Z)
        retry_K = np.asarray(asfloat(retry_Kmat)).ravel()
        retry_post = retry_prior + retry_K * (float(retry_center) - float((Cfloat @ retry_prior).item()))
        record.append(False, None, retry_center, prior=retry_prior, posterior=retry_post)
        check("valid_retry_advances_once", record.core.n == before[0] + 1 and record.monitor.time == before[1] + 1)
    # Direct quadrature checks the shifted kernel, independent of cache recursion.
    mass_errors=[]
    for d,r,b,S in ((-.13,.002,.2,.4),(.21,.08,.07,.7),(-.4,-.2,.25,1.)):
        normalizer=math.sqrt(2*math.pi*S)
        def density(u):
            return math.exp(-(u-b-d)**2/(2*S))/normalizer*(-math.expm1(-float(Z)*(u-b-r)**2/2))
        mass=quad(density,-math.inf,math.inf,epsabs=1e-11)[0]
        silence=math.exp(-(d-r)**2/(2*(S+1/float(Z))))/math.sqrt(1+float(Z)*S)
        error=abs(mass+silence-1)
        check("shifted_kernel_normalization",error<1e-10)
        mass_errors.append(error)
    policy = json.loads((HERE / "statistical_conventions.json").read_text(encoding="utf8"))
    old_protocol = json.loads((REVIEWS / "paper2_stage9_cumulative_evidence_20261123/stage9_protocol.json").read_text(encoding="utf8"))
    check("primary_setting_weights_sum_to_one",
          sum((F(row["weight"]) for row in policy["settings"]), F(0)) == 1)
    check("primary_settings_match_existing_cases",
          [(F(row["amplitude"]),row["evaluation_onset"]) for row in policy["settings"]] ==
          [(F(row["b"]),row["onset"]) for row in old_protocol["cases"]])
    check("healthy_effective_threshold_uses_existing_norm_scale",
          F(policy["healthy_action"]["effective_action_energy_threshold"]) ==
          F(str(policy["healthy_action"]["threshold_norm_display"]))**2 == F(1,1600))
    files=[HERE/"numerical_record.py",HERE/"interval_observation.py",Path(__file__),STAGE6/"vector_record.py",STAGE6/"model.json",
           STAGE6/"exact_linear.py",REVIEWS/"paper2_stage4_certified_correction_20261122/interval_arithmetic.py",
           REVIEWS/"paper2_stage5_certification_acceleration_20261122/strong_concavity.py",
           HERE/"README.md",HERE/"01_numerical_contract.md",HERE/"execution_status.md",
           HERE/"statistical_conventions.json",
           REVIEWS/"paper2_stage9_cumulative_evidence_20261123/stage9_protocol.json"]
    out={"status":"PASS","check_count":sum(counts.values()),"checks_by_kind":dict(counts),
         "deterministic_fixtures":len(fixtures),"maximum_display":{k:float(v) for k,v in maximum.items()},
         "examples":examples,"positive_synthetic_output_bounds":positives,
         "kernel_mass_errors":mass_errors,"source_sha256":{
             str(p.relative_to(REVIEWS.parent)).replace("\\","/"):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
         "new_random_performance_samples":0,
         "likelihood_reference":"independent direct physical kernels, Decimal 100-digit point diagnostics",
         "pollution_reference":"exact Fraction nominal and candidate filters",
         "risk_fixture_scope":"supplied outer intervals for algebraic checks"}
    out["environment"] = {"python": sys.version,
                          "numpy": np.__version__, "scipy": scipy.__version__}
    (HERE/"numerical_contract_checks.json").write_text(json.dumps(out,indent=2)+"\n",encoding="utf8",newline="\n")
    print(json.dumps(out,indent=2))


if __name__=="__main__":
    main()
