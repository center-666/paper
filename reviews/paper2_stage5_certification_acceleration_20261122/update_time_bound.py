"""Replace the old finite-alphabet strong-attack cap only after global replay."""
from pathlib import Path
import json,sys
HERE=Path(__file__).resolve().parent
PREV=HERE.parent/"paper2_stage4_certified_correction_20261122"
sys.path.insert(0,str(PREV))
from interval_arithmetic import Interval as I,D
from compute_separation_bounds import constants,epsilon_upper
from check_certificate import MODELS


def main():
    rows=[]
    for model in MODELS:
        for gap in (".15",".2",".25"):
            stem=f"{model['id']}_gap{D(gap)}_target{D('.0001')}"
            v=json.loads((HERE/"fourier_certificates"/(stem+"_verification.json")).read_text(encoding="utf8"))
            assert v["status"]=="PASS" and v["root_domain_covered"]
        c=constants(model);b=I.exact(".25");eps=I.exact(".001")
        pi=I.exact(".5")/(201*202*3);a="0.9999";kstar=200;J=3
        L=0
        while (c["cB"]*(c["rho"].ln()*L).exp()).hi>(c["kmin"]/2).lo:L+=1
        v=(b*c["kmin"]/2).square()
        allowance=(c["send_probability"]-eps-2*eps*c["B"].square()/v).lo
        assert allowance>0
        target=(I.exact(allowance)/2).lo
        lo=max(L,10001);hi=lo
        while epsilon_upper(hi,L,kstar,J,eps.lo,pi,a)>=target:hi*=2
        while hi-lo>1:
            mid=(lo+hi)//2
            if epsilon_upper(mid,L,kstar,J,eps.lo,pi,a)<target:hi=mid
            else:lo=mid
        exclusion=epsilon_upper(hi,L,kstar,J,eps.lo,pi,a)
        gain=v*(c["send_probability"]-eps-I.exact(exclusion))-2*eps*c["B"].square()
        ratio=(I.exact(hi+kstar+1)/I.exact(hi+kstar)*I.exact(a)).hi
        assert ratio<1 and gain.lo>0
        old=json.loads((PREV/"separation_bounds.json").read_text(encoding="utf8"))
        oldrow=next(r for r in old["rows"] if r["model"]==model["id"] and r["b"]=="0.25")
        rows.append({"model":model["id"],"b":".25","epsilon":".001","true_onset":200,
            "dictionary":["0.05","0.10","0.25"],"health_mixture_mass":".5",
            "true_reference_weight":pi.json(),"old_affinity_gap_lower":oldrow["separation"]["hellinger_gap_lower"],
            "new_affinity_gap_lower":".0001","new_affinity_upper":a,
            "old_sufficient_age":oldrow["certified_sufficient_attack_age"],
            "new_sufficient_age":hi,"exclusion_probability_upper":str(exclusion),
            "conditional_risk_improvement_expectation_lower":str(gain.lo),
            "age_ratio":oldrow["certified_sufficient_attack_age"]/hi,
            "later_age_monotonicity_upper":str(ratio),
            "claim":"sufficient bound under same finite dictionary, not actual recovery delay or continuous-family uniform rate"})
    result={"status":"PASS","rows":rows,"random_samples_generated":False,
            "same_risk_budget_and_reference_as_stage4":True}
    (HERE/"new_time_bounds.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf8",newline="\n")
    print(json.dumps(result,indent=2))


if __name__=="__main__":main()
