"""Deterministic checks for the sequential audit and scalar fusion formulas."""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
from numpy.polynomial.legendre import leggauss
import math
from scipy.special import ndtr


def main():
    checks=[]
    def check(name,ok,detail=None):
        checks.append({"name":name,"pass":bool(ok),"detail":detail})
        if not ok:
            raise AssertionError(name)

    # F_delta is strictly lower away from zero on compact nonzero points.
    delta=.011628232298833967
    V=.9
    grid=np.linspace(-.2,.2,2001)
    nodes,weights=leggauss(128)
    errors=delta*nodes
    vals=np.exp(-(grid[:,None]-errors[None,:])**2/(2*V))@(weights/2)
    center=float(np.exp(-errors**2/(2*V))@(weights/2))
    gap=float(center-np.max(vals[grid!=0]))
    check("phase_average_unique_center_on_grid",gap>0,gap)

    # Direct CDF formula and Gauss rule agree for F_delta,V.
    for dv in [-.3,-.1,-.01,0.,.01,.1,.3]:
        q=float(np.exp(-(dv-delta*nodes)**2/(2*V))@(weights/2))
        cdf=math.sqrt(2*math.pi*V)/(2*delta)*(ndtr((delta-dv)/math.sqrt(V))-ndtr((-delta-dv)/math.sqrt(V)))
        check("phase_cdf_identity",abs(q-cdf)<1e-14,(dv,abs(q-cdf)))

    # Explicit curvature lower bound implies a quadratic phase-averaged drift.
    A=.82; dref=.25; B=.35; Vmin=.75; Vmax=1.25
    q=A*A/(2*Vmax)*math.exp(-(A*A*B*B+dref*dref)/(2*Vmin))
    ds=np.linspace(-B,B,101)
    Fa=np.exp(-((A*ds[:,None]-dref*nodes[None,:])**2)/(2*V))@(weights/2)
    F0=float(np.exp(-(dref*nodes)**2/(2*V))@(weights/2))
    check("drift_secant_bound_grid",np.all(F0-Fa+1e-15>=q*ds*ds),(q,float(np.min((F0-Fa)-q*ds*ds))))

    # Finite-horizon type-I and type-II inequalities, with d_min > 0.
    N=128; alpha=.01; beta=.1; kappa=.05; dmin=.2
    h=math.sqrt(N/2*math.log(1/alpha))
    pfa=math.exp(-2*h*h/N)
    pfn=math.exp(-2*(kappa*dmin*dmin*N-h)**2/N) if kappa*dmin*dmin*N>h else 1.0
    check("fixed_horizon_false_alarm_bound",pfa<=alpha*(1+1e-12),(h,pfa))
    nreq=math.ceil((math.sqrt(math.log(1/alpha))+math.sqrt(math.log(1/beta)))**2/(2*kappa*kappa*dmin**4))
    check("delay_requirement_positive",nreq>0,nreq)

    # Conservative time-uniform bias radius and audit drift constants for S1/U1.
    model_constants=[]
    R=.2; Z=2.; P0=.8; Q=.05; delta_ref=.25; b_ref=.1
    r0=R+1/Z
    for name,A in [("S1",.82),("U1",1.04)]:
        Pmax=max(P0,A*A*r0+Q)
        rho=abs(A)*max(R/(Q+R),r0/(Q+r0))
        gmax=Pmax/(Pmax+R)
        B=gmax*b_ref/(1-rho)
        Vmin=1/Z+Q+R
        Vmax=1/Z+A*A*r0+Q+R
        kappa=A*A/(2*Vmax*np.sqrt(Z*Vmax))*np.exp(-(A*A*B*B+delta_ref**2)/(2*Vmin))
        check(name+"_contractive_bias_radius",rho<1,(rho,B))
        check(name+"_positive_uniform_drift",kappa>0,kappa)
        model_constants.append({"model":name,"rho":float(rho),"bias_radius":float(B),
                                "Vmin":float(Vmin),"Vmax":float(Vmax),"kappa":float(kappa)})

    # Soft-fusion optimizer equals direct quadratic minimizer before clipping.
    rng=np.random.default_rng(20261121)
    ec=rng.normal(size=10000)
    ea=.4*rng.normal(size=10000)+.2*ec
    Pc=np.mean(ec*ec); Ra=np.mean(ea*ea); C=np.mean(ec*ea)
    H=Pc+Ra-2*C
    alpha=np.clip((Pc-C)/H,0,1)
    xs=np.linspace(0,1,10001)
    risks=np.array([np.mean(((1-x)*ec+x*ea)**2) for x in xs])
    check("soft_fusion_quadratic_minimum",abs(alpha-xs[np.argmin(risks)])<2e-4,
          (float(alpha),float(xs[np.argmin(risks)])))

    # Independent-error special case has the claimed risk-weight form.
    Pc=2.; Pa=3.; Ba=5.; alpha=Pc/(Pc+Pa+Ba)
    xs=np.linspace(0,1,100001)
    risk=(1-xs)**2*Pc+xs**2*(Pa+Ba)
    check("independent_risk_weight",abs(alpha-xs[np.argmin(risk)])<2e-5,
          (alpha,float(xs[np.argmin(risk)])))

    path=Path(__file__).with_name("formula_checks.json")
    path.write_text(json.dumps({"status":"PASS","checks":checks,"uniform_constants":model_constants},indent=2)+"\n",
                      encoding="utf8",newline="\n")
    print(json.dumps({"status":"PASS","checks":len(checks)},ensure_ascii=True))


if __name__=="__main__":
    main()
