"""Exact fixed-amplitude pollution envelopes after certified directional evidence.

This module is deliberately model-scoped to the Stage 6 two-state, one-sensor
linear Gaussian system. All dynamics and parameter interval endpoints use
fractions, so onset exclusions and support calculations have no rounding loss.
"""
from __future__ import annotations

from fractions import Fraction as F
from pathlib import Path
import sys

STAGE6 = Path(__file__).resolve().parents[1] / "paper2_stage6_vector_correction_20261122"
STAGE4 = Path(__file__).resolve().parents[1] / "paper2_stage4_certified_correction_20261122"
if str(STAGE6) not in sys.path:
    sys.path.insert(0, str(STAGE6))
if str(STAGE4) not in sys.path:
    sys.path.insert(0, str(STAGE4))

from exact_linear import matrix, identity, add, matmul, transpose, update
from projection import inner, interval_image, weighted_projection
from interval_arithmetic import Interval as I


def interval_fraction(x):
    x = F(x)
    return I.exact(x.numerator) / I.exact(x.denominator)


def interval_dot(a, b):
    return sum((x * y for x, y in zip(a, b)), I.exact(0))


def interval_lower_fraction(x):
    return F(str(x.lo))


def vecmat(a, x):
    return tuple(sum((a[i][j] * x[j] for j in range(len(x))), F(0)) for i in range(len(a)))


def vadd(a, b):
    return tuple(x + y for x, y in zip(a, b))


class FixedAmplitudeEnvelope:
    """Track exact unit responses and onset-specific constant-amplitude ranges."""

    def __init__(self, model, track_responses=True):
        self.model = model
        self.A = matrix(model["A"])
        self.C = matrix(model["C"])
        self.Q = matrix(model["Q"])
        self.P = matrix(model["P0_prior"])
        self.R = F(model["R"])
        self.Z = F(model["Z"])
        self.W = matrix(model["W"])
        self.bmax = F(model["attack_amplitude_cap"])
        self.responses: list[tuple[F, ...] | None] = []
        self.track_responses = track_responses
        self.bounds: dict[int, tuple[F, F]] = {}
        self.constraints: list[dict] = []
        self.time = -1

    def advance(self, sent: bool):
        """Advance covariance and every onset response through one trusted event."""
        noise = F(0) if sent else 1 / self.Z
        post, K, T = update(self.P, self.C, self.R + noise)
        Fmat = matmul(T, self.A)
        kval = tuple(row[0] for row in K)
        if self.track_responses:
            if self.constraints:
                new = [None if h is None or k not in self.bounds else
                       vadd(vecmat(Fmat, h), kval if sent else tuple(F(0) for _ in kval))
                       for k, h in enumerate(self.responses)]
                new.append(None)
            else:
                new = [None if h is None else vecmat(Fmat, h) for h in self.responses]
                if sent:
                    new = [None if h is None else vadd(h, kval) for h in new]
                    new.append(kval)
                else:
                    new.append(tuple(F(0) for _ in kval))
            self.responses = new
        self.P = add(matmul(matmul(self.A, post), transpose(self.A)), self.Q)
        self.time += 1
        return Fmat, K

    def add_certificate(self, direction, z):
        """Intersect each onset's b interval with one exact half-space certificate.

        A successful certificate is d^T W theta >= z > 0. Since theta=b H_k
        and H is exact here, q_k=d^T W H_k gives either an exact onset exclusion
        (q_k<=0) or the exact lower endpoint b>=z/q_k.
        """
        d = tuple(F(x) for x in direction)
        z = F(z)
        if z <= 0:
            raise ValueError("A propagatable certificate must have z > 0")
        if len(d) != len(self.W) or inner(d, d, self.W) <= 0:
            raise ValueError("Invalid certificate direction")
        kept = {}
        removed = []
        raised = 0
        first_constraint = not self.constraints
        for k, H in enumerate(self.responses):
            if H is None:
                continue
            if not first_constraint and k not in self.bounds:
                continue
            q = inner(d, H, self.W)
            if q <= 0:
                removed.append(k)
                continue
            lower = z / q
            if k in self.bounds:
                lower = max(lower, self.bounds[k][0])
            if lower > self.bmax:
                removed.append(k)
                continue
            if k not in self.bounds or lower > self.bounds[k][0]:
                raised += 1
            kept[k] = (lower, self.bmax)
        self.bounds = kept
        self.responses = [H if k in kept else None for k, H in enumerate(self.responses)]
        self.constraints.append({"time": self.time, "direction": d, "z": z})
        return {"time": self.time, "input_onsets": len(self.responses),
                "retained_onsets": len(kept), "removed_onsets": removed,
                "raised_lower_bounds": raised,
                "minimum_b_lower": min((lo for lo, _ in kept.values()), default=None)}

    def support(self, direction):
        """Exact minimum of d^T W theta over the current union of line segments."""
        d = tuple(F(x) for x in direction)
        values = []
        for k, (lo, hi) in self.bounds.items():
            q = inner(d, self.responses[k], self.W)
            values.append(q * (lo if q >= 0 else hi))
        return min(values) if values else None

    def directional_action(self, direction, l1_cap=None):
        """Minimax-safe correction along d, using the exact outer-set support."""
        d = tuple(F(x) for x in direction)
        support = self.support(d)
        denom = inner(d, d, self.W)
        if support is None or support <= 0:
            return {"action": tuple(F(0) for _ in d), "support": support,
                    "guaranteed_gain": F(0), "uncapped_gain": F(0)}
        action = tuple(support / denom * x for x in d)
        uncapped_gain = support * support / denom
        if l1_cap is not None:
            cap = F(l1_cap)
            l1 = sum((abs(x) for x in action), F(0))
            if l1 > cap:
                scale = cap / l1
                action = tuple(scale * x for x in action)
        # Scaling the projection action inward preserves improvement >= ||c||_W^2.
        gain = inner(action, action, self.W)
        return {"action": action, "support": support,
                "guaranteed_gain": gain, "uncapped_gain": uncapped_gain}

    def projected_action(self, l1_cap=None):
        """Exact two-dimensional convex-hull projection of the retained segments."""
        coefficients = [self.responses[k] for k in sorted(self.bounds)]
        amplitudes = [self.bounds[k] for k in sorted(self.bounds)]
        points = interval_image(coefficients, amplitudes, include_unstarted=False)
        result = weighted_projection(points, self.W)
        action = result["point"]
        if l1_cap is not None:
            cap = F(l1_cap)
            l1 = sum((abs(x) for x in action), F(0))
            if l1 > cap:
                action = tuple(cap / l1 * x for x in action)
        result["uncapped_point"] = result["point"]
        result["point"] = action
        result["capped_gain_lower_bound"] = inner(action, action, self.W)
        return result

    def contains_truth(self, onset, amplitude):
        amplitude = F(amplitude)
        return onset in self.bounds and self.bounds[onset][0] <= amplitude <= self.bounds[onset][1]

    def vertices(self):
        coefficients = [self.responses[k] for k in sorted(self.bounds)]
        amplitudes = [self.bounds[k] for k in sorted(self.bounds)]
        return interval_image(coefficients, amplitudes, include_unstarted=False)


class IntervalFixedAmplitudeEnvelope:
    """Outward-rounded response boxes with exact covariance recursion.

    This is the computational replay implementation. The Fraction class above
    remains the exact theorem/checking implementation. Every q interval encloses
    the exact response coefficient, and b lower endpoints are rounded down.
    """

    def __init__(self, model, track_responses=True):
        self.model = model
        self.A = matrix(model["A"])
        self.C = matrix(model["C"])
        self.Q = matrix(model["Q"])
        self.P = matrix(model["P0_prior"])
        self.R = F(model["R"])
        self.Z = F(model["Z"])
        self.W = matrix(model["W"])
        self.bmax = F(model["attack_amplitude_cap"])
        self.responses = []
        self.bounds = {}
        self.constraints = []
        self.track_responses = track_responses
        self.time = -1

    def advance(self, sent):
        noise = F(0) if sent else 1 / self.Z
        post, K, T = update(self.P, self.C, self.R + noise)
        Fmat = matmul(T, self.A)
        Kint = [interval_fraction(row[0]) for row in K]
        Fint = [[interval_fraction(x) for x in row] for row in Fmat]
        if self.track_responses:
            if self.constraints:
                new = []
                for k, H in enumerate(self.responses):
                    if H is None or k not in self.bounds:
                        new.append(None)
                    else:
                        value = [interval_dot(row, H) for row in Fint]
                        if sent:
                            value = [x + Kint[j] for j, x in enumerate(value)]
                        new.append(value)
                new.append(None)
            else:
                new = []
                for H in self.responses:
                    if H is None:
                        new.append(None)
                    else:
                        value = [interval_dot(row, H) for row in Fint]
                        if sent:
                            value = [x + Kint[j] for j, x in enumerate(value)]
                        new.append(value)
                new.append(Kint if sent else [I.exact(0) for _ in Kint])
            self.responses = new
        self.P = add(matmul(matmul(self.A, post), transpose(self.A)), self.Q)
        self.time += 1
        return Fmat, K

    def _q_interval(self, direction, H):
        d = tuple(F(x) for x in direction)
        wd = [sum((self.W[i][j] * d[i] for i in range(len(d))), F(0))
              for j in range(len(d))]
        return interval_dot([interval_fraction(x) for x in wd], H)

    def add_certificate(self, direction, z):
        d = tuple(F(x) for x in direction)
        z = F(z)
        if z <= 0:
            raise ValueError("A propagatable certificate must have z > 0")
        if inner(d, d, self.W) <= 0:
            raise ValueError("Invalid certificate direction")
        first = not self.constraints
        kept = {}
        removed = []
        raised = 0
        for k, H in enumerate(self.responses):
            if H is None or (not first and k not in self.bounds):
                continue
            q = self._q_interval(d, H)
            if not q.hi.is_finite() or q.hi <= 0:
                removed.append(k)
                continue
            ratio = interval_fraction(z) / I.exact(q.hi)
            lower = interval_lower_fraction(ratio)
            if k in self.bounds:
                lower = max(lower, self.bounds[k][0])
            if lower > self.bmax:
                removed.append(k)
                continue
            if k not in self.bounds or lower > self.bounds[k][0]:
                raised += 1
            kept[k] = (lower, self.bmax)
        self.bounds = kept
        self.responses = [H if k in kept else None for k, H in enumerate(self.responses)]
        self.constraints.append({"time": self.time, "direction": d, "z": z})
        return {"time": self.time, "input_onsets": len(self.responses),
                "retained_onsets": len(kept), "removed_onsets": removed,
                "raised_lower_bounds": raised,
                "minimum_b_lower": min((lo for lo, _ in kept.values()), default=None)}

    def support(self, direction):
        supports = []
        for k, (lo, hi) in self.bounds.items():
            q = self._q_interval(direction, self.responses[k])
            if q.lo >= 0:
                supports.append(interval_lower_fraction(q * I.exact(lo.numerator) / I.exact(lo.denominator)))
            else:
                supports.append(interval_lower_fraction(q * I.exact(hi.numerator) / I.exact(hi.denominator)))
        return min(supports) if supports else None

    def directional_action(self, direction, l1_cap=None):
        d = tuple(F(x) for x in direction)
        support = self.support(d)
        denom = inner(d, d, self.W)
        if support is None or support <= 0:
            return {"action": tuple(F(0) for _ in d), "support": support,
                    "guaranteed_gain": F(0), "uncapped_gain": F(0)}
        action = tuple(support / denom * x for x in d)
        uncapped = support * support / denom
        if l1_cap is not None:
            cap = F(l1_cap)
            l1 = sum((abs(x) for x in action), F(0))
            if l1 > cap:
                action = tuple(cap / l1 * x for x in action)
        return {"action": action, "support": support,
                "guaranteed_gain": inner(action, action, self.W),
                "uncapped_gain": uncapped}

    def box_vertices(self):
        """Rational corners of a coordinate-box outer approximation."""
        corners = []
        for k, (lo, hi) in self.bounds.items():
            H = self.responses[k]
            coord = []
            for value in H:
                bvalues = [F(str(value.lo)) * lo, F(str(value.lo)) * hi,
                           F(str(value.hi)) * lo, F(str(value.hi)) * hi]
                coord.append((min(bvalues), max(bvalues)))
            corners.extend((x, y) for x in coord[0] for y in coord[1])
        return corners

    def projected_action(self, l1_cap=None):
        result = weighted_projection(self.box_vertices(), self.W)
        action = result["point"]
        if l1_cap is not None:
            cap = F(l1_cap)
            l1 = sum((abs(x) for x in action), F(0))
            if l1 > cap:
                action = tuple(cap / l1 * x for x in action)
        result["uncapped_point"] = result["point"]
        result["point"] = action
        result["capped_gain_lower_bound"] = inner(action, action, self.W)
        return result

    def contains_truth_amplitude(self, onset, amplitude):
        amplitude = F(amplitude)
        return onset in self.bounds and self.bounds[onset][0] <= amplitude <= self.bounds[onset][1]


def transport_halfspace(certificate, Fmat, K, sent, bmax):
    """Stage 6 legacy half-space propagation, exact rational arithmetic."""
    if certificate is None:
        return None
    from exact_linear import inverse
    d, z = certificate
    moved = tuple(row[0] for row in matmul(transpose(inverse(Fmat)), [[x] for x in d]))
    injection = sum((moved[i] * K[i][0] for i in range(len(moved))), F(0)) * bmax if sent else F(0)
    support = z + min(F(0), injection)
    if support <= 0:
        return None
    scale = max(abs(x) for x in moved)
    if not scale:
        return None
    return tuple(x / scale for x in moved), support / scale


def capped_halfspace_action(certificate, W, l1_cap):
    if certificate is None:
        return tuple(F(0) for _ in W), F(0)
    d, z = certificate
    denom = inner(d, d, W)
    action = tuple(z / denom * x for x in d)
    l1 = sum((abs(x) for x in action), F(0))
    if l1 > F(l1_cap):
        action = tuple(F(l1_cap) / l1 * x for x in action)
    return action, inner(action, action, W)
