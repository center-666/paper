"""Exact center-visible and index-only kernels for a hidden raw dither phase."""
from __future__ import annotations

import math
import numpy as np
from scipy.special import ndtr


def codeword_intervals(mean:float,delta:float):
    """Return (integer index, phase interval, center-residual interval)."""
    if not math.isfinite(mean) or not math.isfinite(delta) or delta<=0:
        raise ValueError("Expected finite prediction and positive phase width")
    rows=[]
    center=int(math.floor(mean/(2*delta)))
    for n in range(center-1,center+3):
        lo=max(-delta,mean-delta-2*delta*n)
        hi=min(delta,mean+delta-2*delta*n)
        if hi-lo>32*np.finfo(float).eps*max(1.,delta):
            rlo=lo+2*delta*n-mean
            rhi=hi+2*delta*n-mean
            rows.append({"index":n,"phase_lo":lo,"phase_hi":hi,
                         "r_lo":min(rlo,rhi),"r_hi":max(rlo,rhi)})
    total=sum(row["phase_hi"]-row["phase_lo"] for row in rows)
    if abs(total-2*delta)>1e-10*max(1.,delta):
        raise AssertionError("Codeword phase intervals do not cover one period")
    return rows


def silent_probability(P,S,d,r,Z):
    V=S+1/Z
    return math.exp(-.5*(d-r)**2/V)/math.sqrt(1+Z*S)


def center_kernel(P,S,d,b,r,Z,u=None):
    """Silent atom and send subdensity conditional on exact center residual."""
    g=silent_probability(P,S,d,r,Z)
    if u is None:
        return g
    u=np.asarray(u,dtype=float)
    normal=np.exp(-.5*(u-b-d)**2/S)/math.sqrt(2*math.pi*S)
    trig=-np.expm1(-.5*Z*(u-b-r)**2)
    return normal*trig


def index_kernel(P,S,d,b,r_lo,r_hi,Z,u=None):
    """Kernel conditional on integer codeword after integrating hidden phase."""
    length=r_hi-r_lo
    if length<=0:
        raise ValueError("Empty codeword phase cell")
    V=S+1/Z
    root=math.sqrt(V)
    g=(math.sqrt(2*math.pi*V)/(length*math.sqrt(1+Z*S))*
       (ndtr((r_hi-d)/root)-ndtr((r_lo-d)/root)))
    if u is None:
        return g
    u=np.asarray(u,dtype=float)
    y=u-b
    gaussian_trigger_average=(
        math.sqrt(2*math.pi/Z)/length*
        (ndtr((r_hi-y)*math.sqrt(Z))-ndtr((r_lo-y)*math.sqrt(Z)))
    )
    hbar=1-gaussian_trigger_average
    normal=np.exp(-.5*(y-d)**2/S)/math.sqrt(2*math.pi*S)
    return normal*hbar


def phase_only_event_kl(mean,delta,d,S,Z):
    """Deterministic codeword-event KL; codeword mass is common and cancels."""
    rows=codeword_intervals(mean,delta)
    result=0.
    for row in rows:
        length=row["phase_hi"]-row["phase_lo"]
        rlo,rhi=row["r_lo"],row["r_hi"]
        p0=index_kernel(0,S,0,0,rlo,rhi,Z)
        p1=index_kernel(0,S,d,0,rlo,rhi,Z)
        q0,q1=p0,p1
        result+=length/(2*delta)*(q1*math.log(q1/q0)+(1-q1)*math.log((1-q1)/(1-q0)))
    return result


def center_phase_only_event_kl(delta,d,S,Z,order=256):
    nodes,weights=np.polynomial.legendre.leggauss(order)
    r=delta*nodes
    G0=np.exp(-r*r/(2*(S+1/Z)))/math.sqrt(1+Z*S)
    G1=np.exp(-(d-r)**2/(2*(S+1/Z)))/math.sqrt(1+Z*S)
    G0=np.clip(G0,1e-300,1-1e-15);G1=np.clip(G1,1e-300,1-1e-15)
    terms=G1*np.log(G1/G0)+(1-G1)*np.log((1-G1)/(1-G0))
    return float(np.dot(weights/2,terms))
