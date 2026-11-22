"""Correctly re-keyed one-sided adjoint support cache."""
from __future__ import annotations
from decimal import ROUND_FLOOR
from fractions import Fraction as F

from fixed_amplitude import IntervalFixedAmplitudeEnvelope, interval_fraction
from interval_arithmetic import rounded
from exact_linear import inverse, matmul, transpose


class CorrectedFastEnvelope(IntervalFixedAmplitudeEnvelope):
    """Propagate lower support coefficients and re-key directions each step."""

    def __init__(self, model, track_responses=True):
        super().__init__(model, track_responses=track_responses)
        self.direction_cache = {}

    def _make_state(self, direction):
        d = tuple(F(x) for x in direction)
        return {"d": d, "q_lower": {k: self._q_interval(d, self.responses[k]).lo
                                      for k in self.bounds}}

    def advance(self, sent):
        Fmat, K = super().advance(sent)
        updated = {}
        for state in self.direction_cache.values():
            d = state["d"]
            Wd = matmul(self.W, [[x] for x in d])
            moved = matmul(inverse(self.W), matmul(transpose(inverse(Fmat)), Wd))
            dnew = tuple(row[0] for row in moved)
            if sent:
                injection = sum((dnew[i] * sum((self.W[i][j] * K[j][0]
                                               for j in range(len(dnew))), F(0))
                                 for i in range(len(dnew))), F(0))
                inc_lower = interval_fraction(injection).lo
                qlower = {k: rounded(lambda q=q, inc=inc_lower: q + inc, ROUND_FLOOR)
                          for k, q in state["q_lower"].items() if k in self.bounds}
            else:
                qlower = {k: q for k, q in state["q_lower"].items() if k in self.bounds}
            state["d"] = dnew
            state["q_lower"] = qlower
            if dnew in updated:
                prior = updated[dnew]["q_lower"]
                updated[dnew]["q_lower"] = {k: min(prior[k], qlower[k])
                    for k in prior.keys() & qlower.keys()}
            else:
                updated[dnew] = state
        self.direction_cache = updated
        return Fmat, K

    def add_certificate(self, direction, z):
        result = super().add_certificate(direction, z)
        for state in self.direction_cache.values():
            state["q_lower"] = {k: q for k, q in state["q_lower"].items()
                                if k in self.bounds}
        key = tuple(F(x) for x in direction)
        if key not in self.direction_cache:
            self.direction_cache[key] = self._make_state(key)
        return result

    def _support_from_state(self, state):
        terms = []
        for k, q in state["q_lower"].items():
            lo, hi = self.bounds[k]
            terms.append(F(str(q)) * (lo if q >= 0 else hi))
        return min(terms, default=None)

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
