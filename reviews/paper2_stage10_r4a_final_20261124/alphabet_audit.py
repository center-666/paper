"""R4a-Final helpers for binary64 overflow words and independent mass checks."""
from dataclasses import dataclass
from fractions import Fraction as F
import math

from mixture_history import I, box, pi_box, trigger_integral
from numerical_record import binary64_rounding_cell, interval_fraction as frac


FLOAT_MAX = F.from_float(float.fromhex("0x1.fffffffffffffp+1023"))
OVERFLOW_THRESHOLD = FLOAT_MAX + F(2**970)
assert OVERFLOW_THRESHOLD == 2**1024 - 2**970


@dataclass(frozen=True)
class AlphabetReading:
    center: float
    word: float | None

    def __post_init__(self):
        if type(self.center) is not float or not math.isfinite(self.center):
            raise ValueError("A finite binary64 center is required")
        if self.word is not None and (type(self.word) is not float or math.isnan(self.word)):
            raise ValueError("A payload must be a binary64 code or signed overflow symbol")


def code_cell(word):
    if word == math.inf:
        return OVERFLOW_THRESHOLD, None
    if word == -math.inf:
        return None, -OVERFLOW_THRESHOLD
    if not math.isfinite(word):
        raise ValueError("NaN is not a communication symbol")
    lo,hi=binary64_rounding_cell(word)
    if word == 0.0:
        half=F(1,2**1075)
        return (-half,F(0)) if math.copysign(1.,word)<0 else (F(0),half)
    return lo,hi


def gaussian_tail_upper(standardized_lower):
    """Mills upper bound P[N(0,1)>=x] <= phi(x)/x, x>0."""
    if standardized_lower <= 0:
        return I.exact(1)
    x=frac(standardized_lower)
    phi=(2*pi_box()).sqrt().reciprocal()*(-(x.square()/2)).exp()
    return I.exact(0)+phi/x


def overflow_mass_upper(word,bias,mean,variance):
    if word not in (math.inf,-math.inf):
        raise ValueError("An overflow symbol is required")
    b,mu,S=F(bias),F(mean),F(variance)
    sigma=frac(S).sqrt()
    if word==math.inf:
        distance=OVERFLOW_THRESHOLD-b-mu
    else:
        distance=OVERFLOW_THRESHOLD+b+mu
    if distance<=0:
        return I.exact(1)
    standardized=frac(distance)/sigma
    if standardized.lo<=0:
        return I.exact(1)
    # The selection factor is at most one, so the untriggered Gaussian tail
    # is a rigorous upper bound. Its lower endpoint stays zero when too small
    # for the Decimal exponent range to resolve.
    return gaussian_tail_upper(F(standardized.lo))


def overflow_mass(word,bias,mean,variance,center,precision):
    """Enclose triggered overflow probability; lower zero marks unresolved tails.

    The event factor is bounded by one, so the Mills bound on the corresponding
    untriggered Gaussian tail is valid without resolving its extremely small
    positive value.
    """
    upper=overflow_mass_upper(word,bias,mean,variance)
    return I.exact(0)+I(upper.lo,upper.hi)


def finite_word_mass(word,bias,mean,variance,center,precision,pieces=2):
    """Enclose one finite-code mass by integrating its exact rounding cell."""
    lo,hi=code_cell(word)
    if lo is None or hi is None:
        raise ValueError("A finite binary64 word is required")
    lo-=F(bias)
    hi-=F(bias)
    if not isinstance(pieces,int) or isinstance(pieces,bool) or pieces<1:
        raise ValueError("A positive cell partition count is required")
    width=(hi-lo)/pieces
    total=I.exact(0)
    norm=(2*pi_box()*frac(variance)).sqrt().reciprocal()
    for i in range(pieces):
        a,b=lo+i*width,lo+(i+1)*width
        y=box(a,b)
        gaussian=(-((y-frac(mean)).square())/(2*frac(variance))).exp()
        selection=trigger_integral(a,b,F(center),F(precision))
        total=total+norm*gaussian*selection
    return total


def _density(y,mean,variance,center,precision):
    delta=y-frac(mean)
    gaussian=(2*pi_box()*frac(variance)).sqrt().reciprocal()
    exponent=-(delta.square())/(2*frac(variance))
    trigger=1-(-(frac(precision)*(y-frac(center)).square()/2)).exp()
    trigger=I(max(trigger.lo,I.exact(0).lo),max(trigger.hi,I.exact(0).hi))
    return gaussian*exponent.exp()*trigger


def finite_alphabet_send_integral(mean,variance,center,precision,bias,panels=16384):
    """Enclose aggregate mass of all finite output words by their union interval.

    A midpoint enclosure with a global derivative bound is used on ±12 sigma.
    The omitted Gaussian tails receive a Mills-ratio upper bound.
    """
    if not isinstance(panels,int) or isinstance(panels,bool) or panels<1:
        raise ValueError("A positive integer panel count is required")
    mu,S,c,Z,b=map(F,(mean,variance,center,precision,bias))
    if S<=0 or Z<=0:
        raise ValueError("Variance and trigger precision must be positive")
    sigma=frac(S).sqrt()
    radius=12*F(sigma.hi)
    lo,hi=mu-radius,mu+radius
    finite_lo=-OVERFLOW_THRESHOLD-b
    finite_hi=OVERFLOW_THRESHOLD-b
    if lo<finite_lo or hi>finite_hi:
        raise NotImplementedError("The central integration window crosses an overflow threshold")
    width=(hi-lo)/panels
    midpoint_sum=I.exact(0)
    local_error=I.exact(0)
    phi_peak=(2*pi_box()*frac(S)).sqrt().reciprocal()
    for i in range(panels):
        left=lo+i*width
        right=left+width
        ybox=I(frac(left).lo,frac(right).hi)
        y=frac((left+right)/2)
        midpoint_sum=midpoint_sum+_density(y,mu,S,c,Z)*frac(width)
        state_distance=ybox-frac(mu)
        state_abs=I(min(abs(state_distance.lo),abs(state_distance.hi))
                    if not state_distance.lo<=0<=state_distance.hi else state_distance.lo*0,
                    max(abs(state_distance.lo),abs(state_distance.hi)))
        state_exp=(-state_distance.square()/(2*frac(S))).exp()
        state_derivative=phi_peak*state_abs/frac(S)*state_exp
        trigger_distance=ybox-frac(c)
        trigger_abs=I(min(abs(trigger_distance.lo),abs(trigger_distance.hi))
                      if not trigger_distance.lo<=0<=trigger_distance.hi else trigger_distance.lo*0,
                      max(abs(trigger_distance.lo),abs(trigger_distance.hi)))
        trigger_exp=(-(frac(Z)*trigger_distance.square()/2)).exp()
        trigger_derivative=frac(Z)*trigger_abs*trigger_exp
        phi_box=phi_peak*state_exp
        local_error=local_error+(state_derivative+phi_box*trigger_derivative)*frac(width*width/4)
    error=local_error
    tail=2*gaussian_tail_upper(F(12))
    lower=max(midpoint_sum.lo-error.hi,I.exact(0).lo)
    upper=midpoint_sum.hi+error.hi+tail.hi
    return I(lower,upper), {
        "central_window":[str(lo),str(hi)],
        "panels":panels,
        "midpoint_sum":midpoint_sum.json(),
        "lipschitz_error":str(error.hi),
        "omitted_gaussian_tail_upper":str(tail.hi),
    }
