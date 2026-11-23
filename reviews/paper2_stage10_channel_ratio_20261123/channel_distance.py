"""One-step comparison under a shared continuous Gaussian input and trusted trigger."""
from fractions import Fraction as F
from functools import lru_cache
from pathlib import Path
import json
import math
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/'paper2_stage10_n03r_20261123'))
from mixture_history import I, frac, pi_box

BIAS = F(1,4)
CUTOFF = F(10)
HOLE = F(1,2**54)
NORMAL = (2*pi_box()).sqrt().reciprocal()
LIPSCHITZ = F(2)  # |f'| <= (1+sqrt(3))/sqrt(2*pi*e) for the frozen fixture.


@lru_cache(maxsize=None)
def primitive(x, k):
    """Enclose integral from 0 to x of exp(-k*y*y/2), using positive terms."""
    if x < 0:
        return -primitive(-x,k)
    if x == 0:
        return I.exact(0)
    u = frac(k*x*x/2)
    term = total = I.exact(1)
    for j in range(1,2049):
        term = term*(2*u)/(2*j+1)
        total = total+term
        # Later ratios decrease. If the first is <= 1/2, remaining sum <= term.
        if 4*k*x*x <= 2*(2*j+3) and term.hi <= (total*I.exact('1e-38')).lo:
            return frac(x)*(-u).exp()*I(total.lo,(total+term).hi)
    raise ArithmeticError("unresolved Gaussian integral")


def send_mass(a,b):
    if a > b:
        raise ValueError("reversed integration limits")
    mass = NORMAL*(primitive(b,1)-primitive(a,1)-primitive(b,3)+primitive(a,3))
    return I(max(I.exact(0).lo,mass.lo),mass.hi)


def spacing(x):
    if not x:
        raise ValueError("spacing requested at zero")
    x = abs(x)
    e = x.numerator.bit_length()-x.denominator.bit_length()
    if F(2)**e > x:
        e -= 1
    return F(2)**(e-52)


def periodic_rate(p,q):
    if p < q:
        return p/(2*q)
    return 1-q/p


def guard_region(a,b):
    mid = (a+b)/2
    if abs(mid) < HOLE or abs(mid+BIAS) < HOLE:
        return None
    p, q = spacing(mid),spacing(mid+BIAS)
    assert (BIAS/p).denominator == (BIAS/q).denominator == 1
    period = 2*max(p,q)
    # Both channel outputs of a retained input stay strictly inside (a+bias,b+bias).
    lo = math.ceil((a+2*period)/period)*period
    hi = math.floor((b-2*period)/period)*period
    if lo >= hi:
        return None
    return lo,hi,p,q,period


def show(x):
    return [str(x.lo),str(x.hi)]


def example_word_masses():
    # Adjacent interior output words, with the exact same physical input law.
    entries = []
    u = F(1,2**54)
    for word in (.625,math.nextafter(.625,math.inf)):
        mid = F(word)-BIAS
        even = int((F(word)-2*BIAS)/(2*u)) % 2 == 0
        masses = []
        for radius in (u,(3*u if even else u)/2):
            left,right = mid-radius,mid+radius
            x = I(frac(left).lo,frac(right).hi)
            x2 = x.square()
            density = NORMAL*(-x2/2).exp()*(1-(-x2).exp())
            masses.append(frac(2*radius)*density)
        direct,twice = masses
        if even:
            assert twice.lo > direct.hi
        else:
            assert twice.hi < direct.lo
        entries.append({'word_hex':word.hex(),'even':even,'direct':show(direct),
                        'twice':show(twice),'twice_over_direct':show(twice/direct)})
    return entries


def certify_channel():
    breaks = {-CUTOFF,CUTOFF,F(0),-BIAS}
    for origin in (F(0),-BIAS):
        for exponent in range(-54,5):
            for sign in (-1,1):
                x = origin + sign*F(2)**exponent
                if -CUTOFF < x < CUTOFF:
                    breaks.add(x)
    points = sorted(breaks)
    retained = I.exact(0)
    discarded_width = F(0)
    count = 0
    for a,b in zip(points,points[1:]):
        region = guard_region(a,b)
        if region is None:
            discarded_width += b-a
            continue
        lo,hi,p,q,period = region
        discarded_width += lo-a+b-hi
        count += 1
        rate = periodic_rate(p,q)
        if rate:
            error = frac(LIPSCHITZ*period*(hi-lo))
            central = frac(rate)*send_mass(lo,hi)
            retained += I(max(I.exact(0).lo,(central-error).lo),(central+error).hi)
    # Separate floating diagnostic on whole untrimmed slabs via Gaussian CDFs.
    # Its rounding and the discarded edge corrections are covered only by the
    # independent Decimal derivation, not by this point calculation.
    def primitive_float(x):
        return (math.erf(x/math.sqrt(2))-math.erf(x*math.sqrt(1.5))/math.sqrt(3))/2
    diagnostic = 0.
    for a,b in zip(points,points[1:]):
        mid = (a+b)/2
        if abs(mid) >= HOLE and abs(mid+BIAS) >= HOLE:
            pin = math.ulp(abs(float(mid)))
            pout = math.ulp(abs(float(mid+BIAS)))
            # Two adjacent breakpoints can be closer than one float ULP here.
            if float(spacing(mid)) != pin or float(spacing(mid+BIAS)) != pout:
                continue
            rate = pin/(2*pout) if pin < pout else 1-pout/pin
            diagnostic += rate*(primitive_float(float(b))-primitive_float(float(a)))
    # Use f<=1/2 inside, and the normal Mills bound outside.
    tails = 2*NORMAL*(-frac(CUTOFF**2/2)).exp()/frac(CUTOFF)
    lost = frac(discarded_width/2)+tails
    cap = (retained+lost).hi
    mismatch = I(retained.lo,cap)
    tv = I(max(I.exact(0).lo,(retained-lost).lo),cap)
    assert float(tv.lo) <= diagnostic <= float(tv.hi)
    # On this complete binade the exact output-word mass imbalance has a fixed sign by parity.
    a,b = BIAS,2*BIAS
    q = spacing((a+b)/2+BIAS)
    error = frac(LIPSCHITZ*2*q*(b-a))
    mass = send_mass(a,b)
    central = mass/4
    local = I((central-error).lo,(central+error).hi)
    send = 1-frac(3).sqrt().reciprocal()
    return {'fixture':{'b':'1/4','mu':0,'c':0,'S':1,'Z':2,'rounding':'nearest-even'},
            'binade':{'interval':'[1/4,1/2)','mismatch_length':'1/16','fraction':'1/4',
                      'word_examples':example_word_masses(),
                      'send_mass':show(mass),'mismatch_and_submeasure_tv':show(local),
                      'conditional_on_binade_and_send':show(local/mass)},
            'full':{'retained_regions':count,'discarded_width':str(discarded_width),
                    'whole_slab_erf_diagnostic':diagnostic,
                    'discarded_send_mass_upper':str(lost.hi),'tail_upper':str(tails.hi),
                    'mismatch':show(mismatch),'output_tv':show(tv),'send_mass':show(send),
                    'tv_given_send':show(tv/send)}}


def check_periods():
    # Independent enumeration of transitions on exact rational grids.
    def rn(x,step):
        return round(x/step)*step
    for ratio in (F(1,16),F(1,4),F(1,2),F(1),F(2),F(4),F(16)):
        p,q = ratio,F(1)
        period = 2*max(p,q)
        step = min(p,q)/2
        words = {}
        disagree = F(0)
        for i in range(int(period/step)):
            x = (F(i)+F(1,2))*step
            direct = rn(x,q) % period
            twice = rn(rn(x,p),q) % period
            words[direct] = words.get(direct,0)-step
            words[twice] = words.get(twice,0)+step
            disagree += step*(direct != twice)
        assert sum(map(abs,words.values()))/2 == disagree == periodic_rate(p,q)*period
    # Actual binary64 additions, both sides of ties and binade boundaries.
    u = F(1,2**54)
    for n in (0,1,2,3,4,5,2**52-3,2**52-2,2**52-1,2**52):
        for j in (-3,-1,1,3):
            x = BIAS+n*u+j*u/8
            if not BIAS <= x < 2*BIAS:
                continue
            direct, twice = float(x+BIAS), float(x)+float(BIAS)
            changes = (n%4==1 and j>0) or (n%4==3 and j<0)
            assert (direct != twice) == changes
            if changes:
                assert int((F(twice)-2*BIAS)/(2*u))%2==0
    return True


if __name__ == '__main__':
    check_periods()
    result = certify_channel()
    (HERE/'channel.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps(result,indent=2))
