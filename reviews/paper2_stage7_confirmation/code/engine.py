"""Single-record Stage 7 comparison. The online class has no truth argument."""
from __future__ import annotations

import hashlib
import json
import math
import os
import struct
import sys
import time
from decimal import Decimal, localcontext
from fractions import Fraction as F
from pathlib import Path
from functools import lru_cache

for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[name] = "1"

import numpy as np

from common import TASK, STAGE6, STAGE7, load_json
sys.path.insert(0, str(STAGE7))
from pilot_v2 import choose_point, exact_mid
from vector_record import VectorRecord
from direction_cache_corrected import CorrectedFastEnvelope
from exact_linear import asfloat, update, add, matmul, transpose, matrix
from fixed_amplitude import transport_halfspace, capped_halfspace_action
import interval_arithmetic
import vector_record

# Both functions are pure with a fixed 50-digit context. Cache exact calls within
# a trajectory, including every interval endpoint; no approximation or pruning.
elementary_cache = lru_cache(maxsize=8192)(interval_arithmetic.elementary)
trigger_cache = lru_cache(maxsize=8192)(vector_record.log_trigger)
interval_arithmetic.elementary = elementary_cache
vector_record.log_trigger = trigger_cache

MODEL = load_json(STAGE6 / "model.json")
SPEC = load_json(STAGE7 / "fresh_protocol.json")
TIMES = tuple(SPEC["certification_times"])
GRID = SPEC["point_estimator_grid"]
A = np.array(MODEL["A"], float)
BMAX = F(1, 4)
W = matrix(MODEL["W"])
CAP = F(1)
USEFUL = F(1, 1600)
ZERO = (F(0), F(0))
# Tolerances for binary64 direct conditional filters on the 608-step horizon.
ABS_TOL = 2e-8
REL_TOL = 2e-10


class ScoredGrid:
    """Observe the grid evaluations performed by the original choose_point."""
    def __init__(self, record):
        self.record = record
        self.candidates = record.candidates
        self.score = Decimal(0)
        self.onset = None

    def all_likelihoods(self, b):
        values = self.record.all_likelihoods(b)
        for onset, box in enumerate(values):
            score = exact_mid(box)
            if score > self.score:
                self.score, self.onset = score, onset
        return values


def simulate(seed, case, index, b, k, steps=608):
    """Stage 7 residual coordinates. Each public frame is generated exactly once."""
    phys, events, phase = [np.random.default_rng(s) for s in
                           np.random.SeedSequence([seed, case, index]).spawn(3)]
    P, C, AX, Q = (matrix(MODEL[name]) for name in ("P0_prior", "C", "A", "Q"))
    process_sqrt = np.linalg.cholesky(np.asarray(MODEL["Q"], float))
    error = np.linalg.cholesky(np.asarray(MODEL["P0_prior"], float)) @ phys.normal(size=2)
    public, private = [], []
    for t in range(steps):
        v = math.sqrt(.2) * phys.normal()
        w = process_sqrt @ phys.normal(size=2)
        r = 0. if not t else float(MODEL["quantization_half_width"]) * (2 * phase.random() - 1)
        y = float(error[0] + v)
        sent = bool(events.random() > math.exp(-(y-r)**2))
        u = y + (b if t >= k else 0.) if sent else None
        post, gain, _ = update(P, C, F(".2") + (0 if sent else F(".5")))
        P = add(matmul(matmul(AX, post), transpose(AX)), Q)
        K = np.asarray(asfloat(gain)).ravel()
        post_error = error - K * (u if sent else r)
        public.append((t, sent, r, u))
        private.append(post_error)
        error = A @ post_error + w
    return public, private


def displacement(monitor, action):
    output = [float(x) - float(a) for x, a in zip(monitor, action)]
    return tuple(F(float(x))-F(y) for x, y in zip(monitor, output))


def publish(monitor, action, radius, cap=CAP):
    """For Stage 7 collinear inward-scaled actions, theta' a >= a' a."""
    if not any(action):
        return ZERO, F(0), False
    actual = displacement(monitor, action)
    support_loss = sum(r*abs(x-y) for r, x, y in zip(radius, action, actual))
    bound = 2*(sum(x*x for x in action)-support_loss)-sum(x*x for x in actual)
    if bound <= 0 or sum(map(abs, actual)) > cap:
        return ZERO, F(0), True
    return actual, bound, False


def point_output(monitor, point):
    # pilot_v2 clips the state which is propagated on the following step.
    length = np.abs(point).sum()
    if length > 1:
        point = point / length
    actual = displacement(monitor, point)
    if sum(map(abs, actual)) > CAP:
        return point, ZERO
    return point, actual


class Online:
    def __init__(self, thresholds):
        self.thresholds = thresholds
        self.points = {name: (np.zeros(2), 0.) for name in thresholds}
        self.monitor = np.zeros(2)
        self.core = VectorRecord(MODEL)
        self.envelope = CorrectedFastEnvelope(MODEL)
        self.old = None
        self.radius = ZERO
        self.prefix = hashlib.sha256()
        self.time = -1
        self.legacy_fallback = False
        self.timing = {"shared_record":0., "point_grid":0., "joint_query":0., "publication":0.}

    def step(self, frame):
        t, sent, r, u = frame
        if t != self.time + 1 or sent != (u is not None):
            raise ValueError("Inconsistent clock or payload")
        self.time = t
        self.prefix.update(struct.pack(">I?dd", t, sent, r, u if sent else 0.))
        fm, km = self.envelope.advance(sent)
        fmat, K = np.array(asfloat(fm)), np.array(asfloat(km)).ravel()
        prior = A @ self.monitor if t else self.monitor
        self.monitor = prior + K * (u if sent else r)
        self.old = transport_halfspace(self.old, fm, km, sent, BMAX)
        # Outward dyadic rounding bounds every possible onset, also for M2.
        factor = 2**48
        self.radius = tuple(F(math.ceil(factor * (sum(abs(x)*v for x,v in zip(row,self.radius))
                               + (abs(g[0])*BMAX if sent else 0))), factor)
                            for row,g in zip(fm,km))
        for name, (point, b) in self.points.items():
            self.points[name] = (fmat @ point + (K*b if sent else 0.), b)
        if t <= TIMES[-1]:
            tick = time.perf_counter()
            self.core.append(sent, repr(u) if sent else None, repr(r))
            self.timing["shared_record"] += time.perf_counter()-tick
        query = None
        if t in TIMES:
            start = time.perf_counter()
            scored = ScoredGrid(self.core)
            d, p, b = choose_point(scored, GRID)
            for name, h in self.thresholds.items():
                self.points[name] = ((p.copy(), float(b)) if scored.score > Decimal(str(h))
                                     else (np.zeros(2), 0.))
            query = dict(t=t, prefix=self.prefix.hexdigest(), score=str(scored.score),
                         onset=scored.onset, amplitude=str(b), direction=list(map(str,d)) if d else None,
                         point_seconds=time.perf_counter()-start, levels=[])
            for level in SPEC["certificate_levels"] if d else ():
                target = F(str(level))*sum(map(abs,d))
                with localcontext() as ctx:
                    ctx.prec = 50
                    z = Decimal(target.numerator)/Decimal(target.denominator)
                assert F(z) == target
                result = self.core.certify_direction(d, str(z), epsilon=".001", max_nodes=64)
                query["levels"].append(dict(level=level, target=str(z), certified=result["certified"],
                                            nodes=result["nodes"], reason=result["reason"],
                                            log_cutoff=result["reference_log_cutoff"]))
                if not result["certified"]:
                    break
                self.envelope.add_certificate(d, target)
                if capped_halfspace_action((d,target), W,CAP)[1] > capped_halfspace_action(self.old,W,CAP)[1]:
                    self.old = d,target
            query["zero_log_cutoff"] = (self.core.ref * ".001").ln().json()
            query["seconds"] = time.perf_counter()-start
            self.timing["point_grid"] += query["point_seconds"]
            self.timing["joint_query"] += query["seconds"]

        tick = time.perf_counter()
        actions = {}
        for name,(point,b) in self.points.items():
            point, actual = point_output(self.monitor, point)
            self.points[name] = point,b
            actions[name] = actual,None,False
        old_action, old_bound = capped_halfspace_action(self.old,W,CAP)
        old = publish(self.monitor,old_action,self.radius)
        best_action, best_bound = ZERO, F(0)
        for d in self.envelope.direction_cache:
            candidate = self.envelope.directional_action(d,CAP)
            if candidate["guaranteed_gain"] > best_bound:
                best_action, best_bound = candidate["action"], candidate["guaranteed_gain"]
        self.legacy_fallback = best_bound < old_bound
        if self.legacy_fallback:
            best_action = old_action
        new = publish(self.monitor,best_action,self.radius) if best_action != old_action else old
        if self.envelope.constraints and not self.envelope.bounds:
            new = ZERO,F(0),True
        elif new[1] < old[1]:
            new = old[0],old[1],True
        actions["M2"], actions["M3"] = old,new
        self.timing["publication"] += time.perf_counter()-tick
        return actions,query,prior,K,fmat


def evaluate(public, private, b, k, thresholds):
    elementary_cache.cache_clear()
    trigger_cache.cache_clear()
    online = Online(thresholds)
    start = k if b else 50
    end = start + 511
    metrics = {name: dict(loss=0.,conditional=0.,certified=0. if name in ("M2","M3") else None,
                          first_nonzero=None, first_in_window=None, useful_steps=0, endpoint=False,
                          preattack=0, nonzero=0, energy=0., fallback=0)
               for name in ["M0",*thresholds,"M2","M3","O"]}
    queries, bounds = [],[]
    H = np.zeros(2)
    mu = np.zeros(2)
    opportunity = max_cross = misses = risk_fails = legacy_steps = 0
    for frame,error in zip(public,private,strict=True):
        t,sent,r,u = frame
        actions,q,prior,K,fm = online.step(frame)
        legacy_steps += int(online.legacy_fallback)
        if q is not None:
            q["point_gain_in_window"] = 0.
            queries.append(q)
        active = t >= k and sent
        H = fm @ H + (K if active else 0.)
        # Independent candidate filter on the same absolute reading. Keep the
        # subtraction in the monitor frame to avoid cancellation of large levels.
        mu_prior = A @ mu
        innovation = (u if sent else r) + (prior[0]-mu_prior[0]) - (b if active else 0.)
        mu = mu_prior + K*innovation
        direct = online.monitor-mu
        delta = b*H
        cross = np.max(np.abs(direct-delta))
        max_cross = max(max_cross,float(cross))
        if cross > ABS_TOL+REL_TOL*np.max(abs(delta)):
            raise ArithmeticError(f"Candidate filter disagrees at {t}: {cross}")
        kept = not online.envelope.constraints or (t >= k and
                       online.envelope.contains_truth_amplitude(k,F(str(b))))
        misses += int(not kept)
        actions["M0"] = ZERO,None,False
        actions["O"] = delta,None,False
        if start <= t <= end:
            opportunity += float(delta@delta)
        for name,(actual,lb,fallback) in actions.items():
            m = metrics[name]
            action = np.asarray(actual,float)
            nonzero = any(actual)
            useful = lb >= USEFUL if lb is not None else nonzero
            cond = float(2*delta@action-action@action)
            if lb is not None:
                assert sum(map(abs,actual)) <= CAP
                risk_fails += int(kept and cond+ABS_TOL < float(lb))
            m["nonzero"] += int(nonzero)
            m["fallback"] += int(fallback)
            if nonzero and m["first_nonzero"] is None:
                m["first_nonzero"] = t
            m["preattack"] += int(t < k and nonzero and b > 0)
            m["energy"] += float(action@action)
            if start <= t <= end:
                m["loss"] += float((error+action)@(error+action))
                if name == "h0" and queries:
                    queries[-1]["point_gain_in_window"] += float(error@error - (error+action)@(error+action))
                m["conditional"] += cond
                if lb is not None:
                    m["certified"] += float(lb)
                if useful:
                    m["useful_steps"] += 1
                    if m["first_in_window"] is None:
                        m["first_in_window"] = t
                if t == end:
                    m["endpoint"] = bool(useful)
        bounds.append([float(actions["M2"][1]),float(actions["M3"][1])])
    return dict(metrics=metrics, queries=queries, bounds=bounds, opportunity=opportunity,
                legacy_fallback_steps=legacy_steps, breakdown=online.timing,
                max_direct_error=max_cross, coverage_missed_steps=misses, risk_violations=risk_fails,
                history_sha256=online.prefix.hexdigest())
