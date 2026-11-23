"""Short-horizon joint-mass enclosures for the one-rounding observation law."""
from dataclasses import dataclass
from fractions import Fraction as F
from functools import lru_cache
from pathlib import Path
import math
import sys

CONTRACT = Path(__file__).resolve().parents[1] / "paper2_stage10_numerical_contract_20261123"
sys.path.insert(0, str(CONTRACT))
from numerical_record import I, binary64_rounding_cell, interval_fraction as frac
from exact_linear import add, matmul, matrix, transpose, update


@dataclass(frozen=True)
class Reading:
    center: float
    word: float | None  # None denotes silence

    def __post_init__(self):
        for value in (self.center, self.word):
            if value is not None and (type(value) is not float or not math.isfinite(value)):
                raise ValueError("A finite binary64 word is required")
        if self.center is None:
            raise ValueError("The common center must be present")

    def physical_cell(self, bias):
        if self.word is None:
            raise ValueError("Silence has no payload cell")
        lo, hi = binary64_rounding_cell(self.word)
        if self.word == 0.0:
            if math.copysign(1., self.word) > 0:
                lo = F(0)
            else:
                hi = F(0)
        return lo - bias, hi - bias


def box(lo, hi):
    return I(frac(lo).lo, frac(hi).hi)


@lru_cache(maxsize=1)
def pi_box():
    # Machin identity, alternating arctangent remainder between adjacent sums.
    def atan_inv(q):
        partial = sum((F((-1)**i, (2*i+1)*q**(2*i+1)) for i in range(48)), F(0))
        return box(partial, partial + F(1, 97*q**97))
    return 16*atan_inv(5) - 4*atan_inv(239)


def attenuation(z):
    # (1-exp(-z))/z, including the limit 1; intersect two valid enclosures.
    if z == 0:
        return I.exact(1)
    iz = frac(z)
    analytic = I((1 / (1 + iz)).lo, I.exact(1).hi)
    if iz.lo == 0:
        return analytic
    direct = (1 - (-iz).exp()) / iz
    return I(max(analytic.lo, direct.lo), min(analytic.hi, direct.hi))


def trigger_integral(lo, hi, center, Z):
    # Integrate the vanishing quadratic exactly, then bound its smooth multiplier.
    a, b = lo - center, hi - center
    zmin = F(0) if a <= 0 <= b else Z*min(a*a, b*b)/2
    zmax = Z*max(a*a, b*b)/2
    area = Z*(hi-lo)*(a*a + a*b + b*b)/6
    return frac(area) * I(attenuation(zmax).lo, attenuation(zmin).hi)


def interval_matrix(rows):
    return [[frac(x) for x in row] for row in rows]


def product(rows, vector):
    return tuple(sum((a*b for a,b in zip(row, vector)), I.exact(0)) for row in rows)


def history_bounds(model, readings, onset, amplitude, pieces=2):
    """Bound unnormalized prefix masses by integrating over latent sent cells.

    Each branch encloses all conditional Gaussian means on one latent subbox.
    The weight is a bound on that branch's total mass, not an atom at its mean.
    """
    if type(onset) is not int or onset < 0 or type(pieces) is not int or pieces < 1:
        raise ValueError("Invalid onset or partition count")
    if type(amplitude) is float or not 0 <= F(amplitude) <= F(model['attack_amplitude_cap']):
        raise ValueError("Declare a legal exact amplitude")
    A, C, Q, P = (matrix(model[k]) for k in ('A','C','Q','P0_prior'))
    R, Z = F(model['R']), F(model['Z'])
    ai, ci = interval_matrix(A), interval_matrix(C)
    branches = [(tuple(I.exact(0) for _ in A), I.exact(1))]
    prefixes = []
    for t, reading in enumerate(readings):
        sent = reading.word is not None
        center = F.from_float(reading.center)
        S = matmul(matmul(C, P), transpose(C))[0][0] + R
        V = S + 1/Z
        posterior, gain, transition = update(P, C, R if sent else R + 1/Z)
        transform = interval_matrix(transition)
        gains = [frac(row[0]) for row in gain]
        if sent:
            lo, hi = reading.physical_cell(F(amplitude) if t >= onset else F(0))
            width = (hi-lo) / pieces
            cells = []
            for j in range(pieces):
                left, right = lo + j*width, lo + (j+1)*width
                cells.append((box(left, right), trigger_integral(left, right, center, Z)))
            scale = (2*pi_box()*frac(S)).sqrt().reciprocal()
        else:
            cells = [(frac(center), I.exact(1))]
            scale = frac(1+Z*S).sqrt().reciprocal()
        next_branches = []
        variance = frac(2*(S if sent else V))
        for mean, mass in branches:
            measured = product(ci, mean)[0]
            base = product(transform, mean)
            for value, trigger_weight in cells:
                gaussian = (-(value-measured).square()/variance).exp()
                weight = mass * scale * gaussian * trigger_weight
                post = tuple(x+k*value for x,k in zip(base,gains))
                next_branches.append((product(ai, post), weight))
        branches = next_branches
        P = add(matmul(matmul(A, posterior), transpose(A)), Q)
        total = sum((weight for _,weight in branches), I.exact(0))
        if not total.hi.is_finite():
            raise ArithmeticError("Unresolved history mass")
        prefixes.append(total)
    return prefixes
