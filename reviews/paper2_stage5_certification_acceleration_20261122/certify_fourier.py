"""Global affinity cap from bounded characteristic features and Decimal boxes.

For |T|<=1, |E1 T-E2 T|² <= 8(1-Affinity). Each accepted parameter box
therefore supplies a lower Hellinger gap, without optimizing the affinity.
No random draws, ordinary optimizer output, or quadrature is used here.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,sys,time
from decimal import Decimal,localcontext
from pathlib import Path

HERE=Path(__file__).resolve().parent
PREV=HERE.parent/"paper2_stage4_certified_correction_20261122"
sys.path.insert(0,str(PREV))
from interval_arithmetic import Interval as I,D,PRECISION
from compute_separation_bounds import constants
from check_certificate import MODELS

FREQUENCIES=(D(1),D(2),D(3),D(4),D(5),D(6),D(8))


def trig_point(x,cosine=False):
    """Interval Taylor enclosure of sin/cos for the present |x|<=4 inputs."""
    if x.copy_abs()>4:
        raise ValueError("Taylor range contract exceeded")
    xx=I.exact(x);power=I.exact(1) if cosine else xx
    result=I.exact(0)
    start=0 if cosine else 1
    for j in range(20):
        exponent=start+2*j
        result=result+((-1 if j%2 else 1)*power/math.factorial(exponent))
        power=power*xx.square()
    # Taylor remainder at degree 38(cos) or 39(sin), all derivatives <=1.
    rem=I.exact(1)
    degree=38 if cosine else 39
    for _ in range(degree+1):rem=rem*I.exact(x.copy_abs())
    rem=rem/math.factorial(degree+1)
    return result+I(rem.hi.copy_negate(),rem.hi)


def trig(x,cosine=False):
    with localcontext() as c:
        c.prec=PRECISION
        mid=(x.lo+x.hi)/2
    radius=max((I.exact(mid)-I.exact(x.lo)).hi,(I.exact(x.hi)-I.exact(mid)).hi)
    y=trig_point(mid,cosine)+I(radius.copy_negate(),radius)
    return I(max(D(-1),y.lo),min(D(1),y.hi))


def complex_exp_phase(theta):
    return trig(theta,True),trig(theta,False)


def cmul(x,y):
    return x[0]*y[0]-x[1]*y[1],x[0]*y[1]+x[1]*y[0]


def cscale(s,z):
    return s*z[0],s*z[1]


def csub(x,y):
    return x[0]-y[0],x[1]-y[1]


def feature(S,z,a,omega):
    den=1+2*S;V=S+I.exact(".5")
    G=(-z.square()/(2*V)).exp()/den.sqrt()
    first=cscale((-S*omega*omega/2).exp(),complex_exp_phase(z*omega))
    second=cscale(G*(-S/den*omega*omega/2).exp(),
                  complex_exp_phase(z/den*omega))
    return cmul(complex_exp_phase(I.exact(a)*omega),csub(first,second))


def minabs(interval):
    if interval.lo<=0<=interval.hi:return D(0)
    return min(interval.lo.copy_abs(),interval.hi.copy_abs())


def gap_lower(box,amplitude_gap,omega):
    S,z1,z2=box
    diff=csub(feature(S,z1,amplitude_gap,omega),feature(S,z2,D(0),omega))
    bound=(I.exact(minabs(diff[0])).square()+I.exact(minabs(diff[1])).square())/8
    return bound.lo


def likely_frequency(box,gap):
    # Ranking only; all acceptance decisions use the interval formula.
    S,z1,z2=[float((x.lo+x.hi)/2) for x in box]
    import cmath
    def F(z,a,w):
        den=1+2*S;V=S+.5
        G=math.exp(-z*z/(2*V))/math.sqrt(den)
        return cmath.exp(1j*w*a)*(cmath.exp(-S*w*w/2+1j*w*z)-
                                  G*cmath.exp(-S/den*w*w/2+1j*w*z/den))
    return sorted(FREQUENCIES,key=lambda w:abs(F(z1,float(gap),float(w))-F(z2,0,float(w))),reverse=True)


def run(model,gap,target,max_nodes):
    c=constants(model)
    delta=I.exact(model["delta"])
    zlo=(-c["Dprior"]-delta).lo
    zhi=delta.hi
    initial=(I(c["smin"].lo,c["smax"].hi),I(zlo,zhi),I(zlo,zhi))
    widths=[x.hi-x.lo for x in initial]
    stack=[(initial,"")];leaves=[];nodes=0;started=time.perf_counter()
    while stack and nodes<max_nodes:
        box,path=stack.pop();nodes+=1
        accepted=False
        # Try the two strongest features at the midpoint first; failure to
        # certify never means exclusion, it just causes subdivision.
        for omega in likely_frequency(box,gap)[:2]:
            lower=gap_lower(box,gap,omega)
            if lower>=target:
                leaves.append((box,path,omega,lower));accepted=True;break
        if accepted:continue
        axis=max(range(3),key=lambda i:(box[i].hi-box[i].lo)/widths[i])
        with localcontext() as context:
            context.prec=PRECISION
            mid=(box[axis].hi+box[axis].lo)/2
        left=list(box);right=list(box)
        left[axis]=I(box[axis].lo,mid);right[axis]=I(mid,box[axis].hi)
        stack.extend(((tuple(right),path+"1"),(tuple(left),path+"0")))
        if nodes%1000==0:
            print(model["id"],str(gap),"nodes",nodes,"pending",len(stack),
                  "seconds",round(time.perf_counter()-started,1),flush=True)
    result={"model":model["id"],"amplitude_gap":str(gap),"target_gap":str(target),
            "status":"CERTIFIED" if not stack else "UNRESOLVED",
            "nodes":nodes,"leaves":len(leaves),"pending":len(stack),
            "seconds":time.perf_counter()-started,
            "root_box":[x.json() for x in initial],
            "random_samples_generated":False,"method":"outward Decimal characteristic-feature enclosure",
            "source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    folder=HERE/"fourier_certificates";folder.mkdir(exist_ok=True)
    stem=f"{model['id']}_gap{gap}_target{target}"
    with (folder/(stem+".csv")).open("w",encoding="utf8",newline="") as f:
        writer=csv.writer(f,lineterminator="\n")
        writer.writerow(["path","S_lo","S_hi","z1_lo","z1_hi","z2_lo","z2_hi","omega","gap_lower"])
        for box,path,w,lower in leaves:
            writer.writerow([path]+[str(x) for item in box for x in (item.lo,item.hi)]+[str(w),str(lower)])
    result["leaves_sha256"]=hashlib.sha256((folder/(stem+".csv")).read_bytes()).hexdigest()
    (folder/(stem+".json")).write_text(json.dumps(result,indent=2)+"\n",encoding="utf8",newline="\n")
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--model",choices=("S1","U1"),required=True)
    parser.add_argument("--gap",default=".15")
    parser.add_argument("--target",default=".0001")
    parser.add_argument("--max-nodes",type=int,default=100000)
    args=parser.parse_args()
    run(next(m for m in MODELS if m["id"]==args.model),D(args.gap),D(args.target),args.max_nodes)
