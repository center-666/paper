"""Certify the emitted binary64 correction using an exact support bound."""

import math
from fractions import Fraction


def weighted_inner(left, right, weight):
    return sum(x * coefficient * y for x, row in zip(left, weight)
               for coefficient, y in zip(row, right))


def certify_output(action, support, bounds, weight, cap):
    """Use s <= inf theta' W action and |theta_i| <= bounds[i]."""
    if not action or len(action) != len(bounds) or len(action) != len(weight):
        raise ValueError("Inconsistent correction dimensions")
    if any(len(row) != len(action) for row in weight):
        raise ValueError("Weight must be square")
    if support < 0 or cap < 0 or any(bound < 0 for bound in bounds):
        raise ValueError("Expected nonnegative certificate, cap, and bounds")
    if sum(map(abs, action)) > cap:
        raise ValueError("Exact correction exceeds the cap")

    output = []
    for value in action:
        rounded = float(value)
        if abs(Fraction.from_float(rounded)) > abs(value):
            rounded = math.nextafter(rounded, 0.0)
        output.append(rounded)
    emitted = tuple(map(Fraction.from_float, output))
    error = tuple(x - y for x, y in zip(emitted, action))
    weighted_error = (sum(coefficient * x for coefficient, x in zip(row, error)) for row in weight)
    support_loss = sum(bound * abs(value) for bound, value in zip(bounds, weighted_error))
    guarantee = 2 * (support - support_loss) - weighted_inner(emitted, emitted, weight)
    if guarantee < 0:
        return (0.0,) * len(action), Fraction(0), True
    return tuple(output), guarantee, False
