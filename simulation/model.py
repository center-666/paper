"""Five-node Yang-form research model. Nominal gain reproduction, not full-paper reproduction."""
from __future__ import annotations
from dataclasses import dataclass
import json
from pathlib import Path
import numpy as np


@dataclass
class Model:
    cfg: dict
    A: np.ndarray
    Q: np.ndarray
    P0: np.ndarray
    H: np.ndarray
    R: np.ndarray
    edges: np.ndarray
    powers: np.ndarray
    gains: np.ndarray
    local_gains: np.ndarray
    nominal_covariance: np.ndarray

    @classmethod
    def build(cls, cfg: dict) -> "Model":
        N, n, T = cfg["N"], cfg["n"], cfg["T"]
        A, Q, P0 = (np.asarray(cfg[k], float) for k in ("A", "Q", "P0"))
        H = np.asarray(cfg["H_matrices"],float) if "H_matrices" in cfg else np.asarray([s * np.eye(n) for s in cfg["H_scales"]])
        R = np.asarray(cfg["R_matrices"],float) if "R_matrices" in cfg else np.asarray([r * np.eye(n) for r in cfg["R_variances"]])
        assert H.shape==(N,n,n) and R.shape==(N,n,n)
        edges = np.asarray(cfg["edges_sender_receiver"], int)
        assert len(set(map(tuple, edges))) == len(edges)
        assert np.all(edges[:, 0] != edges[:, 1])
        assert np.all((edges >= 0) & (edges < N))
        degree = np.bincount(edges[:, 1], minlength=N)
        assert 0 < cfg["epsilon"] < 1 / degree.max()
        powers = np.stack([np.linalg.matrix_power(A, k) for k in range(T + 1)])
        gains, covariance = nominal_gains(A, Q, P0, H, R, edges, cfg["epsilon"], T)
        local_gains, _ = nominal_gains(A, Q, P0, H, R, edges, 0.0, T)
        return cls(cfg, A, Q, P0, H, R, edges, powers, gains, local_gains, covariance)


def nominal_gains(A, Q, P0, H, R, edges, epsilon, T):
    """q=1, instantaneous all-link messages; exact joint covariance recursion.

    K_i = (B P)_{ii} H_i^T (H_i P_ii H_i^T + R_i)^-1,
    B = (I-epsilon*L) kron A. Shared process noise uses ones(N,N) kron Q.
    Event-triggered/robust runs reuse these gains as NOMINAL gains only.
    """
    N, n = len(H), A.shape[0]
    mixing = np.eye(N)
    for j, i in edges:
        mixing[i, i] -= epsilon
        mixing[i, j] += epsilon
    B = np.kron(mixing, A)
    P = np.kron(np.ones((N, N)), P0)  # all initial estimates are zero
    W = np.kron(np.ones((N, N)), Q)
    gains = np.empty((T, N, n, n))
    covariances = [P.copy()]
    for t in range(T):
        BP = B @ P
        F = B.copy()
        noise = W.copy()
        for i in range(N):
            sl = slice(i*n, (i+1)*n)
            S = H[i] @ P[sl, sl] @ H[i].T + R[i]
            K = np.linalg.solve(S, (BP[sl, sl] @ H[i].T).T).T
            gains[t, i] = K
            F[sl, sl] -= K @ H[i]
            noise[sl, sl] += K @ R[i] @ K.T
        P = F @ P @ F.T + noise
        P = (P + P.T) / 2
        if np.linalg.eigvalsh(P)[0] < -1e-9:
            raise ArithmeticError("Nominal covariance lost PSD")
        covariances.append(P.copy())
    return gains, np.asarray(covariances)


def load_model(path: str | Path) -> Model:
    return Model.build(json.loads(Path(path).read_text(encoding="utf-8-sig")))


def seed_range(cfg: dict, split: str) -> np.ndarray:
    s = cfg[split + "_seeds"]
    return np.arange(s["start"], s["start"] + s["count"])


def generate_data(model: Model, seeds: np.ndarray):
    cfg = model.cfg
    S, T, N, n = len(seeds), cfg["T"], cfg["N"], cfg["n"]
    x = np.empty((S, T+1, n))
    y = np.empty((S, T, N, n))
    lq, lp = np.linalg.cholesky(model.Q), np.linalg.cholesky(model.P0)
    lr = np.linalg.cholesky(model.R)
    for s, seed in enumerate(seeds):
        rng = np.random.default_rng(int(seed))
        x[s, 0] = lp @ rng.standard_normal(n)
        process = rng.standard_normal((T, n)) @ lq.T
        measurement = np.einsum("tij,ikj->tik", rng.standard_normal((T, N, n)), lr)
        for t in range(T):
            y[s, t] = np.einsum("imn,n->im", model.H, x[s, t]) + measurement[t]
            x[s, t+1] = model.A @ x[s, t] + process[t]
    return x, y


def diagonal_blocks(P: np.ndarray, N: int, n: int):
    return np.stack([P[..., i*n:(i+1)*n, i*n:(i+1)*n] for i in range(N)], axis=-3)
