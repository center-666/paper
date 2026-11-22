"""Explicit, conservative, outward-rounded Hellinger separation constants."""
from decimal import Decimal,localcontext
from pathlib import Path
import json,hashlib
from interval_arithmetic import Interval as I,PRECISION
from certificate import ExactRecord
from check_certificate import MODELS

HERE=Path(__file__).resolve().parent
D=Decimal
PI=I(D("3.141592653589793238462643383279502884197169399375105820974944592307816"),
     D("3.141592653589793238462643383279502884197169399375105820974944592307817"))


def constants(model):
    A,Q,R,Z,P0=(I.exact(model[k]) for k in ("A","Q","R","Z","P0"))
    linear=R-Q-A*A*R
    pmin=(-linear+(linear.square()+4*Q*R).sqrt())/2
    kmin=pmin/(pmin+R);kmax=P0/(P0+R)
    r0=R+1/Z
    rho=A*r0/(pmin+r0)
    gain=kmax if A.hi<1 else kmin
    cB=gain/(1-A*(1-gain))
    smin=pmin+R;smax=P0+R
    B=cB*I.exact(".25");Dprior=A*B
    return {"A":A,"Z":Z,"kmin":kmin,"rho":rho,"cB":cB,"B":B,
            "Dprior":Dprior,"smin":smin,"smax":smax,
            "send_probability":1-1/(1+Z*smin).sqrt()}


def separation(model,eta):
    c=constants(model)
    eta=I.exact(eta);delta=I.exact(model["delta"])
    max_density=1/(2*PI*c["smin"]).sqrt()
    distance=delta+I.exact(".375")+c["Dprior"]
    min_density=(-distance.square()/(2*c["smin"])).exp()/(2*PI*c["smax"]).sqrt()
    trigger=1-(-c["Z"]*eta.square()/8).exp()
    lower_density=min_density*trigger
    h_candidate=(lower_density/(2*c["Z"]*max_density)).sqrt()
    width=I.exact(min((eta/2).lo,h_candidate.lo))
    # Use a lower density and a lower width; affinity upper is rounded upward.
    gap=I.exact(lower_density.lo)*width/4
    a_upper=(1-gap).hi
    assert 0<a_upper<1
    return {"amplitude_gap":str(eta.lo),"density_lower":str(lower_density.lo),
            "neighborhood_halfwidth":str(width.lo),"hellinger_gap_lower":str(gap.lo),
            "affinity_upper":str(a_upper)}


def epsilon_upper(n,L,kstar,J,eps,pistar,aupper):
    nI=I.exact(n);a=I.exact(aupper)
    loga=a.ln()
    an=(loga*nI).exp()
    recent=(loga*I.exact(n-L+1)).exp()
    count=(J-1)*(kstar+n)
    return ((count*an+(L-1)*recent+an)/(I.exact(eps)*pistar).sqrt()).hi


def main():
    rows=[]
    bvalues=(D(".05"),D(".1"),D(".25"))
    eps=D(".001");kstar=200;J=3
    pistar=I.exact(".5")/((kstar+1)*(kstar+2)*J)
    for model in MODELS:
        c=constants(model)
        L=0
        while (c["cB"]*(c["rho"].ln()*L).exp()).hi>(c["kmin"]/2).lo:
            L+=1
        for b in bvalues:
            gaps=[b]+[abs(b-bj) for bj in bvalues if bj!=b]
            eta=min(gaps)
            sep=separation(model,str(eta))
            v=(I.exact(b)*c["kmin"]/2).square()
            epsmax=v*c["send_probability"]/(v+2*c["B"].square())
            limiting=v*(c["send_probability"]-I.exact(eps))-2*I.exact(eps)*c["B"].square()
            row={"model":model["id"],"b":str(b),"confidence_failure":str(eps),
                 "forgetting_length":L,"risk_budget_epsilon_upper_limit":epsmax.json(),
                 "limiting_gain_lower":str(limiting.lo),"separation":sep,
                 "mixing_true_weight":pistar.json(),"onset":kstar,
                 "constants":{name:box.json() for name,box in c.items()}}
            if limiting.lo>0:
                allowance=(c["send_probability"]-I.exact(eps)-
                           2*I.exact(eps)*c["B"].square()/v).lo
                target=allowance/2
                # Ensure n a^n factors are decreasing for all later n.
                lam_lower=(-I.exact(sep["affinity_upper"]).ln()).lo
                with localcontext() as ctx:
                    ctx.prec=PRECISION
                    monotone_start=int((1/lam_lower).to_integral_value(rounding="ROUND_CEILING"))+1
                lo=max(L,monotone_start);hi=lo
                while epsilon_upper(hi,L,kstar,J,eps,pistar,sep["affinity_upper"])>=target:
                    hi*=2
                while hi-lo>1:
                    mid=(hi+lo)//2
                    if epsilon_upper(mid,L,kstar,J,eps,pistar,sep["affinity_upper"])<target:
                        hi=mid
                    else:
                        lo=mid
                excl=epsilon_upper(hi,L,kstar,J,eps,pistar,sep["affinity_upper"])
                gain=v*(c["send_probability"]-I.exact(eps)-I.exact(excl))-2*I.exact(eps)*c["B"].square()
                assert gain.lo>0
                row.update({"certified_sufficient_attack_age":hi,
                            "exclusion_failure_upper":str(excl),
                            "per_step_expected_gain_lower_at_and_after_age":str(gain.lo),
                            "rate_is_conservative_not_prediction":True})
            else:
                row["certified_sufficient_attack_age"]=None
                row["reason"]="confidence budget too large for this sufficient risk bound"
            rows.append(row)
    out={"status":"PASS","random_samples_generated":False,
         "method":"Analytic local-density separation with outward Decimal interval constants",
         "scope":"Finite inversion alphabet {0.05,0.10,0.25}; exact physical mixture with health mass .5 and w_k=1/[(k+1)(k+2)]",
         "precision":PRECISION,"rows":rows,
         "source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (HERE/"separation_bounds.json").write_text(json.dumps(out,indent=2)+"\n",encoding="utf8",newline="\n")
    for r in rows:
        print(r["model"],"b",r["b"],"L",r["forgetting_length"],
              "epsilon_limit",r["risk_budget_epsilon_upper_limit"]["lo"],
              "gap",r["separation"]["hellinger_gap_lower"],
              "sufficient_age",r["certified_sufficient_attack_age"])


if __name__=="__main__":
    main()
