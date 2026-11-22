"""Independent deterministic checks: affinity, bounded feature and clock."""
from pathlib import Path
from decimal import Decimal,localcontext
from itertools import product
import json,math
import numpy as np
from scipy.integrate import quad
from certify_fourier import trig_point

HERE=Path(__file__).resolve().parent


def normal(u,mean,S):
    return np.exp(-(u-mean)**2/(2*S))/np.sqrt(2*np.pi*S)


def h(x):
    return -np.expm1(-x*x)


def silent(S,d,r):
    return np.exp(-(d-r)**2/(2*(S+.5)))/np.sqrt(1+2*S)


def main():
    checks=[]
    def check(name,ok,detail=None):
        checks.append({"name":name,"pass":bool(ok),"detail":detail})
        if not ok:raise AssertionError(name)
    for S,r,d1,d2,a1,a2 in ((.3,0.,-.1,-.05,.25,.1),(1.,.02,-.27,0.,.25,0.),
                              (.5,-.01,0.,-.1,.1,.25),(.7,.01,-.2,-.2,.25,.25)):
        p1=silent(S,d1,r);p2=silent(S,d2,r)
        def f(u,a,d):return normal(u,a+d,S)*h(u-a-r)
        cuts=sorted([-12.,r+a1,r+a2,12.])
        # Explicit split handles the absolute-value kinks in square roots.
        direct=math.sqrt(p1*p2)+sum(quad(lambda u:math.sqrt(f(u,a1,d1)*f(u,a2,d2)),
            lo,hi,epsabs=1e-12,epsrel=1e-12)[0] for lo,hi in zip(cuts,cuts[1:]))
        m1=a1+d1;m2=a2+d2;mu=(m1+m2)/2
        reduced=math.sqrt(p1*p2)+math.exp(-(m1-m2)**2/(8*S))*sum(
            quad(lambda u:normal(u,mu,S)*math.sqrt(h(u-a1-r)*h(u-a2-r)),
                 lo,hi,epsabs=1e-12,epsrel=1e-12)[0] for lo,hi in zip(cuts,cuts[1:]))
        check("affinity_completed_square",abs(direct-reduced)<2e-13,(direct,reduced))
        for w in (1.,2.,4.,8.):
            features=[]
            for a,d in ((a1,d1),(a2,d2)):
                numeric=complex(quad(lambda u:np.cos(w*(u-r))*f(u,a,d),-12,12,epsabs=1e-12)[0],
                                quad(lambda u:np.sin(w*(u-r))*f(u,a,d),-12,12,epsabs=1e-12)[0])
                z=d-r;den=1+2*S
                analytic=np.exp(1j*w*a)*(np.exp(-S*w*w/2+1j*w*z)-
                     silent(S,z,0)*np.exp(-S/den*w*w/2+1j*w*z/den))
                check("feature_formula_matches_quadrature",abs(numeric-analytic)<2e-12)
                features.append(analytic)
            check("bounded_feature_gap_below_exact_gap",
                  abs(features[0]-features[1])**2/8<=1-direct+1e-12)
    # High-precision independent trig series, compared to interval endpoints.
    with localcontext() as ctx:
        ctx.prec=100
        for x in ("-3.9","-2.51","-.001","0",".27","1.68","3.99"):
            a=Decimal(x)
            for cos in (False,True):
                term=Decimal(1) if cos else a;total=term
                for j in range(1,100):
                    denom=(2*j-1)*(2*j) if cos else (2*j)*(2*j+1)
                    term=term*(-a*a)/denom;total+=term
                interval=trig_point(a,cos)
                check("trig_taylor_contains_100digit",interval.lo<=total<=interval.hi)
    # Exhaust all paths in a predictable Bernoulli fixture: no iid assumption.
    sums=np.zeros(8)
    for bits in product((0,1),repeat=8):
        prob=1.;ratio=1.;clock=0.;history=0
        for i,bit in enumerate(bits):
            p=.3+.05*(history%3)
            q=.55-.04*(history%2)
            aff=math.sqrt(p*q)+math.sqrt((1-p)*(1-q))
            inc=(q/p) if bit else ((1-q)/(1-p))
            prob*=p if bit else 1-p
            ratio*=inc;clock-=math.log(aff)
            if i==7:
                # At final time every complete path contributes once.
                sums[i]+=prob*math.sqrt(ratio)*math.exp(clock)
            history+=bit
    check("information_clock_mean_one_full_tree",abs(sums[-1]-1)<2e-14,sums[-1])
    result={"status":"PASS","check_count":len(checks),"checks":checks,
            "random_samples_generated":False,"quadrature_is_not_global_certificate":True}
    (HERE/"analytic_checks.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf8",newline="\n")
    print(json.dumps({"status":"PASS","checks":len(checks)}))


if __name__=="__main__":main()
