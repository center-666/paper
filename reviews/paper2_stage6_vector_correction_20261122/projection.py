"""Exact W-projection of the origin onto a finite 2D pollution convex hull.

This solves geometry only. Coverage of input outer sets is the caller's duty.
"""
from fractions import Fraction as F
from exact_linear import matrix,spd2


def cross(o,a,b):
    return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])


def hull(points):
    points=sorted(set(tuple(F(x) for x in p) for p in points))
    if any(len(p)!=2 for p in points):raise ValueError("Two-state geometry only")
    if len(points)<=1:return points
    lower=[]
    for p in points:
        while len(lower)>=2 and cross(lower[-2],lower[-1],p)<=0:lower.pop()
        lower.append(p)
    upper=[]
    for p in reversed(points):
        while len(upper)>=2 and cross(upper[-2],upper[-1],p)<=0:upper.pop()
        upper.append(p)
    return lower[:-1]+upper[:-1]


def inner(a,b,W):
    return sum((a[i]*W[i][j]*b[j] for i in range(2) for j in range(2)),F(0))


def weighted_projection(points,W):
    W=matrix(W)
    if not spd2(W):raise ValueError("W must be symmetric positive definite")
    polygon=hull(points);zero=(F(0),F(0))
    if not polygon:
        return {"point":zero,"guaranteed_gain":F(0),"status":"EMPTY_INPUT_ZERO_ACTION","vertices":[]}
    if len(polygon)>=3 and all(cross(polygon[i],polygon[(i+1)%len(polygon)],zero)>=0
                               for i in range(len(polygon))):
        answer=zero
    elif len(polygon)==1:
        answer=polygon[0]
    else:
        candidates=[]
        for i,p in enumerate(polygon):
            q=polygon[(i+1)%len(polygon)]
            d=(q[0]-p[0],q[1]-p[1])
            denom=inner(d,d,W)
            t=max(F(0),min(F(1),-inner(p,d,W)/denom)) if denom else F(0)
            candidates.append((p[0]+t*d[0],p[1]+t*d[1]))
        answer=min(candidates,key=lambda p:inner(p,p,W))
    gain=inner(answer,answer,W)
    # Verify the separating/supporting hyperplane exactly at every hull vertex.
    assert all(inner(theta,answer,W)>=gain for theta in polygon)
    assert min(inner(theta,answer,W) for theta in polygon)==gain
    return {"point":answer,"guaranteed_gain":gain,"vertices":polygon,
            "status":"ZERO_IN_HULL" if gain==0 else "POSITIVE_GUARANTEED_IMPROVEMENT"}


def directional_certificate(points,d,W):
    W=matrix(W);d=tuple(F(x) for x in d)
    if not spd2(W):raise ValueError("W must be positive definite")
    denom=inner(d,d,W)
    if denom==0:raise ValueError("Direction must be nonzero")
    points=[tuple(F(x) for x in p) for p in points]
    if not points:return {"point":(F(0),F(0)),"gain":F(0),"support":None}
    support=min(inner(d,p,W) for p in points)
    if support<=0:return {"point":(F(0),F(0)),"gain":F(0),"support":support}
    point=tuple(support/denom*x for x in d)
    gain=support**2/denom
    assert all(2*inner(theta,point,W)-inner(point,point,W)>=gain for theta in points)
    return {"point":point,"gain":gain,"support":support}


def interval_image(coefficients,amplitude_intervals,include_unstarted=True):
    """Exact endpoints for a union of outer amplitude intervals times H vectors."""
    if len(coefficients)!=len(amplitude_intervals):raise ValueError("Mismatched inputs")
    points=[]
    for H,bounds in zip(coefficients,amplitude_intervals):
        H=tuple(F(x) for x in H);lo,hi=(F(x) for x in bounds)
        if lo<0 or hi<lo:raise ValueError("Invalid positive-amplitude interval")
        points.extend(tuple(b*x for x in H) for b in (lo,hi))
    if include_unstarted:points.append((F(0),F(0)))
    return points
