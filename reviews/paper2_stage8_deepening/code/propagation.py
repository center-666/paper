"""Signed fixed-amplitude contamination envelopes for arbitrary state dimension."""
from __future__ import annotations

from fractions import Fraction as F

from models import Plant, add_vectors, matvec


def response_step(plant: Plant, transition, gain, response, sent: bool,
                  attack_channel: int = 0, attack_active: bool | None = None):
    """Advance H after a measurement update and known system dynamics."""
    propagated = matvec(transition, response)
    if attack_active is None:
        attack_active = sent
    if sent and attack_active:
        for state_index in range(len(propagated)):
            propagated[state_index] += gain[state_index][attack_channel]
    return matvec(plant.A, propagated)


def contamination_step(plant: Plant, transition, gain, contamination, sent: bool,
                       amplitude: F, attack_channel: int = 0):
    response = response_step(plant, transition, gain,
                             [x / amplitude for x in contamination] if amplitude else [F(0)] * plant.n,
                             sent, attack_channel)
    return [amplitude * x for x in response]


def signed_initial_intervals(plant: Plant, bmax: F):
    return {k: (F(-bmax), F(bmax)) for k in range(1)}


def intersect_signed_interval(interval, projection, support):
    """Intersect b in [lo, hi] with projection*b >= support."""
    lo, hi = interval
    if projection > 0:
        lo = max(lo, support / projection)
    elif projection < 0:
        hi = min(hi, support / projection)
    else:
        return None
    return (lo, hi) if lo <= hi else None


def update_signed_intervals(intervals, responses, direction, weight, support):
    """Apply one directional certificate to all onset intervals.

    The response and direction are exact rational vectors. An empty interval is
    removed. Zero projection cannot satisfy a strictly positive certificate.
    """
    updated = {}
    weighted_direction = matvec(weight, direction)
    for onset, interval in intervals.items():
        response = responses[onset]
        projection = sum((x * y for x, y in zip(weighted_direction, response)), F(0))
        result = intersect_signed_interval(interval, projection, support)
        if result is not None:
            updated[onset] = result
    return updated
