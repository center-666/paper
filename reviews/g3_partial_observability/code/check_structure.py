"""Matrix-only G3 structure audit. No data generation, simulator or Monte Carlo."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parents[1]
PLAN = BASE / "plan.json"


def rank(matrix):
    return int(np.linalg.matrix_rank(matrix, tol=1e-10))


def observation(A, H):
    O = np.concatenate([H @ np.linalg.matrix_power(A, k) for k in range(len(A))])
    modes = []
    for lam in np.linalg.eigvals(A):
        modes.append({"eigenvalue": float(np.real(lam)),
                      "pbh_rank": rank(np.concatenate([lam*np.eye(len(A))-A, H])),
                      "requires_detection": bool(abs(lam) >= 1-1e-12)})
    return {"observability_rank": rank(O), "observable": rank(O) == len(A),
            "detectable": all(m["pbh_rank"] == len(A) for m in modes if m["requires_detection"]),
            "pbh": modes}


def augmented_matrix(A, H, gains, edges, fresh, epsilon):
    """z=(e_i(t), c_edge(t)); c is pre-reception age-aligned cache error.

    Receive map D replaces fresh c with current sender error. e(t+1) follows
    Yang update; next pre-receive c(t+1)=A*c_after_receive(t)+shared process noise.
    Fixed gains here are arbitrary test matrices, not fitted or stability claims.
    """
    N, n, E = len(H), len(A), len(edges)
    size = (N+E)*n
    D = np.zeros((E*n, size))
    for edge, (sender, _) in enumerate(edges):
        start = sender*n if fresh[edge] else (N+edge)*n
        D[edge*n:(edge+1)*n, start:start+n] = np.eye(n)
    M = np.zeros((size, size))
    degree = np.bincount(edges[:, 1], minlength=N)
    for node in range(N):
        sl = slice(node*n, (node+1)*n)
        M[sl, sl] = A-gains[node]@H[node]-epsilon*degree[node]*A
    for edge, (_, receiver) in enumerate(edges):
        esl = slice(edge*n, (edge+1)*n)
        M[receiver*n:(receiver+1)*n] += epsilon*A@D[esl]
        M[(N+edge)*n:(N+edge+1)*n] = A@D[esl]
    return M


def main():
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    cfg = plan["model"]
    A, H = np.asarray(cfg["A"]), np.asarray(cfg["partial_H"])
    edges = np.asarray(cfg["edges_sender_receiver"], dtype=int)
    N, n, E = cfg["N"], cfg["n"], len(edges)
    # Deterministic nonzero matrices and state vector check block assembly only.
    gains = np.arange(N*n*n, dtype=float).reshape(N,n,n)/101
    z = np.arange((N+E)*n, dtype=float)/7
    errors, cache = z[:N*n].reshape(N,n), z[N*n:].reshape(E,n)
    patterns = {"all_fresh": np.ones(E, bool), "none_fresh": np.zeros(E, bool),
                "mixed": (np.arange(E)%3 == 0)}
    checks = {}
    for name, fresh in patterns.items():
        M = augmented_matrix(A,H,gains,edges,fresh,cfg["epsilon"])
        received = np.where(fresh[:,None], errors[edges[:,0]], cache)
        expected = errors@A.T - np.einsum("ijk,ik->ij",gains,np.einsum("ijk,ik->ij",H,errors))
        for edge, (_, receiver) in enumerate(edges):
            expected[receiver] += cfg["epsilon"]*A@(received[edge]-errors[receiver])
        expected = np.r_[expected.ravel(),(received@A.T).ravel()]
        residual = float(np.max(np.abs(M@z-expected)))
        assert residual < 1e-12
        checks[name] = {"matrix_shape": list(M.shape), "assembly_max_abs_error": residual,
                        "fresh_uses_current_sender_error": True}
    report = {
        "run_id": "2026-11-13_g3_matrix_structure_v2",
        "scope": "deterministic matrix structure only; no simulator, data generation, calibration or Monte Carlo",
        "plan_sha256": hashlib.sha256(PLAN.read_bytes()).hexdigest(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "partial_nodes": [observation(A,h) for h in H],
        "partial_network": observation(A,np.concatenate(H)),
        "reference_nodes": [observation(A,np.asarray(h)) for h in cfg["full_rank_reference_H"]],
        "receiver_physical_unobservable_direction": {"direction":[1,0],
            "H_A_power_direction_k_0_to_5": [(H[1]@np.linalg.matrix_power(A,k)@np.array([1.,0.])).tolist() for k in range(6)]},
        "augmented_cache_assembly": checks,
        "status": "structure checks passed; normal stability/cooperation/Gate A/Gate B pending",
        "limitations": ["arbitrary gains only validate algebraic assembly, not current fitted gain stability",
                       "no claim of equivalence to engine from this one-step algebra test alone",
                       "joint observability does not certify sparse-cache estimator stability",
                       "finite impulse output sensitivity and conditional incremental evidence not yet evaluated"]
    }
    target = BASE / "results" / report["run_id"] / "structure_check.json"
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():
        raise FileExistsError("Refusing to overwrite an existing structure result")
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"result": str(target), "status": report["status"]},ensure_ascii=False))


if __name__ == "__main__":
    main()
