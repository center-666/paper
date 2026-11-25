"""Certified safety-disk intersection corrector for signed endpoint sets."""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction as F
import numpy as np
from scipy.optimize import minimize


def matvec(matrix, vector):
    return np.asarray(matrix, dtype=float) @ np.asarray(vector, dtype=float)


def whiten(weight):
    values, vectors = np.linalg.eigh(np.asarray(weight, dtype=float))
    if np.any(values <= 0):
        raise ValueError("W must be positive definite")
    root = vectors @ np.diag(np.sqrt(values)) @ vectors.T
    inverse_root = vectors @ np.diag(1.0 / np.sqrt(values)) @ vectors.T
    return root, inverse_root


def vertices(intervals, responses):
    result = []
    for onset, (lo, hi) in sorted(intervals.items()):
        if onset not in responses:
            continue
        response = np.asarray(responses[onset], dtype=float)
        result.extend((onset, endpoint, endpoint * response) for endpoint in (lo, hi))
    return result


def minimum_norm_convex_combination(points, tolerance=1e-12):
    """Enumerate simplex supports for the small state dimensions used here."""
    points = np.asarray(points, dtype=float)
    if len(points) == 0:
        return np.zeros(points.shape[1] if points.ndim == 2 else 0), np.zeros(0)
    best = None
    dimension = points.shape[1]
    for support_size in range(1, min(dimension + 1, len(points)) + 1):
        import itertools
        for support in itertools.combinations(range(len(points)), support_size):
            selected = points[list(support)]
            gram = selected @ selected.T
            kkt = np.block([[gram, np.ones((support_size, 1))],
                            [np.ones((1, support_size)), np.zeros((1, 1))]])
            rhs = np.r_[np.zeros(support_size), 1.0]
            try:
                solution = np.linalg.solve(kkt, rhs)[:support_size]
            except np.linalg.LinAlgError:
                continue
            if np.min(solution) < -tolerance:
                continue
            point = solution @ selected
            norm = float(point @ point)
            if best is None or norm < best[0]:
                weights = np.zeros(len(points)); weights[list(support)] = solution
                best = norm, point, weights
    if best is None:
        index = int(np.argmin(np.sum(points * points, axis=1)))
        weights = np.zeros(len(points)); weights[index] = 1.0
        return points[index], weights
    return best[1], best[2]


def safety_margin(action, points):
    action = np.asarray(action, dtype=float)
    points = np.asarray(points, dtype=float)
    return float(np.min(2.0 * (points @ action) - action @ action))


def safety_value(point, candidate, margin):
    return float(2.0 * point @ candidate - candidate @ candidate - margin)


def pull_back(anchor, candidate, points, margin):
    """Find the largest segment step from a safe anchor to a candidate."""
    anchor = np.asarray(anchor, dtype=float)
    candidate = np.asarray(candidate, dtype=float)
    direction = candidate - anchor
    alpha = 1.0
    for point in np.asarray(points, dtype=float):
        if safety_value(point, candidate, margin) >= -1e-12:
            continue
        left, right = 0.0, alpha
        for _ in range(80):
            middle = 0.5 * (left + right)
            trial = anchor + middle * direction
            if safety_value(point, trial, margin) >= 0:
                left = middle
            else:
                right = middle
        alpha = min(alpha, left)
    return anchor + alpha * direction


@dataclass
class CorrectorResult:
    action: np.ndarray
    margin: float
    anchor_margin: float
    zero_reason: str | None
    endpoint_count: int


def safe_disk_corrector(intervals, responses, weight, estimate, margin=0.0, cap=None):
    root, inverse_root = whiten(weight)
    raw = vertices(intervals, responses)
    if not raw:
        return CorrectorResult(np.zeros(len(estimate)), 0.0, 0.0, "EMPTY_SET", 0)
    if any(lo <= 0 <= hi for lo, hi in intervals.values()):
        return CorrectorResult(np.zeros(len(estimate)), 0.0, 0.0, "ZERO_IN_INTERVAL", len(raw))
    points = np.asarray([point for _, _, point in raw], dtype=float)
    white_points = points @ root.T
    anchor, _ = minimum_norm_convex_combination(white_points)
    anchor_margin = safety_margin(anchor, white_points)
    if anchor @ anchor <= margin:
        return CorrectorResult(np.zeros(len(estimate)), anchor_margin, anchor_margin, "ORIGIN_NOT_SEPARATED", len(raw))
    estimate_white = root @ np.asarray(estimate, dtype=float)
    constraints = [{"type": "ineq", "fun":
                    lambda action, point=point: safety_value(point, action, margin)}
                   for point in white_points]
    optimization = minimize(lambda action: float(np.sum((action - estimate_white) ** 2)),
                            anchor, method="SLSQP", constraints=constraints,
                            options={"ftol": 1e-12, "maxiter": 300})
    candidate = optimization.x if optimization.success else anchor.copy()
    candidate = pull_back(anchor, candidate, white_points, margin)
    actual_margin = safety_margin(candidate, white_points)
    if actual_margin < margin - 1e-9:
        candidate = anchor
        actual_margin = safety_margin(candidate, white_points)
    action = inverse_root @ candidate
    if cap is not None and np.sum(np.abs(action)) > cap:
        action *= cap / np.sum(np.abs(action))
        actual_margin = safety_margin(root @ action, white_points)
        if actual_margin < margin - 1e-9:
            action = np.zeros(len(estimate)); actual_margin = 0.0
    return CorrectorResult(action, actual_margin, anchor_margin, None, len(raw))
