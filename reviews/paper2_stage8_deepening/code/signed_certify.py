"""Stage 6 continuous low-support search on both halves of the amplitude domain."""
from copy import copy
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
import heapq

from vector_record import VectorRecord, I


class SignedRecord(VectorRecord):
    """Onsets sharing a first send have identical scores, responses and bounds."""
    def __init__(self, model, cap):
        super().__init__(model)
        self.send_times = []
        self.warm = [dict(d=[I.exact(0), I.exact(0)], mass=I.exact(0), b=I.exact(scale*cap))
                     for scale in map(D, ("-.2", "-.4", "-1", ".2", ".4", "1"))]

    def append(self, sent, u, r):
        super().append(sent, u, r)
        if sent:
            self.send_times.append(self.n-1)
        else:
            self.candidates.pop()  # a zero-response future-start class still exists
        # The parent accumulates six masses with divisor 3. Use equal weights 1/6.
        inactive = I.exact(1)/(self.n+1)
        self.ref = (self.ref+inactive)/2

    def view(self):
        view = copy(self)
        view.n = len(self.send_times)
        view.marks = [self.marks[t] for t in self.send_times]
        return view


def certify(view, direction, z, cap, eps, budget, witness_score):
    cutoff = (view.ref*eps).ln()
    out = dict(target=str(z), cutoff=cutoff.json(), nodes=0, certified=False)
    if cutoff.lo <= 0:
        return dict(out, reason="zero_or_future")
    if witness_score is None or witness_score.lo <= cutoff.hi:
        return dict(out, reason="no_verified_witness")
    jobs = []
    def queue(k, box):
        upper = view.tangent_upper(k, box)
        if upper >= cutoff.lo:
            heapq.heappush(jobs, (upper.copy_negate(), k, box.lo, box.hi))
    for k in range(view.n):
        q = view.support_coefficient(k, direction)
        # For c=abs(b), bad models satisfy c*(sign*basis projection) <= z.
        for sign, lower_q in ((1, q.lo), (-1, q.hi.copy_negate())):
            end = cap if lower_q <= 0 else min(cap, (I.exact(z)/lower_q).hi)
            left,right = (D(0),end) if sign>0 else (end.copy_negate(),D(0))
            cuts = sorted({left,right,*(v for v,_ in view.marks[k:] if left<v<right)})
            for l,h in zip(cuts,cuts[1:]):
                queue(k,I(l,h))
    while jobs:
        if out["nodes"] >= budget:
            return dict(out,reason="node_budget")
        _,k,l,h=heapq.heappop(jobs)
        out["nodes"]+=1
        if h-l <= D("1e-8"):
            return dict(out,reason="feasible_or_unresolved")
        with localcontext() as ctx:
            ctx.prec=50
            mid=(l+h)/2
        queue(k,I(l,mid))
        queue(k,I(mid,h))
    return dict(out,certified=True,reason="low_support_excluded")


def restrict(interval, q, z):
    """Outer interval after a measured projection in [q.lo,q.hi], b*q >= z."""
    lo,hi=interval
    pieces=[]
    if q.hi>0:
        pieces.append((max(lo,z/F(q.hi)),hi))
    if q.lo<0:
        pieces.append((lo,min(hi,z/F(q.lo))))
    valid=[p for p in pieces if p[0]<=p[1]]
    return (min(p[0] for p in valid),max(p[1] for p in valid)) if valid else None
