"""Incremental adjoint projection cache for the Stage 7 outer set."""
from __future__ import annotations
from fractions import Fraction as F

from fixed_amplitude import IntervalFixedAmplitudeEnvelope, interval_fraction
from exact_linear import inverse, matmul, transpose


class CachedIntervalEnvelope(IntervalFixedAmplitudeEnvelope):
    """Cache d^T W H_{k,t} and update it by one scalar injection term.

    If d_{t+1}=W^{-1}F_{t+1}^{-T}Wd_t, then for every retained onset k,
    q_{k,t+1}=q_{k,t}+gamma*d_{t+1}^T W K_1. This avoids a fresh 2D inner
    product for every (direction,onset,time) tuple.
    """

    def __init__(self, model, track_responses=True):
        super().__init__(model, track_responses=track_responses)
        self.direction_cache = {}

    def _make_state(self, direction):
        d = tuple(F(x) for x in direction)
        return {"d": d, "q": {k: self._q_interval(d, self.responses[k])
                               for k in self.bounds}}

    def advance(self, sent):
        Fmat, K = super().advance(sent)
        for state in self.direction_cache.values():
            d = state["d"]
            Wd = matmul(self.W, [[x] for x in d])
            moved = matmul(inverse(self.W), matmul(transpose(inverse(Fmat)), Wd))
            dnew = tuple(row[0] for row in moved)
            if sent:
                injection = sum((dnew[i] * sum((self.W[i][j] * K[j][0]
                                               for j in range(len(dnew))), F(0))
                                 for i in range(len(dnew))), F(0))
                inc = interval_fraction(injection)
            else:
                inc = None
            state["q"] = {k: (q if inc is None else q + inc)
                           for k, q in state["q"].items() if k in self.bounds}
            state["d"] = dnew
        return Fmat, K

    def add_certificate(self, direction, z):
        result = super().add_certificate(direction, z)
        # Prune old coefficient caches with the exact same onset intersection.
        for state in self.direction_cache.values():
            state["q"] = {k: q for k, q in state["q"].items() if k in self.bounds}
        key = tuple(F(x) for x in direction)
        if key not in self.direction_cache:
            self.direction_cache[key] = self._make_state(key)
        return result

    def _support_from_state(self, state):
        supports = []
        for k, q in state["q"].items():
            lo, hi = self.bounds[k]
            amplitude = lo if q.lo >= 0 else hi
            supports.append(q * interval_fraction(amplitude))
        return min((F(str(value.lo)) for value in supports), default=None)

    def directional_action(self, direction, l1_cap=None):
        d = tuple(F(x) for x in direction)
        state = self.direction_cache.get(d)
        if state is None:
            return super().directional_action(d, l1_cap)
        support = self._support_from_state(state)
        denom = sum((d[i] * self.W[i][j] * d[j]
                     for i in range(len(d)) for j in range(len(d))), F(0))
        if support is None or support <= 0 or denom <= 0:
            return {"action": tuple(F(0) for _ in d), "support": support,
                    "guaranteed_gain": F(0), "uncapped_gain": F(0)}
        action = tuple(support / denom * x for x in d)
        uncapped = support * support / denom
        if l1_cap is not None:
            cap = F(l1_cap)
            l1 = sum((abs(x) for x in action), F(0))
            if l1 > cap:
                action = tuple(cap / l1 * x for x in action)
        gain = sum((action[i] * self.W[i][j] * action[j]
                    for i in range(len(d)) for j in range(len(d))), F(0))
        return {"action": action, "support": support,
                "guaranteed_gain": gain, "uncapped_gain": uncapped}
