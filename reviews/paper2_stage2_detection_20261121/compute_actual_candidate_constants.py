"""Deterministic scalar bounds for persistent positive, send-only corruption.

Standard library only. No random sampling, no changes to prior result packages.
The quadrature entries are numerical checks, not the source of the bounds.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path


HERE = Path(__file__).resolve().parent
MODELS = (
    dict(id="S1", A=0.82, Q=0.05, R=0.2, P0=0.8, Z=2.0,
         delta=0.011628232298833967),
    dict(id="U1", A=1.04, Q=0.05, R=0.2, P0=0.8, Z=2.0,
         delta=0.022259755314928388),
)
AMPLITUDES = (0.05, 0.1, 0.25)


def riccati_root(A, Q, observation_variance):
    # Positive root of p = A^2 r p/(p+r) + Q.
    c = observation_variance - Q - A*A*observation_variance
    return 0.5*(-c + math.sqrt(c*c + 4*Q*observation_variance))


def bernoulli_kl(q, p):
    return q*math.log(q/p) + (1-q)*math.log((1-q)/(1-p))


def raw_gap_simpson(displacement, delta, V, intervals=512):
    """F(0)-F(d), paired +-errors; avoids cancellation of the odd term."""
    assert intervals % 2 == 0
    ed = math.exp(-displacement*displacement/(2*V))
    one_minus_ed = -math.expm1(-displacement*displacement/(2*V))
    total = 0.0
    for j in range(intervals+1):
        e = delta*j/intervals
        value = math.exp(-e*e/(2*V)) * (
            one_minus_ed - ed*2*math.sinh(displacement*e/(2*V))**2)
        weight = 1 if j in (0, intervals) else (4 if j % 2 else 2)
        total += weight*value
    # Mean on [0,delta], equal to the symmetric mean on [-delta,delta].
    return total/(3*intervals)


def main():
    rows = []
    checks = []
    for model in MODELS:
        A,Q,R,P0,Z,delta = (model[k] for k in ("A","Q","R","P0","Z","delta"))
        r0 = R+1/Z
        p_lo = riccati_root(A,Q,R)
        p_hi = max(P0,riccati_root(A,Q,r0))
        k_lo = p_lo/(p_lo+R)
        k_hi = p_hi/(p_hi+R)
        rho = A*r0/(p_lo+r0)
        V_lo = 1/Z + A*A*R*k_lo + Q + R
        V_hi_send = 1/Z + A*A*R*k_hi + Q + R
        nu_lo = math.exp(-delta*delta/(2*V_lo))/math.sqrt(Z*V_hi_send)
        nu_hi = 1/math.sqrt(Z*V_lo)
        p_send = 1-1/math.sqrt(1+Z*(p_lo+R))
        block_95 = math.ceil(math.log(0.05)/math.log1p(-p_send))
        assert P0 >= p_lo and rho < 1 and 0 < nu_lo <= nu_hi < 1
        assert abs(A*A*R*p_lo/(p_lo+R)+Q-p_lo) < 1e-14
        assert A*A*r0*p_hi/(p_hi+r0)+Q <= p_hi+1e-14
        for b in AMPLITUDES:
            bias_after_send = k_lo*b
            shift_after_send = A*bias_after_send
            bias_upper = k_hi*b/(1-rho)
            eps = (shift_after_send**2/(2*V_hi_send*math.sqrt(Z*V_hi_send))
                   * math.exp(-(shift_after_send**2+delta**2)/(2*V_lo)))
            q_lo = nu_lo-eps
            assert 0 < eps < nu_lo and q_lo < nu_hi < 1
            # KL(q||nu) = integral_q^nu (u-q)/(u(1-u)) du.
            # All u in [nu_lo-eps,nu_hi]; use its maximum Bernoulli variance.
            closest_half = min(nu_hi,max(q_lo,0.5))
            variance_max = closest_half*(1-closest_half)
            info = eps*eps/(2*variance_max)
            log_range = (math.log1p(eps/(1-nu_hi))
                         - math.log1p(-eps/nu_lo))
            # Implemented candidate: q=s*F(A*K*b), not nu-eps. Pairing +/-e
            # gives F(d)/F(0) >= exp(-d^2/(2V)). This bounds BOTH its tails.
            max_candidate_shift = A*k_hi*b
            implemented_log_negative_bound = max_candidate_shift**2/(2*V_lo)
            implemented_log_positive_bound = math.log1p(
                nu_hi/(1-nu_hi)*(-math.expm1(-implemented_log_negative_bound)))
            implemented_log_range = implemented_log_negative_bound+implemented_log_positive_bound
            numeric_min_gap = math.inf
            numeric_min_kl = math.inf
            implemented_min_gap = math.inf
            implemented_max_log_range = 0.0
            quadrature_refinement_error = 0.0
            for j in range(101):
                V = V_lo+(V_hi_send-V_lo)*j/100
                s = 1/math.sqrt(Z*V)
                gap = s*raw_gap_simpson(shift_after_send,delta,V)
                refined = s*raw_gap_simpson(shift_after_send,delta,V,1024)
                numeric_min_gap = min(numeric_min_gap,refined)
                quadrature_refinement_error = max(quadrature_refinement_error,abs(gap-refined))
                nu = nu_lo+(nu_hi-nu_lo)*j/100
                numeric_min_kl = min(numeric_min_kl,bernoulli_kl(nu-eps,nu))
                current_K = (V-1/Z-Q-R)/(A*A*R)
                f0 = math.sqrt(2*math.pi*V)/(2*delta)*math.erf(delta/math.sqrt(2*V))
                actual_nu = s*f0
                actual_gap = s*raw_gap_simpson(A*current_K*b,delta,V,1024)
                negative = math.log1p(-actual_gap/actual_nu)
                positive = math.log1p(actual_gap/(1-actual_nu))
                implemented_min_gap = min(implemented_min_gap,actual_gap)
                implemented_max_log_range = max(implemented_max_log_range,positive-negative)
                assert negative >= -implemented_log_negative_bound-1e-13
                assert positive <= implemented_log_positive_bound+1e-13
            assert numeric_min_gap >= eps*(1-1e-10)
            assert numeric_min_kl >= info*(1-1e-7)
            assert implemented_min_gap >= eps*(1-1e-10)
            row = dict(model=model["id"],b=b,delta=delta,
                prior_variance_lower=p_lo,prior_variance_upper=p_hi,
                send_gain_lower=k_lo,send_gain_upper=k_hi,silent_contraction_upper=rho,
                analysis_bias_upper=bias_upper,
                bias_lower_conditional_on_current_send=bias_after_send,
                next_prediction_shift_lower_conditional_on_current_send=shift_after_send,
                next_kernel_V_lower=V_lo,next_kernel_V_upper_conditional_on_current_send=V_hi_send,
                nu_lower_conditional_on_current_send=nu_lo,
                nu_upper_conditional_on_current_send=nu_hi,
                epsilon_lower_conditional_on_current_send=eps,
                bernoulli_information_pinsker_lower_conditional_on_current_send=2*eps*eps,
                bernoulli_information_lower_conditional_on_current_send=info,
                constant_epsilon_candidate_only_log_lr_range_upper_on_current_send=log_range,
                implemented_candidate_maximum_prediction_shift=max_candidate_shift,
                implemented_candidate_log_factor_lower=-implemented_log_negative_bound,
                implemented_candidate_log_factor_upper=implemented_log_positive_bound,
                implemented_candidate_log_lr_range_upper_on_current_send=implemented_log_range,
                send_probability_lower=p_send,
                mean_information_lower_per_action_after_averaging_send_opportunity=p_send*info,
                block_length_for_at_least_one_send_with_probability_95pct=block_95,
                block_send_probability_lower={str(L):1-(1-p_send)**L for L in (4,8,16,32)},
                count_lower_tail_rate_at_half_minimum_send_rate=bernoulli_kl(p_send/2,p_send),
                per_time_almost_sure_positive_bias_lower=0.0,
                per_time_almost_sure_positive_information_lower=0.0)
            rows.append(row)
            checks.append(dict(model=model["id"],b=b,
                phase_gap_101_point_grid_min=numeric_min_gap,
                certified_epsilon=eps,
                paired_simpson_512_to_1024_max_difference=quadrature_refinement_error,
                kl_101_point_grid_min=numeric_min_kl,
                implemented_candidate_gap_101_point_grid_min=implemented_min_gap,
                implemented_candidate_log_range_101_point_grid_max=implemented_max_log_range,
                implemented_candidate_certified_log_range_upper=implemented_log_range,
                certified_information=info,status="PASS"))
    obj = dict(base_commit="8cf49e73",purpose="send-conditional bounds; not per-time a.s. bounds",
        implemented_candidate="after send q=s(Ppost)*F(A*K*b_j); after silence q=nu",
        constant_epsilon_candidate="theoretical comparator q=nu-gamma*epsilon_b; its range is not the implemented candidate range",
        assumptions=["A>0,Q>0; P0 >= the all-send Riccati fixed point",
            "no attack before onset; action=b only after a trusted true send",
            "fresh full-period uniform phase after payload commitment",
            "the provisional monitor drives the actual sensor center",
            "unmodified scalar Gaussian process, trusted event bits"],
        amplitudes=list(AMPLITUDES),models=list(MODELS),rows=rows,
        verification=dict(random_samples_generated=False,standard_library_only=True,
            numeric_checks_are_not_certified_global_optimizations=True,checks=checks),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (HERE/"constants_actual_candidate.json").write_text(json.dumps(obj,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    for row in rows:
        print(row["model"],row["b"],"eps",format(row["epsilon_lower_conditional_on_current_send"],".9g"),
              "I",format(row["bernoulli_information_lower_conditional_on_current_send"],".9g"),
              "send_p",format(row["send_probability_lower"],".9g"))


if __name__ == "__main__":
    main()
