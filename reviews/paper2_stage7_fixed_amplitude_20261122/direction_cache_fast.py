"""Fast conservative adjoint support cache storing one-sided Decimal bounds."""
from __future__ import annotations
from decimal import ROUND_FLOOR
from fractions import Fraction as F

from fixed_amplitude import IntervalFixedAmplitudeEnvelope, interval_fraction
from interval_arithmetic import rounded
from exact_linear import inverse, matmul, transpose


class FastCachedEnvelope(IntervalFixedAmplitudeEnvelope):
    """Update one outward lower projection per (direction,onset).

    For q_k=d^T W H_k and d+=W^-1 F^-T Wd,
    q_k+=q_k + d+^T W K_1 when a send occurs. A lower Decimal bound is
    propagated by adding an outward-rounded lower bound on that exact scalar.
    """

    def __init__(self, model, track_responses=True):
        super().__init__(model, track_responses=track_responses)
        self.direction_cache = {}

    def _make_state(self, direction):
        d = tuple(F(x) for x in direction)
        q = {k: self._q_interval(d, self.responses[k]).lo for k in self.bounds}
        return {"d": d, "q_lower": q}

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
                inc_lower = interval_fraction(injection).lo
                qlower = {k: rounded(lambda q=q, inc=inc_lower: q + inc, ROUND_FLOOR)
                          for k, q in state["q_lower"].items() if k in self.bounds}
            else:
                qlower = {k: q for k, q in state["q_lower"].items() if k in self.bounds}
            state["q_lower"] = qlower
            state["d"] = dnew
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
        supports = []
        for k, q in state["q_lower"].items():
            _, hi = self.bounds[k]
            amplitude = self.bounds[k][0] if q >= 0 else hi
            supports.append(F(str(q)) * amplitude)
        return min(supports, default=None)

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
