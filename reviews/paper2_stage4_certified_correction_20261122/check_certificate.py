"""Deterministic numeric-contract checks, not attack-performance simulations."""
from __future__ import annotations
import hashlib
import json
from decimal import Decimal,localcontext
from pathlib import Path
import sys
import time
from interval_arithmetic import Interval as I,log_trigger,PRECISION
from certificate import ExactRecord,Step

HERE=Path(__file__).resolve().parent
MODELS=(
    dict(id="S1",A="0.82",Q="0.05",R="0.2",Z="2",P0="0.8",delta="0.011628232298833967"),
    dict(id="U1",A="1.04",Q="0.05",R="0.2",Z="2",P0="0.8",delta="0.022259755314928388"))


def reference_point(model,steps,k,b):
    """Independent 100-digit scalar recursion for enclosure spot checks."""
    with localcontext() as c:
        c.prec=100
        D=Decimal
        A,Q,R,Z,P=(D(model[name]) for name in ("A","Q","R","Z","P0"))
        b=D(b);H=D(0);result=D(0)
        for t,step in enumerate(steps):
            r=D(step.r);S=P+R;V=S+1/Z;K=P/(P+R+(0 if step.sent else 1/Z))
            if t>=k:
                d=-A*H*b
                if step.sent:
                    u=D(step.u)
                    def lh(x):
                        return (1-(-Z*x*x/2).exp()).ln()
                    result+=(u*(b+d)-(b+d)**2/2)/S+lh(u-b-r)-lh(u-r)
                else:
                    result+=(r*d-d*d/2)/V
                H=(1-K)*A*H+(K if step.sent else 0)
            P=A*A*P*(1-K)+Q
        return +result,+H


def main():
    checks=[]
    def check(name,ok,detail=None):
        checks.append(dict(name=name,pass_check=bool(ok),detail=detail))
        if not ok:
            raise AssertionError(name)
    x=I(Decimal("-0.2"),Decimal("0.3"))
    check("interval_square_includes_zero",x.square().contains(0) and x.square().contains(".09"))
    check("trigger_zero_is_minus_infinity",log_trigger(I.exact(0),"2").hi==Decimal("-Infinity"))
    check("interval_trigger_crossing_zero_keeps_upper",
          log_trigger(x,"2").lo==Decimal("-Infinity") and log_trigger(x,"2").hi.is_finite())
    allcerts=[]
    for model in MODELS:
        steps=[Step(True,"0.13","0.001"),Step(False,None,"-0.002"),
               Step(True,"-0.21","0"),Step(True,"0.37","0.003"),
               Step(False,None,"0"),Step(True,"-0.09","-0.001")]
        record=ExactRecord(model,steps)
        for k in range(len(steps)+1):
            for b in ("0","0.05","0.10","0.25"):
                exact,H=reference_point(model,steps,k,b)
                box=record.log_likelihood(k,I.exact(b))
                check(model["id"]+"_point_likelihood_encloses_100digit",
                      box.contains(exact),{"k":k,"b":b,"width":str(box.hi-box.lo)})
                check(model["id"]+"_pollution_coefficient_encloses_100digit",
                      record.coefficient(k).contains(H))
        for k in (0,2,5):
            B=I(Decimal("0.02"),Decimal("0.24"))
            box=record.log_likelihood(k,B)
            for j in range(12):
                b=Decimal("0.02")+Decimal(j)*Decimal("0.02")
                exact,_=reference_point(model,steps,k,b)
                check(model["id"]+"_interval_contains_interior_likelihood",box.contains(exact))
        check(model["id"]+"_unstarted_is_healthy",record.log_likelihood(99,I.exact(".25")).contains(0)
              and record.coefficient(99).contains(0))
        # Predetermined artificial received records; not a state/noise simulation.
        # Tiny innovations have positive send density, despite being rare.
        informative=[Step(True,"0.00001","0") for _ in range(8)]
        evidence=ExactRecord(model,informative)
        start=time.perf_counter()
        results=[evidence.certify(z,max_nodes=512) for z in ("0","0.01","0.05")]
        elapsed=time.perf_counter()-start
        check(model["id"]+"_positive_certificate_exists_on_fixed_fixture",
              any(c["certified"] and Decimal(c["lower_bound"])>0 for c in results))
        check(model["id"]+"_zero_compute_budget_fails_closed",
              not evidence.certify("0.2",max_nodes=0)["certified"])
        negative=ExactRecord(model,[Step(False,None,"0") for _ in range(8)])
        outcome=negative.certify(".01")
        check(model["id"]+"_health_retained_no_correction",
              not outcome["certified"] and outcome["lower_bound"]=="0")
        for eps_bad in ("0","1","2","NaN"):
            try:
                evidence.certify(".01",epsilon=eps_bad)
                accepted=True
            except ValueError:
                accepted=False
            check(model["id"]+"_invalid_epsilon_rejected_"+eps_bad,not accepted)
        for cap in ("0","-1","Infinity"):
            try:
                evidence.certify(".01",bmax=cap)
                accepted=True
            except ValueError:
                accepted=False
            check(model["id"]+"_invalid_amplitude_cap_rejected_"+cap,not accepted)
        for dictionary,mass in (((),".5"),(("0.1",),"1.1")):
            try:
                evidence.reference(dictionary,mass)
                accepted=True
            except ValueError:
                accepted=False
            check(model["id"]+"_invalid_reference_rejected",not accepted)
        allcerts.append({"model":model["id"],"fixed_fixture":informative[0].__dict__,
                         "repeats":8,"seconds":elapsed,"certificates":results,
                         "negative_fixture":outcome})
        # Strict maximin improvement c=L against theta in [L,U].
        with localcontext() as c:
            c.prec=60
            L=Decimal(".03");U=Decimal(".2")
            for theta in (L,(L+U)/2,U):
                check("risk_gain_at_least_L_squared",2*theta*L-L*L>=L*L)
    split_fixture=ExactRecord(MODELS[0],[Step(True,"0.00001","0") for _ in range(8)])
    split=split_fixture.certify(".099",max_nodes=256)
    check("successful_certificate_requires_actual_interval_splitting",
          split["certified"] and split["nodes"]>0,split)
    exhausted=split_fixture.certify(".099",max_nodes=0)
    check("same_problem_no_refinement_budget_fails_closed",
          not exhausted["certified"] and exhausted["reason"]=="UNRESOLVED_NODE_LIMIT",exhausted)
    result={"status":"PASS","checks":checks,"check_count":len(checks),
            "random_samples_generated":False,"performance_recovery_claimed":False,
            "precision":PRECISION,"python":sys.version,
            "fixtures":allcerts,"assumption":"Decimal inputs interpreted as exact reals",
            "arithmetic_contract":"Directed elementary arithmetic and outward-ULP enclosure of correctly-rounded Decimal exp/ln",
            "not_machine_formal_verification":True,
            "input_hashes":{name:hashlib.sha256((HERE/name).read_bytes()).hexdigest()
                            for name in ("interval_arithmetic.py","certificate.py")}}
    (HERE/"certificate_checks.json").write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",
                                                encoding="utf8",newline="\n")
    print(json.dumps({"status":"PASS","checks":len(checks),"fixtures":allcerts},ensure_ascii=False))


if __name__=="__main__":
    main()
