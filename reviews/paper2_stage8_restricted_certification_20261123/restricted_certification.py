"""Continuous likelihood certification restricted to a valid fixed-amplitude outer set.

The restriction is safe only after a previous positive certificate has been
accepted under the same full-time confidence sequence. The outer set must be
an outward interval envelope indexed by onset. Before that point callers must
use VectorRecord.certify_direction over the full [0,bmax] domain.
"""
from __future__ import annotations

import heapq
from decimal import Decimal, localcontext
from fractions import Fraction as F
from pathlib import Path
import sys

STAGE6 = Path(__file__).resolve().parents[1] / "paper2_stage6_vector_correction_20261122"
if str(STAGE6) not in sys.path:
    sys.path.insert(0, str(STAGE6))

from vector_record import I, D, PRECISION, interval_fraction
from strong_concavity import positive_quadratic_max
from projection import inner


def _box(lo, hi):
    lo, hi = D(lo), D(hi)
    if not lo.is_finite() or not hi.is_finite() or lo < 0 or hi < lo:
        raise ValueError("Invalid nonnegative amplitude interval")
    return I(lo, hi)


def _restricted_witness(record, bounds, threshold, bmax):
    """Find a finite witness inside the retained domain.

    Failure to find one is treated as unresolved. The endpoint/midpoint check
    is only a gate; all surviving intervals are still certified continuously
    by branch-and-bound below.
    """
    for k, (lo, hi) in sorted(bounds.items()):
        points = [lo, hi]
        with localcontext() as ctx:
            ctx.prec = PRECISION
            points.append((lo + hi) / 2)
        for b in points:
            value = record.likelihood(k, I.exact(b))
            if value.lo > threshold.hi:
                return {"onset": k, "amplitude": str(b)}
    return None


def certify_direction_restricted(record, direction, z, bounds,
                                 epsilon=".001", bmax=".25", max_nodes=256,
                                 require_witness=False):
    """Certify a direction over onset-specific fixed-amplitude intervals.

    ``bounds`` is a mapping ``onset -> (lower, upper)`` produced by a prior
    valid certificate. The previous certificate excludes all parameters
    outside this domain on the common confidence event; this routine spends
    no new failure budget for those already-excluded parameters.
    """
    d = tuple(F(x) for x in direction)
    z = D(z)
    bmax_d = D(bmax)
    norm = inner(d, d, record.W)
    if norm <= 0 or z <= 0 or not z.is_finite() or not 0 < D(epsilon) < 1:
        raise ValueError("Invalid direction or confidence parameters")
    if bmax_d <= 0:
        raise ValueError("Invalid amplitude cap")

    clean = {}
    for k, interval in bounds.items():
        if len(interval) != 2:
            raise ValueError("Each retained onset needs [lower, upper]")
        raw_lo, raw_hi = interval
        lo = D(str(raw_lo)) if not isinstance(raw_lo, F) else interval_fraction(raw_lo).lo
        raw_hi_d = D(str(raw_hi)) if not isinstance(raw_hi, F) else interval_fraction(raw_hi).hi
        if lo < 0 or raw_hi_d < lo:
            raise ValueError("Invalid retained amplitude interval")
        if lo > bmax_d:
            continue
        hi = min(raw_hi_d, bmax_d)
        if hi < lo:
            continue
        clean[int(k)] = (lo, hi)

    for k in clean:
        if k < 0 or k >= len(record.candidates):
            raise ValueError("Retained onset is outside the record")

    threshold = (I.exact(epsilon) * record.ref).ln()
    out = {
        "certified": False,
        "correction": ["0", "0"],
        "guaranteed_gain": "0",
        "nodes": 0,
        "segments_tested": 0,
        "reason": "",
        "target_support": str(z),
        "reference_log_cutoff": threshold.json(),
        "restricted": True,
        "witness_check_performed": bool(require_witness),
        "search_onsets": len(clean),
        "search_width": str(sum((hi - lo for lo, hi in clean.values()), D(0))),
    }
    if not clean:
        out["reason"] = "EMPTY_RETAINED_DOMAIN"
        return out
    if threshold.lo <= 0:
        out["reason"] = "HEALTH_OR_FUTURE_START_RETAINED"
        return out

    if require_witness:
        witness = _restricted_witness(record, clean, threshold, bmax_d)
        if witness is None:
            out["reason"] = "RESTRICTED_WITNESS_UNRESOLVED"
            return out
        out["nonempty_witness"] = witness

    jobs = []
    serial = 0
    unresolved_points = []
    for k, (lo, hi) in sorted(clean.items()):
        candidate = record.candidates[k]
        a = record.support_coefficient(k, d)
        # If the lower support coefficient is positive, amplitudes above
        # z/a cannot be low-support. With interval uncertainty, using a.lo
        # is conservative; a.lo<=0 retains the complete interval.
        upper = hi
        if a.lo > 0:
            upper = min(upper, (I.exact(z) / I.exact(a.lo)).hi)
        if upper < lo:
            continue
        if upper == lo:
            point_support = a * I.exact(lo)
            if point_support.lo < z:
                point_bound = record.likelihood(k, I.exact(lo)).hi
                if point_bound >= threshold.lo:
                    unresolved_points.append({"onset": k, "amplitude": str(lo),
                                              "support_lower": str(point_support.lo),
                                              "likelihood_upper": str(point_bound)})
            continue
        cuts = [lo, upper]
        for mark in record.marks[k:]:
            if mark is None:
                continue
            zero = mark[0]
            if lo < zero < upper:
                cuts.append(zero)
        cuts = sorted(set(cuts))
        for left, right in zip(cuts, cuts[1:]):
            interval = I(left, right)
            bound = record.tangent_upper(k, interval)
            out["segments_tested"] += 1
            if bound >= threshold.lo:
                heapq.heappush(jobs, (-bound, serial, k, interval))
                serial += 1

    if unresolved_points:
        out["unresolved_point_candidates"] = unresolved_points
        out["reason"] = "UNRESOLVED_POINT_CANDIDATE"
        return out

    while jobs:
        if out["nodes"] >= max_nodes:
            out["reason"] = "UNRESOLVED_NODE_LIMIT"
            return out
        _, _, k, interval = heapq.heappop(jobs)
        out["nodes"] += 1
        if interval.hi - interval.lo <= D(".00000001"):
            out["reason"] = "UNRESOLVED_OR_FEASIBLE"
            return out
        with localcontext() as ctx:
            ctx.prec = PRECISION
            mid = (interval.lo + interval.hi) / 2
        for child in (I(interval.lo, mid), I(mid, interval.hi)):
            upper = record.tangent_upper(k, child)
            if upper >= threshold.lo:
                heapq.heappush(jobs, (-upper, serial, k, child))
                serial += 1

    alpha = F(z) / norm
    correction = tuple(alpha * x for x in d)
    out.update(
        certified=True,
        correction=[str(x) for x in correction],
        guaranteed_gain=str(F(z) ** 2 / norm),
        reason="ALL_RETAINED_LOW_SUPPORT_MODELS_EXCLUDED",
    )
    return out
