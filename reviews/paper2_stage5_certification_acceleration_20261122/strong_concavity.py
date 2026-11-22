"""Cached exact-onset likelihood and certified strong-concavity upper bounds."""
from __future__ import annotations
from decimal import Decimal,localcontext
from pathlib import Path
import heapq,sys
PREV=Path(__file__).resolve().parent.parent/"paper2_stage4_certified_correction_20261122"
sys.path.insert(0,str(PREV))
from certificate import ExactRecord,Step
from interval_arithmetic import Interval as I,D,PRECISION,log_trigger,NINF


def exact_subtract(x,y):
    x,y=D(x),D(y)
    with localcontext() as context:
        context.prec=max(x.adjusted(),y.adjusted())-min(x.as_tuple().exponent,y.as_tuple().exponent)+3
        return x-y


def positive_quadratic_max(p,curvature,width):
    """Upper endpoint of max_{0<=x<=width} p*x-curvature*x²/2."""
    if p<=0 or width<=0:return D(0)
    optimum=I.exact(p)/I.exact(curvature)
    optimum=I(min(width,max(D(0),optimum.lo)),min(width,max(D(0),optimum.hi)))
    return (I.exact(p)*optimum-I.exact(curvature)*optimum.square()/2).hi


class CachedRecord(ExactRecord):
    def __init__(self,model,steps):
        super().__init__(model,steps)
        self.cache={};self.stats={"likelihood_calls":0,"derivative_calls":0,"tangent_bounds":0,
                                "cache_state_steps":0,"trigger_terms":0}
        A=I.exact(model["A"])
        for k in range(len(self.rows)):
            H=I.exact(0);linear=I.exact(0);curvature=I.exact(0);marks=[]
            for t in range(k,len(self.rows)):
                step,u,r,S,V,K,denominator=self.rows[t]
                hprior=A*H
                if step.sent:
                    coefficient=1-hprior
                    linear=linear+coefficient*u/S
                    curvature=curvature+coefficient.square()/S
                    marks.append((exact_subtract(step.u,step.r),denominator))
                else:
                    linear=linear-r*hprior/V
                    curvature=curvature+hprior.square()/V
                H=(1-K)*hprior+(K if step.sent else 0)
                self.stats["cache_state_steps"]+=1
            self.cache[k]=(linear,curvature,H,tuple(marks))

    def coefficient(self,k):
        return self.cache[k][2] if k in self.cache else I.exact(0)

    def log_likelihood(self,k,b):
        self.stats["likelihood_calls"]+=1
        b=I.coerce(b)
        if k not in self.cache:return I.exact(0)
        a,B,H,marks=self.cache[k]
        answer=a*b-B*b.square()/2
        for v,den in marks:
            answer=answer+log_trigger(I.exact(v)-b,self.model["Z"])-den
            self.stats["trigger_terms"]+=1
        return answer

    def derivative(self,k,b):
        self.stats["derivative_calls"]+=1
        if k not in self.cache:return I.exact(0)
        a,B,H,marks=self.cache[k]
        b=I.coerce(b);ans=a-B*b;Z=I.exact(self.model["Z"])
        for v,_ in marks:
            x=I.exact(v)-b
            if x.lo<=0<=x.hi:raise ArithmeticError("Derivative interval meets a moving zero")
            den=(Z*x.square()/2).exp()-1
            if den.lo<=0:raise ArithmeticError("Derivative denominator unresolved")
            ans=ans-Z*x/den
        return ans

    def segments(self,k,box):
        marks=self.cache[k][3] if k in self.cache else ()
        cuts=sorted(set([box.lo,box.hi]+[v for v,_ in marks if box.lo<v<box.hi]))
        if len(cuts)==1:return [box]
        return [I(a,b) for a,b in zip(cuts,cuts[1:])]

    def segment_upper(self,k,box):
        natural=self.log_likelihood(k,box)
        if box.lo==box.hi or k not in self.cache or not self.cache[k][3]:
            return natural.hi
        if any(box.lo<v<box.hi for v,_ in self.cache[k][3]):
            raise ValueError("Tangent upper bound must stay inside one smooth segment")
        B=self.cache[k][1].lo
        if B<=0:return natural.hi
        with localcontext() as ctx:
            ctx.prec=PRECISION
            mid=(box.lo+box.hi)/2
        if mid in (box.lo,box.hi):return natural.hi
        try:
            slope=self.derivative(k,I.exact(mid))
            value=self.log_likelihood(k,I.exact(mid))
            right=(I.exact(box.hi)-I.exact(mid)).hi
            left=(I.exact(mid)-I.exact(box.lo)).hi
            bump=max(positive_quadratic_max(slope.hi,B,right),
                     positive_quadratic_max(slope.lo.copy_negate(),B,left))
            upper=(I.exact(value.hi)+I.exact(bump)).hi
            self.stats["tangent_bounds"]+=1
            return min(natural.hi,upper)
        except ArithmeticError:
            return natural.hi

    def certify(self,z,epsilon="0.001",bmax=".25",max_nodes=4096,min_width=".00000001"):
        z=D(z)
        if not (z.is_finite() and z>=0 and D(epsilon).is_finite() and 0<D(epsilon)<1
                and D(bmax).is_finite() and D(bmax)>0 and D(min_width)>0
                and D(min_width).is_finite() and isinstance(max_nodes,int) and max_nodes>=0):
            raise ValueError("Invalid certificate parameters")
        ref=self.reference();cutoff=(I.exact(epsilon)*ref).ln()
        out={"requested_z":str(z),"certified":False,"lower_bound":"0","reason":"",
             "log_cutoff":cutoff.json(),"nodes":0,"segments":0,
             "future_onsets_retained_or_excluded_exactly":True}
        if z>self.universal_pollution_cap(bmax):
            out["reason"]="REQUEST_ABOVE_PROVED_OUTPUT_CAP";return out
        if cutoff.lo<=0:
            out["reason"]="HEALTH_OR_FUTURE_START_RETAINED";return out
        witness=self.witness(cutoff,bmax);out["nonempty_witness"]=witness
        if witness is None:
            out["reason"]="NO_CERTIFIED_NONEMPTY_WITNESS";return out
        queue=[];serial=0
        for k in range(len(self.rows)):
            H=self.coefficient(k)
            upper=D(bmax) if H.lo<=0 else min(D(bmax),(I.exact(z)/I.exact(H.lo)).hi)
            for segment in self.segments(k,I(D(0),upper)):
                out["segments"]+=1
                bound=self.segment_upper(k,segment)
                if bound>=cutoff.lo:
                    heapq.heappush(queue,(-bound,serial,k,segment));serial+=1
        while queue:
            if out["nodes"]>=max_nodes:
                out["reason"]="UNRESOLVED_NODE_LIMIT";out["remaining"]=len(queue);return out
            _,_,k,segment=heapq.heappop(queue)
            out["nodes"]+=1
            if segment.hi-segment.lo<=D(min_width):
                out["reason"]="UNRESOLVED_WIDTH_OR_RETAINED_CANDIDATE";return out
            with localcontext() as context:
                context.prec=PRECISION
                mid=(segment.lo+segment.hi)/2
            for child in (I(segment.lo,mid),I(mid,segment.hi)):
                upper=self.segment_upper(k,child)
                if upper>=cutoff.lo:
                    heapq.heappush(queue,(-upper,serial,k,child));serial+=1
        out.update(certified=True,lower_bound=str(z),reason="ALL_LOW_POLLUTION_CANDIDATES_EXCLUDED")
        return out
