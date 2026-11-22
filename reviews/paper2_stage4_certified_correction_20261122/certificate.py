"""Continuous-amplitude pollution certificate with outward likelihood bounds.

Finite actual onsets are enumerated. All future onsets and permanent health
are one exact healthy likelihood class. Unresolved intervals are never removed.
This is a deterministic theory prototype, not a performance-tested online solver.
"""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal,localcontext
import heapq
from interval_arithmetic import Interval as I, D, PRECISION, log_trigger, NINF


@dataclass
class Step:
    sent: bool
    u: str | None
    r: str


class ExactRecord:
    def __init__(self,model,steps):
        for key in ("A","Q","R","Z","P0","delta"):
            if isinstance(model[key],float) or not D(model[key]).is_finite() or D(model[key])<=0:
                raise ValueError("Model constants must be finite positive decimal strings")
        self.model=model
        self.steps=steps
        self.rows=[]
        A,Q,R,Z,P=(I.exact(model[k]) for k in ("A","Q","R","Z","P0"))
        for step in steps:
            u=I.exact(step.u) if step.sent else None
            if not step.sent and step.u is not None:
                raise ValueError("Silent payload is unavailable")
            r=I.exact(step.r)
            if not (-D(model["delta"])<=r.lo<=D(model["delta"])):
                raise ValueError("Center residual outside full phase period")
            S=P+R;V=S+1/Z
            K=P/(P+R+(0 if step.sent else 1/Z))
            denominator=log_trigger(u-r,model["Z"]) if step.sent else None
            if denominator is not None and denominator.lo==NINF:
                raise ValueError("Null send density zero or unresolved; do not certify")
            self.rows.append((step,u,r,S,V,K,denominator))
            P=A*A*P*(1-K)+Q

    def coefficient(self,k):
        H=I.exact(0);A=I.exact(self.model["A"])
        for t,(step,u,r,S,V,K,denominator) in enumerate(self.rows):
            H=(1-K)*A*H+(K if step.sent and t>=k else 0)
        return H

    def log_likelihood(self,k,b):
        """Log(p_k,b/p_healthy), all parameters/observations decimal exact."""
        b=I.coerce(b);H=I.exact(0);total=I.exact(0);A=I.exact(self.model["A"])
        for t,(step,u,r,S,V,K,denominator) in enumerate(self.rows):
            if t<k:
                continue
            d=-A*H*b
            if step.sent:
                shift=b+d
                term=(u*shift-shift.square()/2)/S+log_trigger(u-b-r,self.model["Z"])-denominator
            else:
                term=(r*d-d.square()/2)/V
            total=total+term
            H=(1-K)*A*H+(K if step.sent else 0)
        return total

    def reference(self,strengths=("0.05","0.10","0.25"),health_weight="0.5"):
        """Exact physical candidate mixture, including infinite unstarted tail."""
        if not strengths or not D(health_weight).is_finite() or not 0<=D(health_weight)<=1:
            raise ValueError("Invalid reference weights or empty candidate dictionary")
        if any(not D(b).is_finite() or D(b)<0 for b in strengths):
            raise ValueError("Invalid reference amplitudes")
        rho=I.exact(health_weight)
        n=len(self.rows)
        # k=0,...,n-1 observed; sum_{k>=n}1/[(k+1)(k+2)]=1/(n+1)
        mixture=I.exact(1)/(n+1)
        for k in range(n):
            component=I.exact(0)
            for b in strengths:
                component=component+self.log_likelihood(k,I.exact(b)).exp()/len(strengths)
            mixture=mixture+component/((k+1)*(k+2))
        return rho+(1-rho)*mixture

    def witness(self,threshold,bmax):
        for k in range(len(self.rows)):
            for b in (D(bmax)/4,D(bmax)/2,D(bmax)):
                if self.log_likelihood(k,I.exact(b)).lo>threshold.hi:
                    return {"onset":k,"amplitude":str(b)}
        return None

    def universal_pollution_cap(self,bmax):
        """Lower enclosure of the proved model-wide Bmax (for output clipping)."""
        A,Q,R,P0=(I.exact(self.model[k]) for k in ("A","Q","R","P0"))
        # All-send Riccati root, expressed without subtractive cancellation.
        linear=R-Q-A*A*R
        root=(-linear+(linear.square()+4*Q*R).sqrt())/2
        if not P0.lo>=root.hi:
            raise ValueError("This invariant needs initial covariance >= root")
        kmin=root/(root+R)
        r0=R+1/I.exact(self.model["Z"])
        coarseP=A*A*r0+Q
        Pmax=I(max(P0.lo,coarseP.lo),max(P0.hi,coarseP.hi))
        kmax=Pmax/(Pmax+R)
        gain=kmax if A.hi<=1 else kmin
        denominator=1-A*(1-gain)
        if denominator.lo<=0 or (A*r0/(root+r0)).hi>=1:
            raise ValueError("Unproved pollution invariant")
        return (I.exact(bmax)*gain/denominator).lo

    def certify(self,z,epsilon="0.001",bmax="0.25",max_nodes=4096,
                min_width="0.00000001"):
        """Certify θ>z for every retained parameter, else return lower bound zero.

        A lower enclosed cutoff is used to reject a likelihood interval.
        Nonempty-set witness is independent of the exclusion calculation.
        This function never interprets a coarse grid as an upper bound.
        """
        z=D(z)
        if (not z.is_finite() or not D(epsilon).is_finite() or not 0<D(epsilon)<1
            or not D(bmax).is_finite() or D(bmax)<=0
            or not D(min_width).is_finite() or D(min_width)<=0
            or not isinstance(max_nodes,int) or max_nodes<0):
            raise ValueError("Invalid confidence, amplitude, or computation budget")
        if z<0 or z>D(bmax)*2:
            raise ValueError("Invalid candidate pollution level")
        E=self.reference()
        threshold=(I.exact(epsilon)*E).ln()
        out={"requested_z":str(z),"epsilon":epsilon,"log_cutoff":threshold.json(),
             "reference_e":E.json(),"certified":False,"lower_bound":"0",
             "reason":"","nodes":0,"future_onsets_checked":True}
        cap=self.universal_pollution_cap(bmax)
        out["certified_output_cap_lower"]=str(cap)
        if z>cap:
            out["reason"]="REQUEST_ABOVE_PROVED_OUTPUT_CAP"
            return out
        # Health and all unstarted candidates have log Lambda=0, theta=0.
        if threshold.lo<=0:
            out["reason"]="HEALTH_OR_FUTURE_START_RETAINED"
            return out
        witness=self.witness(threshold,bmax)
        out["nonempty_witness"]=witness
        if witness is None:
            out["reason"]="NO_CERTIFIED_NONEMPTY_WITNESS"
            return out
        heap=[];serial=0
        for k in range(len(self.rows)):
            H=self.coefficient(k)
            upper=D(bmax) if H.lo<=0 else min(D(bmax),(I.exact(z)/I.exact(H.lo)).hi)
            B=I(D(0),max(D(0),upper))
            ll=self.log_likelihood(k,B)
            if ll.hi>=threshold.lo:
                heapq.heappush(heap,(-ll.hi,serial,k,B));serial+=1
        rejected=0
        while heap:
            if out["nodes"]>=max_nodes:
                out["reason"]="UNRESOLVED_NODE_LIMIT"
                out["unresolved_intervals"]=len(heap)
                return out
            negup,_,k,B=heapq.heappop(heap)
            out["nodes"]+=1
            if B.hi-B.lo<=D(min_width):
                out["reason"]="UNRESOLVED_WIDTH_OR_RETAINED_CANDIDATE"
                out["unresolved_interval"]={"k":k,"b":B.json(),"log_upper":str(-negup)}
                return out
            with localcontext() as c:
                c.prec=PRECISION
                middle=(B.lo+B.hi)/2
            for sub in (I(B.lo,middle),I(middle,B.hi)):
                ll=self.log_likelihood(k,sub)
                if ll.hi<threshold.lo:
                    rejected+=1
                else:
                    heapq.heappush(heap,(-ll.hi,serial,k,sub));serial+=1
        out.update({"certified":True,"lower_bound":str(z),"reason":"ALL_LOW_POLLUTION_CANDIDATES_EXCLUDED",
                    "rejected_intervals":rejected})
        return out
