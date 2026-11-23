"""Conservative primitives for interval-valued observations.

These enclose pointwise likelihood factors and do not implement the probability
mass of a rounded observation or a sequential confidence process.
"""
from numerical_record import exact_value, finite_decimal, interval_fraction, I, log_trigger


def bounds(values):
    lo, hi = (exact_value(value) for value in values)
    if lo > hi:
        raise ValueError("Interval endpoints are reversed")
    return lo, hi


def center_contract(center, measured_prior, half_width):
    """Classify all possible actual residuals as legal, illegal or unresolved."""
    center_lo, center_hi = bounds(center)
    prior_lo, prior_hi = bounds(measured_prior)
    delta = exact_value(half_width)
    if delta <= 0:
        raise ValueError("A positive quantization half-width is required")
    lo, hi = center_lo - prior_hi, center_hi - prior_lo
    if -delta <= lo and hi <= delta:
        return "legal"
    if hi < -delta or lo > delta:
        return "illegal"
    return "unresolved"


def box(values):
    lo, hi = bounds(values)
    return I(interval_fraction(lo).lo, interval_fraction(hi).hi)


def selection_log_ratio(payload, center, amplitude, trigger_precision):
    """Enclose log h(payload-center-amplitude)-log h(payload-center).

    None denotes an unresolved denominator, including a possible healthy zero.
    The numerator can legitimately have lower endpoint negative infinity.
    """
    Z = exact_value(trigger_precision)
    if Z <= 0:
        raise ValueError("A positive trigger precision is required")
    z = str(finite_decimal(Z))
    residual = box(payload) - box(center)
    denominator = log_trigger(residual, z)
    if not denominator.lo.is_finite():
        return None
    numerator = log_trigger(residual - box(amplitude), z)
    return numerator - denominator
