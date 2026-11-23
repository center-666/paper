"""Deterministic diagnostics for rounded-cell probability bounds."""
from decimal import Decimal, localcontext
from fractions import Fraction
import math

from scipy.integrate import quad
from scipy.special import ndtr

from numerical_record import binary64_rounding_cell
from rounded_mass import rounded_ratio, unnormalized_mass


def decimal_fraction(x):
    return Decimal(x.numerator) / Decimal(x.denominator)


def main():
    # Direct midpoint quadrature is an independent numerical diagnostic. The
    # certified enclosure follows from the inequalities in rounded_mass.py.
    scenarios = [
        (0.2, Fraction(".02"), Fraction(".4"), Fraction(".001"), Fraction(2)),
        (0.0, Fraction(0), Fraction(1), Fraction(0), Fraction(2)),
        (math.ulp(0.0), Fraction(0), Fraction(1), Fraction(0), Fraction(2)),
        (-1.2, Fraction(".3"), Fraction(".7"), Fraction("-.5"), Fraction(2)),
    ]
    for value, mean, variance, center, precision in scenarios:
        cell = binary64_rounding_cell(value)
        mass = unnormalized_mass(cell, mean, variance, center, precision)
        assert mass.lo > 0 and mass.hi >= mass.lo
        with localcontext() as context:
            context.prec = 1150
            lo, hi = map(decimal_fraction, cell)
            mu, S, c, Z = map(decimal_fraction, (mean, variance, center, precision))
            count = 512
            step = (hi-lo)/count
            total = Decimal(0)
            for i in range(count):
                u = lo + (Decimal(i)+Decimal(".5"))*step
                gaussian = (-((u-mu)**2)/(2*S)).exp()
                trigger = 1-(-Z*(u-c)**2/2).exp()
                total += gaussian*trigger*step
            assert mass.lo <= total <= mass.hi, (value, mass, total)
    for value in (0., 0.2, -1.2):
        ratio = rounded_ratio(value, "0", "0", "1", "0", "0", "2")
        assert ratio is not None and ratio.lo <= 1 <= ratio.hi
    # Analytic difference against direct integration on a non-tiny interval.
    lo, hi, mu, S, center, Z = -.9, 1.1, .25, .7, -.15, 2.
    adjusted_S = S/(1+Z*S)
    adjusted_mu = (mu+Z*S*center)/(1+Z*S)
    p = math.exp(-(mu-center)**2/(2*(S+1/Z)))/math.sqrt(1+Z*S)
    delta = lambda m, s: ndtr((hi-m)/math.sqrt(s))-ndtr((lo-m)/math.sqrt(s))
    formula = delta(mu,S)-p*delta(adjusted_mu,adjusted_S)
    direct = quad(lambda u: math.exp(-(u-mu)**2/(2*S))/math.sqrt(2*math.pi*S)
                  * (-math.expm1(-Z*(u-center)**2/2)), lo, hi, epsabs=1e-13)[0]
    assert abs(formula-direct) < 1e-13
    print("PASS: four rounded-cell mass diagnostics, three ratios, analytic identity")


if __name__ == "__main__":
    main()
