"""Batch-integral bounds using integer/rational arithmetic only (short records)."""
from fractions import Fraction as F
from math import isqrt, prod
from functools import lru_cache

GRID = 1 << 170


def down(x):
    return F(x.numerator*GRID // x.denominator, GRID)


def up(x):
    return -down(-x)


@lru_cache(maxsize=256)
def exp_negative(x):
    """Bounds exp(-x) by two neighboring partial sums and range reduction."""
    if x < 0:
        raise ValueError('Nonnegative exponent magnitude required')
    if x > 256:
        return F(0), F(1)  # Valid coarse fallback outside the diagnostic range.
    halves = 0
    while x > 1:
        x /= 2
        halves += 1

    def series(arg, degree):
        term = total = F(1)
        for i in range(1,degree+1):
            term *= -arg/i
            total += term
        return total

    # For arguments in [0,1], odd/ even degrees give lower/upper bounds.
    lo = max(F(0), down(series(up(x),39)))
    hi = min(F(1), up(series(down(x),40)))
    for _ in range(halves):
        lo, hi = down(lo*lo), up(hi*hi)
    return lo,hi


def sqrt_bounds(x):
    q = isqrt((x.numerator*GRID*GRID)//x.denominator)
    return F(q,GRID),F(q+1,GRID)


@lru_cache(maxsize=1)
def pi_bounds():
    def atan_small(q):
        even_sum = sum((F((-1)**j,(2*j+1)*q**(2*j+1)) for j in range(32)),F(0))
        return even_sum, even_sum + F(1,65*q**65)
    a,b = atan_small(5)
    c,d = atan_small(239)
    return 16*a-4*d,16*b-4*c


def squared(box):
    lo, hi = box
    return (F(0) if lo<=0<=hi else min(lo*lo,hi*hi)), max(lo*lo,hi*hi)


def psi(z):
    # Integral of exp(-t*z) for t in [0,1]. The linear lower bound follows
    # from exp(-s)>=1-s and remains useful when z is subnormal-sized.
    if z == 0:
        return F(1),F(1)
    l,u = exp_negative(z)
    return max(F(0),1-z/2,(1-u)/z), min(F(1),(1-l)/z)


def batch_bounds(rows, physical_boxes, L, pivots, Z):
    """Enclose the unfiltered joint Gaussian integral over the product of cells."""
    projected = []
    qlo = qhi = F(0)
    alo = ahi = F(1)
    sends = 0
    for i, (row,(a,b)) in enumerate(zip(rows,physical_boxes)):
        lo,hi = a,b
        for j,(u,v) in enumerate(projected):
            coefficient = L[i][j]
            lo -= max(coefficient*u,coefficient*v)
            hi -= min(coefficient*u,coefficient*v)
        projected.append((lo,hi))
        small,large = squared((lo,hi))
        qlo += small/(2*pivots[i])
        qhi += large/(2*pivots[i])
        if row.word is not None:
            sends += 1
            c = F.from_float(row.center)
            left, right = a-c,b-c
            small, large = squared((left,right))
            # Positive integral of z via midpoint and uniform-cell variance.
            area = Z*(b-a)*(((left+right)/2)**2+(b-a)**2/12)/2
            alo *= area*psi(Z*large/2)[0]
            ahi *= area*psi(Z*small/2)[1]
    pi_lo, pi_hi = pi_bounds()
    common = prod(pivots)*Z**(len(rows)-sends)
    norm_lo = sqrt_bounds(common*(2*pi_lo)**sends)[0]
    norm_hi = sqrt_bounds(common*(2*pi_hi)**sends)[1]
    if norm_lo == 0:
        raise ArithmeticError('Unresolved normalizer')
    return alo*exp_negative(qhi)[0]/norm_hi, ahi*exp_negative(qlo)[1]/norm_lo
