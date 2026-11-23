"""Outward bounds for a single Gaussian/trigger rounding-cell kernel.

The caller must supply valid conditional Gaussian parameters. This module does
not assert Gaussian closure after previous rounded observations.
"""
import math

from numerical_record import binary64_rounding_cell, binary64_value, exact_value, interval_fraction, I


def scalar_box(value):
    if isinstance(value, (tuple, list)):
        lo, hi = map(exact_value, value)
    else:
        lo = hi = exact_value(value)
    if lo > hi:
        raise ValueError("Reversed parameter interval")
    return I(interval_fraction(lo).lo, interval_fraction(hi).hi)


def unnormalized_mass(cell, mean, variance, trigger_center, precision, pieces=16):
    """Enclose integral exp(-(u-mean)^2/(2*S))*h(u-center) du.

    The Gaussian normalizing factor is omitted. Lower and upper Riemann
    enclosures apply uniformly to each supplied parameter interval.
    """
    lo, hi = map(exact_value, cell)
    if lo >= hi or not isinstance(pieces, int) or isinstance(pieces, bool) or pieces < 1:
        raise ValueError("A positive-width cell and positive partition count are required")
    mu, S = scalar_box(mean), scalar_box(variance)
    center, Z = scalar_box(trigger_center), scalar_box(precision)
    if S.lo <= 0 or Z.lo <= 0:
        raise ValueError("Variance and trigger precision must be positive")
    width = (hi - lo) / pieces
    total = I.exact(0)
    for i in range(pieces):
        u = scalar_box((lo + i * width, lo + (i + 1) * width))
        gaussian = (-((u - mu).square()) / (2 * S)).exp()
        z = Z * (u - center).square() / 2
        # For z>=0, z/(1+z) <= 1-exp(-z) <= min(z,1).
        # This avoids cancellation and preserves positivity around zero.
        lower = (I.exact(z.lo) / (1 + I.exact(z.lo))).lo
        upper = min(z.hi, I.exact(1).hi)
        trigger = I(lower, upper)
        total = total + interval_fraction(width) * gaussian * trigger
    return total


def rounded_ratio(received, mean_candidate, mean_healthy, variance,
                  center_candidate, center_healthy, precision, pieces=16):
    """Return a conservative one-step ratio, or None if unresolved.

    Both hypotheses must have the same conditional variance. The arguments
    are values or endpoint pairs in the physical payload coordinate.
    """
    cell = binary64_rounding_cell(received)
    # Signed zero is observable in a binary64 bit-pattern record. The shared
    # endpoint has probability zero under the continuous input model.
    if received == 0.0:
        half_subnormal = binary64_value(math.ulp(0.0)) / 2
        cell = (-half_subnormal, 0) if math.copysign(1.0, received) < 0 else (0, half_subnormal)
    numerator = unnormalized_mass(cell, mean_candidate, variance, center_candidate, precision, pieces)
    denominator = unnormalized_mass(cell, mean_healthy, variance, center_healthy, precision, pieces)
    if denominator.lo <= 0:
        return None
    return numerator / denominator
