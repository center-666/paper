"""Predictable rounded-observation reference kernels and interval histories."""
from fractions import Fraction as F
import math

from exact_linear import add, matmul, matrix, transpose, update
from mixture_history import I, box, pi_box, trigger_integral
from numerical_record import binary64_rounding_cell, interval_fraction as frac


def reading_cell(word):
    if not math.isfinite(word):
        raise NotImplementedError('Overflow symbols are described analytically, not in this finite-word prototype')
    lo,hi=binary64_rounding_cell(word)
    if word == 0.0:
        half=F(1,2**1075)
        return (-half,F(0)) if math.copysign(1.,word)<0 else (F(0),half)
    return lo,hi


def sent_mass(reading, bias, mean, variance, trigger_center, Z, pieces=4):
    lo,hi=reading_cell(reading.word)
    lo-=bias
    hi-=bias
    width=(hi-lo)/pieces
    total=I.exact(0)
    normalizer=(2*pi_box()*frac(variance)).sqrt().reciprocal()
    for i in range(pieces):
        a,b=lo+i*width,lo+(i+1)*width
        ybox=box(a,b)
        gaussian=(-((ybox-frac(mean)).square())/(2*frac(variance))).exp()
        selection=trigger_integral(a,b,F.from_float(reading.center),Z)
        total=total+normalizer*gaussian*selection
    return total


def silence_mass(center, mean, variance, Z):
    S=frac(variance)
    V=S+1/frac(Z)
    residual=frac(mean)-frac(F.from_float(center))
    return (1+frac(Z)*S).sqrt().reciprocal()*(-(residual.square())/(2*V)).exp()


def reference_step(reading, bias, variance, Z, pieces=4):
    if reading.word is None:
        return silence_mass(reading.center,F(0),variance,Z)
    return sent_mass(reading,bias,F(0),variance,F.from_float(reading.center),Z,pieces)


def reference_sequence(readings, model, biases=(F(1,20),F(1,10),F(1,4)), pieces=4):
    """Return local reference kernels and each fixed-bias sequence likelihood."""
    A,C,Q,P=(matrix(model[k]) for k in ('A','C','Q','P0_prior'))
    R,Z=F(model['R']),F(model['Z'])
    masses={b:[] for b in biases}
    variances=[]
    for reading in readings:
        sent=reading.word is not None
        S=matmul(matmul(C,P),transpose(C))[0][0]+R
        variances.append(S)
        for b in biases:
            masses[b].append(reference_step(reading,b,S,Z,pieces))
        posterior,_,_=update(P,C,R if sent else R+1/Z)
        P=add(matmul(matmul(A,posterior),transpose(A)),Q)
    return variances,masses


def history_union_upper(model, readings, onset, amplitude, pieces=2):
    """Enclose candidate mass for every fixed b in amplitude, using union cells.

    Each sent physical cell is enlarged to the union over b in the supplied
    interval. This relaxes cross-time equality of b, so the returned mass is an
    upper bound for every fixed candidate in the box.
    """
    blo,bhi=map(F,amplitude)
    if blo<0 or bhi<blo or bhi>F(model['attack_amplitude_cap']):
        raise ValueError('Invalid amplitude interval')
    A,C,Q,P=(matrix(model[k]) for k in ('A','C','Q','P0_prior'))
    R,Z=F(model['R']),F(model['Z'])
    ai=[[frac(x) for x in row] for row in A]
    ci=[[frac(x) for x in row] for row in C]
    branches=[(tuple(I.exact(0) for _ in A),I.exact(1))]
    for t,reading in enumerate(readings):
        sent=reading.word is not None
        S=matmul(matmul(C,P),transpose(C))[0][0]+R
        V=S+1/Z
        posterior,gain,transition=update(P,C,R if sent else R+1/Z)
        tr=[[frac(x) for x in row] for row in transition]
        gains=[frac(row[0]) for row in gain]
        if sent:
            lo,hi=reading_cell(reading.word)
            if t>=onset:
                lo-=bhi
                hi-=blo
            width=(hi-lo)/pieces
            cells=[]
            for j in range(pieces):
                a,b=lo+j*width,lo+(j+1)*width
                cells.append((box(a,b),trigger_integral(a,b,F.from_float(reading.center),Z)))
            scale=(2*pi_box()*frac(S)).sqrt().reciprocal()
        else:
            cells=[(frac(F.from_float(reading.center)),I.exact(1))]
            scale=(1+frac(Z)*frac(S)).sqrt().reciprocal()
        variance=frac(2*(S if sent else V))
        following=[]
        for mean,mass in branches:
            measured=sum((x*y for x,y in zip(ci[0],mean)),I.exact(0))
            base=tuple(sum((x*y for x,y in zip(row,mean)),I.exact(0)) for row in tr)
            for value,trigger in cells:
                gaussian=(-((value-measured).square())/variance).exp()
                weight=mass*scale*gaussian*trigger
                post=tuple(x+k*value for x,k in zip(base,gains))
                pushed=tuple(sum((x*y for x,y in zip(row,post)),I.exact(0)) for row in ai)
                following.append((pushed,weight))
        branches=following
        P=add(matmul(matmul(A,posterior),transpose(A)),Q)
    return sum((weight for _,weight in branches),I.exact(0))
