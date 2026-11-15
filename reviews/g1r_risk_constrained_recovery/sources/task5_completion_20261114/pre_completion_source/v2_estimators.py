"""Frozen v2 Hard/Soft/Set proposal estimators.

The online public interface is propose(z, frozen_public_model).  It has no
simulator, event labels, true state, replay source, or unsent neighbor data.
Normal calibration thresholds are applied separately by ``apply_gate``.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
from scipy.optimize import minimize, minimize_scalar
from scipy.special import logsumexp


EPS = np.finfo(np.float64).eps
U_DEFAULT = 0.051261


@dataclass(frozen=True)
class Ellipse:
    center: np.ndarray
    shape: np.ndarray  # d x d; set may be rank deficient
    event: tuple[int, int]


@dataclass
class Proposal:
    method: str
    action: np.ndarray
    score: float
    status: str
    event: tuple[int, int] | None = None
    certificate: dict | None = None


def _fail(method: str, dim: int, status: str, certificate=None) -> Proposal:
    return Proposal(method, np.zeros(dim), 0.0, status, None, certificate or {})


def _radial_cap(x: np.ndarray, cap: float) -> np.ndarray:
    x = np.asarray(x, dtype=np.float64)
    norm = float(np.linalg.norm(x))
    if norm <= cap or norm == 0.0:
        return x.copy()
    return x * (np.nextafter(float(cap), 0.0) / norm)


def apply_gate(proposal: Proposal, threshold: float) -> Proposal:
    """Apply the frozen strict upper-tail threshold; no equality alarms."""
    if proposal.status != "VALID":
        return Proposal(proposal.method, np.zeros_like(proposal.action), 0.0,
                        proposal.status, proposal.event, proposal.certificate)
    if not (math.isfinite(threshold) and proposal.score > threshold):
        return Proposal(proposal.method, np.zeros_like(proposal.action),
                        proposal.score, "GATE_REJECT", proposal.event,
                        proposal.certificate)
    return Proposal(proposal.method, proposal.action.copy(), proposal.score,
                    "EXECUTED", proposal.event, proposal.certificate)


def _checked_input(z, public_model):
    z = np.asarray(z, dtype=np.float64)
    sigma = np.asarray(public_model["Sigma_eta"], dtype=np.float64)
    if z.ndim != 1 or sigma.shape != (z.size, z.size) or not np.all(np.isfinite(z)):
        raise ValueError("INPUT_INVALID")
    if not np.all(np.isfinite(sigma)) or not np.allclose(sigma, sigma.T, rtol=1e-12, atol=1e-14):
        raise ValueError("MODEL_INVALID")
    chol = np.linalg.cholesky(sigma)
    cap = float(public_model.get("U", U_DEFAULT))
    if not math.isfinite(cap) or cap <= 0:
        raise ValueError("MODEL_INVALID")
    return z, sigma, chol, cap


def _event_gls(z, chol, event):
    O = np.asarray(event["O"], dtype=np.float64)
    G = np.asarray(event["G"], dtype=np.float64)
    Ow = np.linalg.solve(chol, O)
    zw = np.linalg.solve(chol, z)
    info = Ow.T @ Ow
    eig = np.linalg.eigvalsh((info + info.T) * 0.5)
    if eig[0] <= 0 or eig[0] / eig[-1] < 1e-12 or np.linalg.cond(info) > 1e12:
        raise ArithmeticError("MODEL_INVALID")
    theta_cov = np.linalg.solve(info, np.eye(info.shape[0]))
    Kz = np.linalg.solve(info, Ow.T @ zw)
    residual = zw - Ow @ Kz
    score = float(Kz @ info @ Kz)
    return {"O": O, "G": G, "info": info, "theta": Kz,
            "theta_cov": theta_cov, "residual": float(residual @ residual),
            "explained": score}


def propose_hard(z, frozen_public_model) -> Proposal:
    method = "hard_gls_capped"
    dim = int(np.asarray(frozen_public_model["G"][0]).shape[0])
    try:
        z, _, chol, cap = _checked_input(z, frozen_public_model)
        fits = []
        for event in frozen_public_model["events"]:
            fit = _event_gls(z, chol, event)
            fit["event"] = (int(event["edge"]), int(event["r"]))
            fits.append(fit)
        fit = min(fits, key=lambda f: (-f["explained"], f["event"]))
        action = _radial_cap(fit["G"] @ fit["theta"], cap)
        score = max(0.0, max(f["explained"] for f in fits))
        return Proposal(method, action, score, "VALID", fit["event"],
                        {"selected_explained_energy": fit["explained"],
                         "U": cap, "fit_count": len(fits)})
    except (ValueError, ArithmeticError, np.linalg.LinAlgError, FloatingPointError) as exc:
        return _fail(method, dim, str(exc) if str(exc) in {"INPUT_INVALID", "MODEL_INVALID"}
                     else "MODEL_INVALID")


def propose_soft(z, frozen_public_model) -> Proposal:
    method = "correct_joint_soft_impact_capped"
    dim = int(np.asarray(frozen_public_model["G"][0]).shape[0])
    try:
        z, sigma, _, cap = _checked_input(z, frozen_public_model)
        models = frozen_public_model["events"]
        prior = frozen_public_model["prior"]
        logits, impacts = [], []
        sign0, logdet0 = np.linalg.slogdet(sigma)
        if sign0 <= 0:
            raise ArithmeticError("MODEL_INVALID")
        solved0 = np.linalg.solve(sigma, z)
        logits.append(math.log(float(prior["normal"])) - 0.5 * (
            z.size * math.log(2.0 * math.pi) + logdet0 + float(z @ solved0)))
        impacts.append(np.zeros(dim))
        each_probability = prior["each_event"]
        if np.isscalar(each_probability):
            probabilities = [float(each_probability)] * len(models)
        else:
            probabilities = list(each_probability)
        if len(probabilities) != len(models):
            raise ArithmeticError("MODEL_INVALID")
        for event, probability in zip(models, probabilities):
            Szz = np.asarray(event["Sigma_zz"], dtype=np.float64)
            Sthz = np.asarray(event["Sigma_theta_z"], dtype=np.float64)
            G = np.asarray(event["G"], dtype=np.float64)
            sign, logdet = np.linalg.slogdet(Szz)
            if sign <= 0 or not np.all(np.isfinite(Szz)):
                raise ArithmeticError("MODEL_INVALID")
            solved = np.linalg.solve(Szz, z)
            loglike = -0.5 * (z.size * math.log(2.0 * math.pi) + logdet + float(z @ solved))
            theta_mean = Sthz @ solved
            logits.append(math.log(float(probability)) + loglike)
            impacts.append(G @ theta_mean)
        weights = np.exp(np.asarray(logits) - logsumexp(logits))
        mean = np.einsum("h,hd->d", weights, np.asarray(impacts))
        action = _radial_cap(mean, cap)
        return Proposal(method, action, float(np.linalg.norm(mean)), "VALID", None,
                        {"posterior_weights": weights.tolist(), "U": cap,
                         "normal_model_included": True})
    except (ValueError, ArithmeticError, np.linalg.LinAlgError, FloatingPointError,
            OverflowError):
        return _fail(method, dim, "MODEL_INVALID")


def _psd_sqrt(matrix: np.ndarray) -> np.ndarray:
    matrix = (np.asarray(matrix, dtype=np.float64) + np.asarray(matrix, dtype=np.float64).T) * 0.5
    values, vectors = np.linalg.eigh(matrix)
    scale = max(1.0, float(np.max(np.abs(values))))
    if float(values[0]) < -1e-12 * scale:
        raise ArithmeticError("MODEL_INVALID")
    return vectors @ np.diag(np.sqrt(np.maximum(values, 0.0))) @ vectors.T


def _support(ellipse: Ellipse, direction: np.ndarray) -> np.ndarray:
    v = np.asarray(direction, dtype=np.float64)
    lv = ellipse.shape.T @ v
    norm = float(np.linalg.norm(lv))
    if norm <= 1e-15:
        return ellipse.center.copy()
    return ellipse.center + ellipse.shape @ lv / norm


def _support_value(ellipse: Ellipse, direction: np.ndarray) -> float:
    return float(direction @ ellipse.center + np.linalg.norm(ellipse.shape.T @ direction))


def _unique_add(points: list[np.ndarray], candidate: np.ndarray, tolerance=1e-13) -> bool:
    if not np.all(np.isfinite(candidate)):
        raise ArithmeticError("SOLVER_REJECT")
    if any(np.linalg.norm(candidate - p) <= tolerance * max(1.0, np.linalg.norm(candidate))
           for p in points):
        return False
    points.append(np.asarray(candidate, dtype=np.float64).copy())
    return True


def _feasible_weights(result, old, count):
    values = old if result.x is None or not np.all(np.isfinite(result.x)) else np.asarray(result.x)
    values = np.maximum(values, 0.0)
    total = float(values.sum())
    if total <= 0 or not math.isfinite(total):
        raise ArithmeticError("SOLVER_REJECT")
    values /= total
    if values.shape != (count,):
        raise ArithmeticError("SOLVER_REJECT")
    return values


def _distance_hull(ellipses, tol=1e-7, max_iter=2048):
    points: list[np.ndarray] = []
    eye = np.eye(2)
    for e in ellipses:
        _unique_add(points, e.center)
        for axis in eye:
            for sign in (-1.0, 1.0):
                _unique_add(points, _support(e, sign * axis))
    weights = np.full(len(points), 1.0 / len(points))
    for iteration in range(1, max_iter + 1):
        P_raw = np.asarray(points)
        scale = max(float(np.max(np.linalg.norm(P_raw, axis=1))), 1e-12)
        P = P_raw / scale
        objective = lambda w: float(np.dot(w @ P, w @ P))
        jacobian = lambda w: 2.0 * P @ (w @ P)
        result = minimize(objective, weights, jac=jacobian, method="SLSQP",
                          bounds=[(0.0, 1.0)] * len(points),
                          constraints=[{"type": "eq", "fun": lambda w: float(w.sum()-1.0),
                                        "jac": lambda w: np.ones_like(w)}],
                          options={"maxiter": 512, "ftol": 1e-12, "disp": False})
        weights = _feasible_weights(result, weights, len(points))
        p = scale * (weights @ P)
        upper = float(np.linalg.norm(p))
        if upper <= 1e-15:
            return 0.0, 0.0, p, iteration
        direction = -p / upper
        support_value = max(_support_value(e, direction) for e in ellipses)
        roundoff = 128.0 * EPS * max(1.0, abs(support_value), upper)
        lower = max(0.0, -support_value - roundoff)
        if upper - lower <= tol:
            return lower, upper, p, iteration
        chosen = max(ellipses, key=lambda e: (_support_value(e, direction), e.event))
        added = _unique_add(points, _support(chosen, direction))
        if not added:
            if result.success and upper - lower <= 10 * tol:
                return lower, upper, p, iteration
            raise ArithmeticError("SOLVER_REJECT")
        weights = np.append(weights, 0.0)
    raise ArithmeticError("SOLVER_REJECT")


def _trust_max(a: np.ndarray, L: np.ndarray, event) -> tuple[float, float, np.ndarray]:
    """Feasible lower point and Lagrange-dual upper for max ||a+L v||^2, ||v||<=1."""
    Q = (L.T @ L + (L.T @ L).T) * 0.5
    b = L.T @ a
    vals, V = np.linalg.eigh(Q)
    vals = np.maximum(vals, 0.0)
    be = V.T @ b
    qmax = float(vals[-1])
    scale = max(1.0, qmax, float(np.linalg.norm(be)), float(a @ a))
    tol = 128.0 * EPS * scale
    top = vals >= qmax - 64.0 * EPS * max(1.0, qmax)
    lower_mask = ~top
    top_norm = float(np.linalg.norm(be[top]))
    c0 = float(a @ a)

    def secular(lam):
        return float(np.sum((be / (lam - vals)) ** 2))

    hard = top_norm <= tol
    if hard:
        v_e = np.zeros(2)
        if np.any(lower_mask):
            gaps = qmax - vals[lower_mask]
            if np.any(gaps <= 0):
                raise ArithmeticError("SOLVER_REJECT")
            v_e[lower_mask] = be[lower_mask] / gaps
        norm2 = float(v_e @ v_e)
        if norm2 > 1.0 + 1e-10:
            hard = False
        else:
            top_id = int(np.flatnonzero(top)[0])
            amplitude = math.sqrt(max(0.0, 1.0 - norm2))
            candidates = []
            for sign in (-1.0, 1.0):
                trial = v_e.copy()
                trial[top_id] = sign * amplitude
                v = V @ trial
                val = float(np.linalg.norm(a + L @ v) ** 2)
                candidates.append((val, v))
            lower, v = max(candidates, key=lambda item: item[0])
            dual = c0 + qmax
            if np.any(lower_mask):
                dual += float(np.sum(be[lower_mask] ** 2 / (qmax - vals[lower_mask])))
            roundoff = 128.0 * EPS * max(1.0, abs(lower), abs(dual), scale)
            return max(0.0, lower - roundoff), dual + roundoff, v

    delta = max(64.0 * EPS * max(1.0, qmax), np.nextafter(qmax, math.inf) - qmax)
    lo = qmax + delta
    if not math.isfinite(lo):
        raise ArithmeticError("SOLVER_REJECT")
    flo = secular(lo) - 1.0
    if flo <= 0.0:
        # A near-hard case: use a valid dual point just above the spectrum.
        lam = lo
    else:
        hi = max(qmax + 1.0, lo * 2.0 + 1.0)
        for _ in range(128):
            if secular(hi) <= 1.0:
                break
            hi = qmax + 2.0 * (hi - qmax)
        else:
            raise ArithmeticError("SOLVER_REJECT")
        for _ in range(128):
            mid = 0.5 * (lo + hi)
            if secular(mid) > 1.0:
                lo = mid
            else:
                hi = mid
        lam = hi
    denom = lam - vals
    if np.any(denom <= 0):
        raise ArithmeticError("SOLVER_REJECT")
    v_e = be / denom
    norm = float(np.linalg.norm(v_e))
    if norm > 1.0 + 1e-8:
        raise ArithmeticError("SOLVER_REJECT")
    if norm > 0:
        v_e = v_e / max(1.0, norm)
    v = V @ v_e
    lower = float(np.linalg.norm(a + L @ v) ** 2)
    dual = c0 + lam + float(np.sum(be * be / denom))
    roundoff = 128.0 * EPS * max(1.0, abs(lower), abs(dual), scale)
    return max(0.0, lower - roundoff), dual + roundoff, v


def _center_dual(points: np.ndarray, weights: np.ndarray, cap: float):
    mean = weights @ points
    second = float(weights @ np.sum(points * points, axis=1))
    norm = float(np.linalg.norm(mean))
    lower = second - norm * norm + max(norm - cap, 0.0) ** 2
    return lower, mean


def _chebyshev(ellipses, cap, gap_tol=1e-10, max_iter=256):
    points: list[np.ndarray] = []
    eye = np.eye(2)
    for e in ellipses:
        _unique_add(points, e.center)
        for axis in eye:
            for sign in (-1.0, 1.0):
                _unique_add(points, _support(e, sign * axis))
    weights = np.full(len(points), 1.0 / len(points))
    for iteration in range(1, max_iter + 1):
        P_raw = np.asarray(points)
        scale = max(float(np.max(np.linalg.norm(P_raw, axis=1))), 1e-12)
        P = P_raw / scale
        cap_scaled = cap / scale

        def neg_dual(w):
            lower, _ = _center_dual(P, w, cap_scaled)
            return -lower

        def neg_jac(w):
            lower, mean = _center_dual(P, w, cap_scaled)
            projected = _radial_cap(mean, cap_scaled)
            return -(np.sum(P * P, axis=1) - 2.0 * (P @ projected))

        result = minimize(neg_dual, weights, jac=neg_jac, method="SLSQP",
                          bounds=[(0.0, 1.0)] * len(points),
                          constraints=[{"type": "eq", "fun": lambda w: float(w.sum()-1.0),
                                        "jac": lambda w: np.ones_like(w)}],
                          options={"maxiter": 512, "ftol": 1e-12, "disp": False})
        weights = _feasible_weights(result, weights, len(points))
        dual_scaled, mean_scaled = _center_dual(P, weights, cap_scaled)
        dual_lower = scale * scale * dual_scaled
        mean = scale * mean_scaled
        center = _radial_cap(mean, cap)
        hi = 0.0
        new_points = []
        for e in ellipses:
            lower, upper, v = _trust_max(e.center - center, e.shape, e.event)
            hi = max(hi, upper)
            new_points.append(e.center + e.shape @ v)
        roundoff = 128.0 * EPS * max(1.0, abs(hi), abs(dual_lower))
        dual_lower -= roundoff
        gap = hi - dual_lower
        if gap < -roundoff:
            raise ArithmeticError("SOLVER_REJECT")
        if gap <= gap_tol:
            return center, {"lower_squared": dual_lower, "upper_squared": hi,
                            "gap_squared": max(0.0, gap),
                            "action_error_bound": math.sqrt(max(0.0, gap)),
                            "iterations": iteration}
        added = False
        for point in new_points:
            added |= _unique_add(points, point)
        if not added:
            raise ArithmeticError("SOLVER_REJECT")
        weights = np.append(weights, np.zeros(len(points) - len(weights)))
    raise ArithmeticError("SOLVER_REJECT")


def _build_set_ellipses(z, chol, public_model):
    threshold_q = float(public_model["t_Q"])
    threshold_r = float(public_model["t_r"])
    accepted, rejected, boundary = [], [], []
    roundoff = 128.0 * EPS
    for event in public_model["events"]:
        fit = _event_gls(z, chol, event)
        event_key = (int(event["edge"]), int(event["r"]))
        residual_guard = roundoff * max(1.0, abs(fit["residual"]))
        if fit["residual"] - residual_guard <= threshold_r:
            if abs(fit["residual"] - threshold_r) <= 10.0 * residual_guard:
                boundary.append(event_key)
            cov = threshold_q * fit["G"] @ fit["theta_cov"] @ fit["G"].T
            shape = _psd_sqrt(cov)
            accepted.append(Ellipse(fit["G"] @ fit["theta"], shape, event_key))
        else:
            rejected.append(event_key)
    return accepted, rejected, boundary


def propose_set(z, frozen_public_model) -> Proposal:
    method = "set_constrained_chebyshev"
    dim = int(np.asarray(frozen_public_model["G"][0]).shape[0])
    try:
        z, _, chol, cap = _checked_input(z, frozen_public_model)
        ellipses, rejected, boundary = _build_set_ellipses(z, chol, frozen_public_model)
        if not ellipses:
            raise ArithmeticError("EMPTY_UNION")
        score_lo, score_hi, _, score_iterations = _distance_hull(ellipses)
        if score_hi - score_lo > 1e-7:
            raise ArithmeticError("SOLVER_REJECT")
        if score_lo <= 1e-10:
            return Proposal(method, np.zeros(dim), 0.0, "VALID", None,
                            {"score_lower": score_lo, "score_upper": score_hi,
                             "coverage_candidates": len(ellipses),
                             "rejected_events": rejected, "boundary_retained": boundary,
                             "score_iterations": score_iterations, "zero_or_unresolved": True})
        action, cert = _chebyshev(ellipses, cap)
        action = _radial_cap(action, cap)
        if float(np.linalg.norm(action)) > cap:
            raise ArithmeticError("SOLVER_REJECT")
        cert.update({"score_lower": score_lo, "score_upper": score_hi,
                     "coverage_candidates": len(ellipses), "rejected_events": rejected,
                     "boundary_retained": boundary, "score_iterations": score_iterations,
                     "U": cap})
        return Proposal(method, action, score_lo, "VALID", None, cert)
    except ValueError as exc:
        status = str(exc) if str(exc) in {"INPUT_INVALID", "MODEL_INVALID"} else "MODEL_INVALID"
        return _fail(method, dim, status)
    except ArithmeticError as exc:
        status = str(exc) if str(exc) in {"EMPTY_UNION", "SOLVER_REJECT", "MODEL_INVALID"} else "SOLVER_REJECT"
        return _fail(method, dim, status, {"error": str(exc)})
    except (np.linalg.LinAlgError, FloatingPointError, OverflowError):
        return _fail(method, dim, "MODEL_INVALID")


def propose(z, frozen_public_model, method: str) -> Proposal:
    """Single whitelist interface used by the future evaluator/calibrator."""
    if method == "hard_gls_capped":
        return propose_hard(z, frozen_public_model)
    if method == "correct_joint_soft_impact_capped":
        return propose_soft(z, frozen_public_model)
    if method == "set_constrained_chebyshev":
        return propose_set(z, frozen_public_model)
    raise ValueError(f"unknown frozen method {method!r}")


def public_model_from_npz(npz_path, protocol):
    """Construct immutable shared matrices; no samples, labels, or truth."""
    events = []
    with np.load(npz_path, allow_pickle=False) as data:
        for edge, r in protocol["events_edge_r"]:
            ix = np.flatnonzero(np.all(data["case_edge_r_age"] == [edge, r, 64], axis=1))
            if len(ix) != 1:
                raise ValueError("MODEL_INVALID")
            i = int(ix[0])
            events.append({"edge": int(edge), "r": int(r),
                           "O": data["O"][i].copy(), "G": data["G"][i].copy(),
                           "Sigma_theta_z": data["Sigma_theta_z"][i].copy(),
                           "Sigma_zz": data["Sigma_zz"][i].copy()})
        sigma = data["Sigma_eta"].copy()
    return {"Sigma_eta": sigma, "events": events,
            "G": [e["G"] for e in events],
            "prior": {"normal": float(protocol["nominal_prior"]["normal"]),
                      "each_event": float(protocol["nominal_prior"]["each_event"])},
            "t_Q": float(protocol["t_Q"] if "t_Q" in protocol else 11.536641991587517),
            "t_r": float(protocol["t_r"] if "t_r" in protocol else 26.498086492638055),
            "U": float(protocol["U_common"])}
