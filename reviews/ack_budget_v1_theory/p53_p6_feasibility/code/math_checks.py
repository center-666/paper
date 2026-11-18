"""Fixed algebra checks only: no simulator, trajectories, RNG, or calibration."""
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
EDGES = [(j, i) for j in range(5) for i in range(5) if j != i]
OBS = [0, 1, 0, 1, 0]
A = [Q(51, 50), Q(101, 100)]
K = Q(3, 5)
C = [Q(51, 5000)*a for a in A]


def zero(n, m):
    return [[Q(0) for _ in range(m)] for _ in range(n)]


def mv(M, v):
    return [sum((x*y for x, y in zip(row, v)), Q(0)) for row in M]


def dot(x, y):
    return sum((a*b for a, b in zip(x, y)), Q(0))


def plus(x, y):
    return [a+b for a, b in zip(x, y)]


def minus(x, y):
    return [a-b for a, b in zip(x, y)]


def construct():
    F, D, J, S = zero(10, 10), zero(10, 40), zero(10, 10), zero(40, 10)
    for i in range(5):
        for r in range(2):
            F[2*i+r][2*i+r] = A[r] - (K if OBS[i] == r else 0) - 4*C[r]
            for j in range(5):
                if j != i:
                    F[2*i+r][2*j+r] = C[r]
    for l, (j, i) in enumerate(EDGES):
        for r in range(2):
            D[2*i+r][2*l+r] = C[r]
            S[2*l+r][2*j+r] = Q(1)
    for i in range(10):
        for j in range(10):
            J[i][j] = (A[i % 2] if i == j else 0) - F[i][j]
    return F, D, J, S


def algebra():
    F, D, J, S = construct()
    checks = []
    # Fixed mathematical vectors are not plant or estimator trajectories.
    for case in range(7):
        e = [Q(((n+2)*(case+3)) % 17 - 8, 7) for n in range(10)]
        d = [Q(((n+1)*(case+5)) % 23 - 11, 9) for n in range(40)]
        rhs = plus(mv(F, e), mv(D, d))
        literal = []
        for i in range(5):
            for r in range(2):
                val = (A[r] - (K if OBS[i] == r else 0))*e[2*i+r]
                for l, (j, dest) in enumerate(EDGES):
                    if dest == i:
                        val += C[r]*(e[2*j+r]-e[2*i+r]+d[2*l+r])
                literal.append(val)
        assert literal == rhs
        # Same past, successful link reset: b_send=b_wait-D_l d_l.
        for l in range(20):
            action = [Q(0)]*40
            action[2*l:2*l+2] = d[2*l:2*l+2]
            v = mv(D, action)
            direct = dot(rhs, rhs) - dot(minus(rhs, v), minus(rhs, v))
            formula = 2*dot(rhs, v) - dot(v, v)
            assert direct == formula
        # Joint action interaction, not sum of isolated benefits.
        for l, m in [(0, 1), (0, 8), (3, 7), (8, 16)]:
            acts = []
            for index in (l, m):
                action = [Q(0)]*40
                action[2*index:2*index+2] = d[2*index:2*index+2]
                acts.append(mv(D, action))
            v, w = acts
            f = lambda q: 2*dot(rhs, q)-dot(q, q)
            assert f(plus(v, w)) == f(v)+f(w)-2*dot(v, w)
        # Exact two-point distribution, not a physical trajectory:
        # e=mu+sign*u, d=dbar+sign*h retains nonzero cross covariance.
        u = [Q((n+case) % 5-2, 11) for n in range(10)]
        h = [Q((n+2*case) % 7-3, 13) for n in range(40)]
        m = plus(mv(F, e), mv(D, d))
        spread = plus(mv(F, u), mv(D, h))
        expected = (dot(plus(m, spread), plus(m, spread)) +
                    dot(minus(m, spread), minus(m, spread)))/2
        covariance_formula = dot(m, m)+dot(mv(F, u), mv(F, u)) + \
            2*dot(mv(F, u), mv(D, h))+dot(mv(D, h), mv(D, h))
        assert expected == covariance_formula
        checks.append(case)
    # Exact covariance contribution of common process noise and independent v.
    omega = zero(10, 10)
    for i in range(5):
        for j in range(5):
            for r in range(2):
                omega[2*i+r][2*j+r] = Q(1, 50)
                if i == j and OBS[i] == r:
                    omega[2*i+r][2*j+r] += K*K*Q(1, 5)
    trace = sum(omega[i][i] for i in range(10))
    assert trace == Q(14, 25)
    # Row sums cancel consensus: F(1 tensor I)=col(A-K_i H_i).
    for i in range(5):
        for r in range(2):
            assert sum(F[2*i+r][2*j+r] for j in range(5)) == \
                A[r]-(K if OBS[i] == r else 0)
    # A distribution-level oracle sign example, explicitly not a reachable plant case.
    v, wait_mean_1, wait_mean_2 = [Q(1)], [Q(0)], [Q(1)]
    signs = [2*dot(mu, v)-dot(v, v) for mu in (wait_mean_1, wait_mean_2)]
    assert signs == [-1, 1]
    return F, D, J, S, dict(exact_error_identity_cases=len(checks),
            exact_single_link_benefit_cases=7*20,
            exact_joint_interaction_cases=7*4,
            exact_correlated_conditional_moment_cases=7,
            trace_fresh_noise_total=str(trace),
            trace_fresh_noise_per_node=str(trace/5),
            generic_sign_example=[str(x) for x in signs],
            generic_sign_example_is_not_reachable_network_evidence=True)


def certificate(F, D, J, S):
    f = lambda x: np.array(x, dtype=float)
    F, D, J, S = map(f, (F, D, J, S))
    H1 = np.diag([float(a) for _ in EDGES for a in A]) @ S
    M = np.block([[abs(F), abs(D)@S, abs(D)@H1],
                  [abs(J), abs(D)@S, abs(D)@H1],
                  [np.zeros((10, 10)), np.eye(10), np.zeros((10, 10))]])
    h = np.array([float(a*a*Q(1, 5)) for _ in EDGES for a in A])
    eta = np.array([.31 if OBS[i] == r else .15 for i in range(5) for r in range(2)])
    kv = np.array([.27 if OBS[i] == r else 0 for i in range(5) for r in range(2)])
    g = np.concatenate((abs(D)@h+eta, abs(D)@h+kv, np.zeros(10)))
    bar = np.linalg.solve(np.eye(30)-M, g)
    rho = float(max(abs(np.linalg.eigvals(M))))
    bound = (bar[:10].reshape(5, 2)**2).sum(axis=1)
    expected = np.array([3391.677064, 1783.993595, 3391.677064, 1783.993595, 3391.677064])
    assert max(abs(bound-expected)) < .000006
    assert rho < 1 and min(bar) > 0 and np.all(bar >= np.r_[np.ones(10), np.zeros(20)])
    return dict(rho_M=rho, node_unconditional_certificate=bound.tolist(),
                frozen_table_max_abs_difference=float(max(abs(bound-expected))),
                certificate_is_not_a_conditional_bound=True,
                parameters_unchanged=True)


def conditional_initial_example():
    # Analytic regular conditional law at k=1 after initial measurement y0.
    # All five scalar y0=t; each directed packet blocked legally at first tick.
    # No realization, state recursion or random sample is generated.
    coef, variance = Q(0), Q(0)
    after_coef, after_variance = Q(0), Q(0)
    for r in range(2):
        n = OBS.count(r)
        post_var_x0 = 1 / (1 + Q(n)/Q(1, 5))
        mean_x1_per_t = A[r]*Q(n)/(Q(n)+Q(1, 5))
        var_x1 = A[r]**2*post_var_x0 + Q(1, 50)
        for i in range(5):
            delta = mean_x1_per_t - (K if OBS[i] == r else 0)
            coef += delta*delta
            variance += var_x1
            tmap = A[r]-(K if OBS[i] == r else 0)
            hat1_coef = K if OBS[i] == r else Q(0)
            next_delta = tmap*mean_x1_per_t-(tmap-4*C[r])*hat1_coef
            after_coef += next_delta*next_delta
            after_variance += tmap*tmap*var_x1+Q(1, 50) + \
                (K*K*Q(1, 5) if OBS[i] == r else 0)
    # E[||e1||^2 | all y0=t]=variance+coef*t^2.
    assert coef > 0
    # Independent full-network identity for the e2 conditional expression.
    F, D, _, S = construct()
    mean1 = [A[r]*Q(OBS.count(r))/(Q(OBS.count(r))+Q(1, 5))
             for i in range(5) for r in range(2)]
    hats = [K if OBS[i] == r else Q(0) for i in range(5) for r in range(2)]
    coef2_vector = plus(mv(F, minus(mean1, hats)), mv(D, mv(S, hats)))
    assert dot(coef2_vector, coef2_vector) == after_coef
    covariance1 = zero(10, 10)
    for i in range(5):
        for j in range(5):
            for r in range(2):
                covariance1[2*i+r][2*j+r] = \
                    A[r]**2/(1+Q(OBS.count(r))/Q(1, 5))+Q(1, 50)
    matrix_variance = sum(
        F[row][i]*covariance1[i][j]*F[row][j]
        for row in range(10) for i in range(10) for j in range(10)) + Q(14, 25)
    assert matrix_variance == after_variance
    return dict(time=1, condition="regular conditional y_i,0=t for all i; t>1/3",
                all_initial_attempts_blocked_legal_when_B_at_least_1=True,
                exact_total_conditional_MSE_coefficient=str(coef),
                exact_total_conditional_MSE_constant=str(variance),
                coefficient_float=float(coef), constant_float=float(variance),
                after_first_communication_target_time=2,
                exact_total_conditional_MSE_e2_coefficient=str(after_coef),
                exact_total_conditional_MSE_e2_constant=str(after_variance),
                e2_coefficient_float=float(after_coef),
                e2_constant_float=float(after_variance),
                e2_checked_against_full_F_D_shared_covariance=True,
                grows_unbounded_with_t=True,
                actual_noise_or_state_trajectory_generated=False)


def support_margins():
    # Finite-horizon uniform bound for the unused coordinate:
    # max over node estimates and predicted/post caches <= M at a tick.
    # cache <= max(A M, M), update <= (A+K+4C) M +4C A M +K eps.
    a, c = max(A), max(C)
    g = a+K+4*c+4*c*a
    horizon_bounds = []
    for T in (1, 6, 20, 41):
        q = Q(0)
        for _ in range(T):
            q = g*q+K
        residual_bound_per_eps = (1+a)*q
        eps = Q(1, 5)/(4*(1+residual_bound_per_eps))
        assert eps*residual_bound_per_eps < Q(1, 20)
        horizon_bounds.append(dict(T=T, epsilon_other_coordinate=str(eps),
                                    epsilon_float=float(eps),
                                    unobserved_residual_less_than_theta_over_4=True))
    theta = Q(1, 5)
    assert 2*(theta/4)**2 < theta**2
    assert 2*theta-theta/4 > theta
    return dict(low_squared_norm_upper=str(2*(theta/4)**2),
                threshold_squared=str(theta**2),
                high_observed_coordinate_lower=str(2*theta-theta/4),
                examples=horizon_bounds,
                finite_horizon_analytic_bounds_not_trajectory_samples=True)


def main():
    F, D, J, S, result = algebra()
    output = dict(status="PASS", scope="fixed matrix and rational identities only",
                  algebra=result, old_certificate=certificate(F, D, J, S),
                  conditional_initial_example=conditional_initial_example(),
                  support_tube_margins=support_margins(),
                  numpy_version=np.__version__, python_version=sys.version,
                  simulations=0, random_samples=0, experiment_runs=0)
    data = (json.dumps(output, indent=2)+"\n").encode()
    out = ROOT/"data"/"math_checks.json"
    if "--verify" in sys.argv:
        assert out.read_bytes() == data
        print("PASS: deterministic algebra outputs match saved bytes")
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
