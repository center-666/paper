"""Two-state exact-onset likelihood cache with outward Decimal coefficients.

Physical covariance/gains are exact rational functions of decimal model input.
Continuous observation inputs are interpreted as exact decimal reals.
"""
from __future__ import annotations
from pathlib import Path
import sys
from fractions import Fraction as F
from decimal import Decimal,localcontext
import heapq
HERE=Path(__file__).resolve().parent
STAGE4=HERE.parent/"paper2_stage4_certified_correction_20261122"
STAGE5=HERE.parent/"paper2_stage5_certification_acceleration_20261122"
sys.path.insert(0,str(STAGE4));sys.path.insert(0,str(STAGE5))
from interval_arithmetic import Interval as I,D,PRECISION,log_trigger
from strong_concavity import positive_quadratic_max,exact_subtract
from exact_linear import matrix,identity,add,sub,scale,matmul,transpose,update
from projection import weighted_projection,inner


def interval_fraction(x):
    x=F(x)
    return I.exact(x.numerator)/I.exact(x.denominator)


def dot(a,b):
    return sum((x*y for x,y in zip(a,b)),I.exact(0))


class VectorRecord:
    def __init__(self,model):
        self.model=model;self.n=0
        self.A=matrix(model["A"]);self.C=matrix(model["C"])
        self.Q=matrix(model["Q"]);self.P=matrix(model["P0_prior"])
        self.R=F(model["R"]);self.Z=F(model["Z"]);self.W=matrix(model["W"])
        self.candidates=[];self.marks=[]
        self.warm=[{"d":[I.exact(0),I.exact(0)],"mass":I.exact(0),"b":I.exact(b)}
                   for b in (".05",".10",".25")]
        self.ref=I.exact(1)
        self.stats={"candidate_updates":0,"suffix_trigger_evaluations":0,
                    "likelihood_evaluations":0,"segments_tested":0}

    def append(self,sent,u,r):
        if not sent and u is not None:raise ValueError("Silent payload unavailable")
        ri=I.exact(r);ui=I.exact(u) if sent else None
        if not (ri.lo.is_finite() and ri.lo.copy_abs()<=D(self.model["quantization_half_width"])):
            raise ValueError("Invalid measurement-center offset")
        if sent and not ui.lo.is_finite():raise ValueError("Invalid payload")
        Ppost,K,T=update(self.P,self.C,self.R+(0 if sent else 1/self.Z))
        Sm=matmul(matmul(self.C,self.P),transpose(self.C))[0][0]+self.R
        S=interval_fraction(Sm);V=S+I.exact(self.model["Z"]).reciprocal()
        Ti=[[interval_fraction(x) for x in row] for row in T]
        Ai=[[interval_fraction(x) for x in row] for row in self.A]
        Ki=[interval_fraction(row[0]) for row in K]
        Ci=[interval_fraction(x) for x in self.C[0]]
        denom=log_trigger(ui-ri,self.model["Z"]) if sent else None
        if sent and not denom.lo.is_finite():raise ArithmeticError("Null density unresolved")
        mark=(exact_subtract(u,r),denom) if sent else None
        self.marks.append(mark)
        self.candidates.append({"H":[I.exact(0),I.exact(0)],"a":I.exact(0),"B":I.exact(0),"sends":0})
        for candidate in self.candidates:
            prior=[dot(row,candidate["H"]) for row in Ai]
            eta=dot(Ci,prior)
            if sent:
                coeff=1-eta
                candidate["a"]=candidate["a"]+coeff*ui/S
                candidate["B"]=candidate["B"]+coeff.square()/S
                candidate["sends"]+=1
            else:
                candidate["a"]=candidate["a"]-ri*eta/V
                candidate["B"]=candidate["B"]+eta.square()/V
            candidate["H"]=[dot(row,prior)+(Ki[j] if sent else 0) for j,row in enumerate(Ti)]
            self.stats["candidate_updates"]+=1
        # A normalized warm joint e-process supplies the reference numerator.
        for reference in self.warm:
            d=dot(Ci,reference["d"]);b=reference["b"]
            if sent:
                shift=b+d
                logfactor=(ui*shift-shift.square()/2)/S+log_trigger(ui-b-ri,self.model["Z"])-denom
            else:
                logfactor=(ri*d-d.square()/2)/V
            weight=I.exact(1)/((self.n+1)*(self.n+2))
            reference["mass"]=(reference["mass"]+weight)*logfactor.exp()
            post=[dot(row,reference["d"])-(Ki[j]*b if sent else 0) for j,row in enumerate(Ti)]
            reference["d"]=[dot(row,post) for row in Ai]
        self.ref=sum((c["mass"]/3 for c in self.warm),I.exact(1)/(self.n+2))
        self.P=add(matmul(matmul(self.A,Ppost),transpose(self.A)),self.Q)
        self.n+=1

    def all_likelihoods(self,b):
        """One shared selection suffix pass scores every onset at this b/box."""
        b=I.coerce(b);suffix=I.exact(0);values=[None]*self.n
        for k in range(self.n-1,-1,-1):
            if self.marks[k] is not None:
                v,den=self.marks[k]
                suffix=suffix+log_trigger(I.exact(v)-b,self.model["Z"])-den
                self.stats["suffix_trigger_evaluations"]+=1
            candidate=self.candidates[k]
            values[k]=candidate["a"]*b-candidate["B"]*b.square()/2+suffix
        return values

    def likelihood(self,k,b):
        b=I.coerce(b);candidate=self.candidates[k]
        result=candidate["a"]*b-candidate["B"]*b.square()/2
        for mark in self.marks[k:]:
            if mark is None:continue
            v,den=mark;result=result+log_trigger(I.exact(v)-b,self.model["Z"])-den
        self.stats["likelihood_evaluations"]+=1
        return result

    def support_coefficient(self,k,d):
        wd=[sum((self.W[i][j]*F(d[i]) for i in range(2)),F(0)) for j in range(2)]
        return dot([interval_fraction(x) for x in wd],self.candidates[k]["H"])

    def tangent_upper(self,k,box):
        natural=self.likelihood(k,box).hi;candidate=self.candidates[k];B=candidate["B"].lo
        if B<=0 or box.lo==box.hi:return natural
        with localcontext() as c:
            c.prec=PRECISION;mid=(box.lo+box.hi)/2
        if mid==box.lo or mid==box.hi:return natural
        if any(mark is not None and box.lo<mark[0]<box.hi for mark in self.marks[k:]):
            raise ValueError("Split at all moving zeros before using a tangent")
        try:
            derivative=candidate["a"]-candidate["B"]*I.exact(mid)
            for mark in self.marks[k:]:
                if mark is None:continue
                x=I.exact(mark[0])-I.exact(mid)
                den=(I.exact(self.model["Z"])*x.square()/2).exp()-1
                if den.lo<=0:return natural
                derivative=derivative-I.exact(self.model["Z"])*x/den
            value=self.likelihood(k,I.exact(mid))
            left=(I.exact(mid)-I.exact(box.lo)).hi;right=(I.exact(box.hi)-I.exact(mid)).hi
            bump=max(positive_quadratic_max(derivative.hi,B,right),
                     positive_quadratic_max(derivative.lo.copy_negate(),B,left))
            return min(natural,(I.exact(value.hi)+I.exact(bump)).hi)
        except ArithmeticError:return natural

    def certify_direction(self,d,z,epsilon=".001",bmax=".25",max_nodes=256):
        d=tuple(F(x) for x in d);z=D(z)
        norm=inner(d,d,self.W)
        if norm<=0 or z<0 or not z.is_finite() or not 0<D(epsilon)<1 or D(bmax)<=0:
            raise ValueError("Invalid direction or confidence parameters")
        threshold=(I.exact(epsilon)*self.ref).ln()
        out={"certified":False,"correction":["0","0"],"guaranteed_gain":"0",
             "nodes":0,"reason":"","target_support":str(z),"reference_log_cutoff":threshold.json()}
        if threshold.lo<=0:
            out["reason"]="HEALTH_OR_FUTURE_START_RETAINED";return out
        # Direction may depend on this data; the full common CS supplies validity.
        witness=None
        for b in (".05",".10",bmax):
            for k,value in enumerate(self.all_likelihoods(I.exact(b))):
                if value.lo>threshold.hi:witness={"onset":k,"amplitude":b};break
            if witness is not None:break
        if witness is None:out["reason"]="NONEMPTY_WITNESS_UNRESOLVED";return out
        out["nonempty_witness"]=witness
        jobs=[];serial=0
        for k,candidate in enumerate(self.candidates):
            a=self.support_coefficient(k,d)
            upper=D(bmax) if a.lo<=0 else min(D(bmax),(I.exact(z)/I.exact(a.lo)).hi)
            cuts=sorted(set([D(0),upper]+[m[0] for m in self.marks[k:] if m is not None and 0<m[0]<upper]))
            segments=[I(x,y) for x,y in zip(cuts,cuts[1:])] if len(cuts)>1 else [I.exact(0)]
            for interval in segments:
                bound=self.tangent_upper(k,interval);self.stats["segments_tested"]+=1
                if bound>=threshold.lo:heapq.heappush(jobs,(-bound,serial,k,interval));serial+=1
        while jobs:
            if out["nodes"]>=max_nodes:
                out["reason"]="UNRESOLVED_NODE_LIMIT";return out
            _,_,k,interval=heapq.heappop(jobs);out["nodes"]+=1
            if interval.hi-interval.lo<=D(".00000001"):
                out["reason"]="UNRESOLVED_OR_FEASIBLE";return out
            with localcontext() as c:
                c.prec=PRECISION;mid=(interval.lo+interval.hi)/2
            for child in (I(interval.lo,mid),I(mid,interval.hi)):
                upper=self.tangent_upper(k,child)
                if upper>=threshold.lo:heapq.heappush(jobs,(-upper,serial,k,child));serial+=1
        alpha=F(z)/norm;correction=tuple(alpha*x for x in d)
        out.update(certified=True,correction=[str(x) for x in correction],
                   guaranteed_gain=str(F(z)**2/norm),reason="ALL_LOW_SUPPORT_MODELS_EXCLUDED")
        return out
