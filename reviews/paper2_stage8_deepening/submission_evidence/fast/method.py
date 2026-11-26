"""Binary64 engineering replay of the signed, single-output two-tank M2/M3."""
import json
import math
import os
from pathlib import Path
from time import perf_counter

for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ[key] = "1"

import numpy as np
from scipy.optimize import brentq

ROOT = Path(__file__).resolve().parents[2]
PLANT = json.loads((ROOT / "config/plants.json").read_text())["plants"]["industrial_two_tank"]
A, B, Q, P0 = (np.asarray(PLANT[k], float) for k in ("A", "B", "Q", "P0"))
Z, R = float(PLANT["Z"]), float(PLANT["R"][0][0])
CAP = .35
EPS = .001
LEVELS = (.025, .05, .10)
QUERIES = (127, 255, 383, 511)
GRID = np.asarray([-.35, -.28, -.21, -.14, -.07, .07, .14, .21, .28, .35])
REF = np.asarray([-.07, -.14, -.35, .07, .14, .35])
# Engineering guard in log-likelihood units; no directed-rounding guarantee.
GUARD = 1e-9
USEFUL = .000625


def log_trigger(x):
    with np.errstate(divide="ignore"):
        return np.log(-np.expm1(-Z*x*x/2))


def ideal(d, support):
    return d*min(support/(d@d), 1/np.abs(d).sum())


class Fast:
    def __init__(self):
        self.P = P0.copy()
        self.prior = np.zeros(2)
        self.H = np.empty((0, 2))
        self.linear = np.empty(0)
        self.curvature = np.empty(0)
        self.marks = np.empty(0)
        self.log_den = np.empty(0)
        self.log_mass = np.full(REF.size, -np.inf)
        self.intervals = None
        self.directions = []
        self.old = None
        self.radius = np.zeros(2)

    def step(self, frame):
        t, sent, center, payload = frame
        S = self.P[0, 0]+R
        V = S+1/Z
        K = self.P[:, 0]/(S if sent else V)
        T = np.eye(2)
        T[:, 0] -= K
        F = T@A
        self.P = A@(T@self.P)@A.T+Q
        self.P = (self.P+self.P.T)/2
        r = center-self.prior[0]
        u = payload-self.prior[0] if sent else r
        self.monitor = self.prior+K*u
        self.prior = A@self.monitor + B@([.15, .05] if t % 120 < 60 else [.08, .05])
        if sent:
            self.H = np.vstack((self.H, [0., 0.]))
            self.linear = np.append(self.linear, 0.)
            self.curvature = np.append(self.curvature, 0.)
            self.marks = np.append(self.marks, payload-center)
            self.log_den = np.append(self.log_den, log_trigger(payload-center))
        prior_response = self.H@A.T
        eta = prior_response[:, 0]
        shift = -REF*(eta[0] if eta.size else 0)
        if sent:
            shift += REF
            logfactor = (u*shift-shift*shift/2)/S + log_trigger(payload-center-REF)-self.log_den[-1]
            self.linear += (1-eta)*u/S
            self.curvature += (1-eta)**2/S
        else:
            logfactor = (r*shift-shift*shift/2)/V
            self.linear -= r*eta/V
            self.curvature += eta**2/V
        self.log_mass = np.logaddexp(self.log_mass, -math.log((t+1)*(t+2))) + logfactor
        self.H = prior_response@T.T
        if sent:
            self.H += K
        self.radius = np.ceil((np.abs(F)@self.radius + (CAP*np.abs(K) if sent else 0))*2**48)/2**48

        if self.directions or self.old is not None:
            inv_t = np.linalg.inv(F).T
            self.directions = [self.move(d, inv_t)[0] for d in self.directions]
            if self.old is not None:
                old_d, old_s = self.old
                d, scale = self.move(old_d, inv_t)
                support = old_s/scale - (CAP*abs(d@K) if sent else 0.)
                self.old = (d, support) if support > 0 else None

        query = None
        if t in QUERIES:
            clock = perf_counter()
            d, score = self.propose()
            ref = np.logaddexp(-math.log(t+2), np.logaddexp.reduce(self.log_mass)-math.log(REF.size))
            cutoff = math.log(EPS)+ref
            decisions = []
            if d is not None:
                for level in LEVELS:
                    target = level*np.abs(d).sum()
                    passed = self.certify(d, target, cutoff, score)
                    decisions.append(bool(passed))
                    if not passed:
                        break
                    self.accept(d, target)
            query = (d, decisions, perf_counter()-clock)

        zero = np.zeros(2), 0.
        legacy = self.publish(*self.old) if self.old is not None else zero
        best = legacy if self.intervals else zero
        if self.intervals:
            keys = np.fromiter(self.intervals, dtype=int)
            boxes = np.array(list(self.intervals.values()))
            for d in self.directions:
                q = self.H[keys]@d
                s = np.min(np.minimum(boxes[:, 0]*q, boxes[:, 1]*q))
                if s > 0:
                    candidate = self.publish(d, s)
                    if candidate[1] > best[1]:
                        best = candidate
        return (legacy, best), query, K, F

    @staticmethod
    def move(d, inv_t):
        moved = inv_t@d
        scale = np.abs(moved).max()
        return moved/scale, scale

    def publish(self, d, support):
        a = ideal(d, support)
        actual = self.monitor-(self.monitor-a)
        gain = 2*(a@a - self.radius@np.abs(actual-a)) - actual@actual
        if gain <= 0 or np.abs(actual).sum() > 1:
            return np.zeros(2), 0.
        return actual, gain

    def propose(self):
        if not self.marks.size:
            return None, 0.
        b = GRID[:, None]
        increments = log_trigger(self.marks-b)-self.log_den
        suffix = np.cumsum(increments[:, ::-1], axis=1)[:, ::-1]
        scores = self.linear*b-self.curvature*b*b/2+suffix
        j, k = np.unravel_index(np.argmax(scores), scores.shape)
        point = GRID[j]*self.H[k]
        norm = np.abs(point).max()
        if scores[j, k] <= 0 or norm < 1e-14:
            return None, 0.
        return np.round(point/norm, 6), scores[j, k]

    def segment_upper(self, k, lo, hi, cutoff):
        """Maximize the concave log-likelihood between two successive zeros.

        The tangent at the interior mode (or a midpoint) bounds the segment
        maximum in real arithmetic. End-point maxima are selected by derivative
        signs. A numerical guard is applied by the caller.
        """
        marks = self.marks[k:]
        a, h = self.linear[k], self.curvature[k]
        denom = self.log_den[k:].sum()
        def value(b):
            return a*b-h*b*b/2+log_trigger(marks-b).sum()-denom

        def slope(b):
            x = marks-b
            return a-h*b-(Z*x/np.expm1(Z*x*x/2)).sum()

        if lo == hi:
            return value(lo)
        middle = (lo+hi)/2
        derivative = slope(middle)
        middle_value = value(middle)
        tangent = middle_value+max((lo-middle)*derivative, (hi-middle)*derivative)
        if tangent + GUARD < cutoff or middle_value >= cutoff:
            return tangent
        # Each possible zero is an explicit partition boundary. The slope
        # just to its right/left tends to positive/negative infinity.
        left_zero, right_zero = np.any(marks == lo), np.any(marks == hi)
        if not left_zero and slope(lo) <= 0:
            return value(lo)
        if not right_zero and slope(hi) >= 0:
            return value(hi)

        def bracket_slope(b):
            if b == lo and left_zero:
                return np.inf
            if b == hi and right_zero:
                return -np.inf
            return slope(b)

        root = brentq(bracket_slope, lo, hi, xtol=1e-14)
        if not lo < root < hi:
            return tangent
        derivative = slope(root)
        upper = value(root)+max((lo-root)*derivative, (hi-root)*derivative)
        return min(tangent, upper)

    def certify(self, d, target, cutoff, score):
        if cutoff <= GUARD or score <= cutoff+GUARD:
            return False
        for k, q in enumerate(self.H@d):
            lo, hi = -CAP, CAP
            if q > 0:
                hi = min(hi, target/q)
            elif q < 0:
                lo = max(lo, target/q)
            marks = self.marks[k:]
            cuts = np.r_[lo, np.unique(marks[(lo < marks) & (marks < hi)]), hi]
            for left, right in zip(cuts[:-1], cuts[1:]):
                upper = self.segment_upper(k, left, right, cutoff)
                if not (upper+GUARD < cutoff):
                    return False
        return True

    def accept(self, d, target):
        if self.intervals is None:
            self.intervals = {k: (-CAP, CAP) for k in range(len(self.H))}
        kept = {}
        projections = self.H@d
        for k, (lo, hi) in self.intervals.items():
            q = projections[k]
            if q > 0:
                lo = max(lo, target/q)
            elif q < 0:
                hi = min(hi, target/q)
            else:
                continue
            if lo <= hi:
                kept[k] = (lo, hi)
        self.intervals = kept
        if not any(np.array_equal(v, d) for v in self.directions):
            self.directions.append(d)
        if self.old is None or np.linalg.norm(ideal(d,target)) > np.linalg.norm(ideal(*self.old)):
            self.old = d, target
