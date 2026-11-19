"""Deterministic P1-B algebra checks. No random draws or Monte Carlo."""
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "simulation"))
from model import load_model, nominal_gains


def assemble_B(N, A, edges, epsilon):
    mix = np.eye(N)
    for sender, receiver in edges:
        mix[receiver, receiver] -= epsilon
        mix[receiver, sender] += epsilon
    return np.kron(mix, A)


def explicit_update_covariance(A, Q, P, H, R, B, gains):
    N, n = len(H), A.shape[0]
    Hbar = np.zeros((N*n, N*n))
    Rbar = np.zeros_like(Hbar)
    Kbar = np.zeros_like(Hbar)
    for i in range(N):
        s = slice(i*n, (i+1)*n)
        Hbar[s, s] = H[i]
        Rbar[s, s] = R[i]
        Kbar[s, s] = gains[i]
    F = B - Kbar @ Hbar
    return F @ P @ F.T + np.kron(np.ones((N, N)), Q) + Kbar @ Rbar @ Kbar.T, F


def main():
    model = load_model(ROOT / "simulation/config.json")
    cfg = model.cfg
    N, n, T = cfg["N"], cfg["n"], cfg["T"]
    eps = cfg["epsilon"]
    B = assemble_B(N, model.A, model.edges, eps)
    I = np.eye(n)
    G = np.zeros((N*n, n))
    G[n:2*n] = eps * model.A  # edge 0 -> 1 injects only into receiver 1

    # Asymmetric H and full SPD R expose the P_ij versus P_ji orientation.
    H = np.array([
        [[1.00, 0.27], [-0.16, 0.91]],
        [[0.82, -0.21], [0.13, 1.14]],
        [[1.19, 0.18], [-0.31, 0.76]],
        [[0.93, -0.26], [0.22, 1.07]],
        [[1.08, 0.33], [-0.12, 0.88]],
    ])
    R = np.array([
        [[0.060, 0.012], [0.012, 0.085]],
        [[0.070, -0.011], [-0.011, 0.055]],
        [[0.050, 0.009], [0.009, 0.075]],
        [[0.065, -0.008], [-0.008, 0.090]],
        [[0.080, 0.014], [0.014, 0.060]],
    ])
    assert min(np.linalg.eigvalsh(r)[0] for r in R) > 0
    gains, pref = nominal_gains(model.A, model.Q, model.P0, H, R, model.edges, eps, 3)
    P = np.kron(np.ones((N, N)), model.P0)
    paper_gap = 0.0
    gain_lmmse_error = 0.0
    cov_error = 0.0
    cross_asymmetry = 0.0
    cross_orientation_gap = 0.0
    for t in range(3):
        Bp = B @ P
        for i in range(N):
            s = slice(i*n, (i+1)*n)
            S = H[i] @ P[s, s] @ H[i].T + R[i]
            K_lmmse = Bp[s, s] @ H[i].T @ np.linalg.inv(S)
            gain_lmmse_error = max(gain_lmmse_error, np.max(np.abs(gains[t, i] - K_lmmse)))

            # Yang et al. (2014), printed Eq. (9), uses P_{i,s}; Eq. (8)
            # defines P_{i,s}=E[e_i e_s^T].
            js = model.edges[model.edges[:, 1] == i, 0]
            block = P[s, s].copy()
            for j in js:
                sj = slice(j*n, (j+1)*n)
                block += eps * (P[s, sj] - P[s, s])
            K_yang_printed = model.A @ block @ H[i].T @ np.linalg.inv(S)
            paper_gap = max(paper_gap, np.max(np.abs(gains[t, i] - K_yang_printed)))

            for j in range(N):
                sj = slice(j*n, (j+1)*n)
                cross_asymmetry = max(cross_asymmetry, np.max(np.abs(P[s, sj] - P[sj, s].T)))
                cross_orientation_gap = max(cross_orientation_gap, np.max(np.abs(P[s, sj] - P[sj, s])))
        Pnext, _ = explicit_update_covariance(model.A, model.Q, P, H, R, B, gains[t])
        P = (Pnext + Pnext.T) / 2
        cov_error = max(cov_error, np.max(np.abs(P-pref[t+1])))
        if t < 2:
            # Recompute the next gain independently via the explicit LMMSE block formula.
            for i in range(N):
                s = slice(i*n, (i+1)*n)
                S = H[i] @ P[s, s] @ H[i].T + R[i]
                direct = (B @ P)[s, s] @ H[i].T @ np.linalg.inv(S)
                gain_lmmse_error = max(gain_lmmse_error, np.max(np.abs(gains[t+1, i] - direct)))

    # Baseline frozen model: exact P1-A gain/covariance agreement remains intact.
    base_model = model
    baseline_orientation_gap = 0.0
    for Pc in base_model.nominal_covariance:
        for i in range(N):
            si = slice(i*n, (i+1)*n)
            for j in range(N):
                sj = slice(j*n, (j+1)*n)
                baseline_orientation_gap = max(baseline_orientation_gap,
                    np.max(np.abs(Pc[si, sj] - Pc[sj, si])))
    # Response matrix from a_200:249 (100-vector) to Delta_201:300 (1000-vector).
    Fbase = []
    for t in range(T):
        F = B.copy()
        for i in range(N):
            s = slice(i*n, (i+1)*n)
            F[s, s] -= base_model.gains[t, i] @ base_model.H[i]
        Fbase.append(F)
    Fbase = np.asarray(Fbase)
    Ms = []
    for t in range(200, 250):
        beta = np.array([0.2*np.sin(0.03*t), 0.3*np.cos(0.02*t)])
        Ms.append(0.5*I + np.outer(beta, beta))
    response = np.zeros((100*N*n, 50*n))
    for out_idx, k in enumerate(range(201, 301)):
        for inp_idx, t in enumerate(range(200, 250)):
            if k < t+1:
                continue
            phiG = G.copy()
            for sidx in range(t+1, k):
                phiG = Fbase[sidx] @ phiG
            response[out_idx*N*n:(out_idx+1)*N*n, inp_idx*n:(inp_idx+1)*n] = phiG @ Ms[inp_idx]
    assert response.shape == (1000, 100)
    # Causality and graph propagation: first affected state is node 1 at t+1.
    first = response[0:N*n, 0:n]
    expected_first = G @ Ms[0]
    first_error = np.max(np.abs(first - expected_first))
    forbidden = np.max(np.abs(response[0:N*n, n:]))
    # A deterministic fixed action and fixed M sequence must match the full matrix map.
    action = np.array([0.17, -0.23])
    u = np.tile(action, 50)
    mapped = response @ u
    delta = np.zeros(N*n)
    direct_outputs = []
    for k in range(201, 301):
        # propagate all input times that have already arrived
        if k == 201:
            delta = G @ Ms[0] @ action
        else:
            delta = Fbase[k-1] @ delta
            if 200 <= k-1 <= 249:
                delta += G @ Ms[k-1-200] @ action
        direct_outputs.extend(delta)
    response_error = np.max(np.abs(mapped - np.asarray(direct_outputs)))
    lag_support = {}
    for lag, expected_nodes in ((0, [1]), (1, [0, 1, 2]), (2, [0, 1, 2, 3, 4])):
        inp_idx = 0
        out_idx = lag
        blockrow = response[out_idx*N*n:(out_idx+1)*N*n, inp_idx*n:(inp_idx+1)*n]
        got_nodes = [i for i in range(N) if np.linalg.norm(blockrow[i*n:(i+1)*n]) > 1e-14]
        lag_support[str(lag)] = got_nodes
        assert got_nodes == expected_nodes

    # Continue only the deterministic covariance/gain recursion, not sample paths.
    P = model.nominal_covariance[-1].copy()
    max_tail_step = 0.0
    min_eigenvalue = np.linalg.eigvalsh(P)[0]
    max_trace = float(np.trace(P))
    rho_final = float("nan")
    for _ in range(10_000):
        Bp = B @ P
        K = np.zeros((N, n, n))
        for i in range(N):
            s = slice(i*n, (i+1)*n)
            S = model.H[i] @ P[s, s] @ model.H[i].T + model.R[i]
            K[i] = np.linalg.solve(S, (Bp[s, s] @ model.H[i].T).T).T
        Pnext, Fnext = explicit_update_covariance(model.A, model.Q, P, model.H, model.R, B, K)
        Pnext = (Pnext + Pnext.T) / 2
        max_tail_step = max(max_tail_step, np.linalg.norm(Pnext-P, ord=2))
        min_eigenvalue = min(min_eigenvalue, float(np.linalg.eigvalsh(Pnext)[0]))
        max_trace = max(max_trace, float(np.trace(Pnext)))
        P = Pnext
        rho_final = float(np.max(np.abs(np.linalg.eigvals(Fnext))))

    # Gaussian moment identities via Isserlis' formula, no random sampling.
    lam, sigma2, dim = 0.5, 0.5, 2
    EM = (lam + sigma2) * I
    EMtM = (lam**2 + 2*lam*sigma2 + (dim+2)*sigma2**2) * I
    operator_second_moment = lam**2 + 2*lam*dim*sigma2 + dim*(dim+2)*sigma2**2
    assert np.max(np.abs(EM-I)) < 1e-15
    assert np.max(np.abs(EMtM-1.75*I)) < 1e-15

    result = {
        "non_symmetric_gain_lmmse_error": float(gain_lmmse_error),
        "printed_yang_eq9_general_matrix_max_gap": float(paper_gap),
        "cross_covariance_block_symmetry_max": float(cross_asymmetry),
        "cross_covariance_orientation_gap_max": float(cross_orientation_gap),
        "baseline_scalar_isotropic_orientation_gap_max": float(baseline_orientation_gap),
        "joint_covariance_independent_assembly_error": float(cov_error),
        "response_matrix_shape": list(response.shape),
        "response_first_block_error": float(first_error),
        "response_causality_zero_max": float(forbidden),
        "response_vs_direct_recursion_error": float(response_error),
        "response_node_support_by_lag": lag_support,
        "E_M": EM.tolist(),
        "E_MtM": EMtM.tolist(),
        "E_spectral_norm_M_squared": float(operator_second_moment),
        "deterministic_covariance_steps_after_400": 10_000,
        "deterministic_covariance_final_trace": float(np.trace(P)),
        "deterministic_covariance_max_trace": max_trace,
        "deterministic_covariance_min_eigenvalue": min_eigenvalue,
        "deterministic_covariance_max_step_change": max_tail_step,
        "final_error_matrix_spectral_radius": rho_final,
    }
    for key, value in result.items():
        print(f"{key}: {value}")
    assert max(gain_lmmse_error, cov_error, first_error, forbidden, response_error) < 1e-9


if __name__ == "__main__":
    main()
