"""Exact rational examples and closed-form constants only; no trajectory simulation."""
from fractions import Fraction as F
from pathlib import Path
import json
import math

HERE=Path(__file__).resolve().parent

def main():
    checks=[]
    def ck(name, passed, **details):
        checks.append(dict(name=name,passed=bool(passed),**details))
    def show(x):
        return {"fraction":str(x),"decimal":float(x)}
    # Generic three-time counterexample, normalized delta=1.
    A,P,R,Q,r0=F(6,5),F(175,293),F(1),F(1,10),F(2)
    K=P/(P+R); post=R*K; prior=A*A*post+Q
    beta=r0/(prior+r0); g=A*beta
    ck("generic_covariances",K==F(175,468) and prior==F(83,130)
       and beta==F(260,343) and g==F(312,343))
    shift=A*K*F(156,875)
    center=F(10201,3900)
    endpoints=[]
    for x in [center-F(1,1000),center,center+F(1,1000)]:
        health=A*(2+beta*(x-2));attack=health+g*shift
        ck("generic_strict_interval_"+str(x),1<x<x+shift<3 and 1<health<3<attack<5)
        endpoints.append({"x":show(x),"next_health":show(health),"next_attack":show(attack)})
    ck("generic_center_identity",A*(2+beta*(center-2))==F(74,25))
    ck("generic_contracts",0<g<1 and shift==F(2,25))
    # S1, without changing any of its original physical parameters.
    A,P,R,Q,Z=F(41,50),F(4,5),F(1,5),F(1,20),F(2)
    r0=R+1/Z;K=P/(P+R);post=R*K;prior=A*A*post+Q
    beta=r0/(prior+r0);g=A*beta
    boundary_preimage=-2+(2-1/A)/beta
    shift=A*K*F(5,164)
    ck("S1_coefficients",K==F(4,5) and post==F(4,25) and prior==F(9849,62500)
       and beta==F(6250,7657) and g==F(5125,7657))
    ck("S1_boundary_preimage",boundary_preimage==F(-133738,128125))
    s1end=[]
    for x in [boundary_preimage-F(1,200)-F(1,1000),
              boundary_preimage-F(1,200),
              boundary_preimage-F(1,200)+F(1,1000)]:
        health=A*(-2+beta*(x+2));attack=health+g*shift
        ck("S1_strict_interval_"+str(x),-3<x<x+shift<-1 and -3<health<-1<attack<1)
        s1end.append({"x":show(x),"next_health":show(health),"next_attack":show(attack)})
    ck("S1_contracts",0<g<1 and shift==F(1,50))
    # Closed-form bounds at the two original models. No simulation, RNG or search.
    model_constants={}
    for name,A in [("S1",.82),("U1",1.04),("A1_analytic_case",1.0)]:
        P0,Q,R,Z=.8,.05,.2,2.
        r0=R+1/Z;pmin=min(P0,Q);pmax=max(P0,A*A*r0+Q)
        theta=r0/(Q+r0); q=math.sqrt(theta)
        kmin=pmin/(pmin+R); betamax=R/(pmin+R)
        rs=math.sqrt(r0/R)/(1-q)
        # Reference budgets for reporting constants, not newly tested parameters.
        bref,dref=.1,.1
        vmax=1/Z+A*A*r0+Q+R
        hmin=A*A/(2*vmax);B=rs*bref+dref/abs(A)
        chi=-math.expm1(-hmin*B*B)/(B*B)
        c0=1/(2*(1/Z+Q+R)); M=math.sqrt(1+Z*(A*A*r0+Q+R))
        cd=(math.sqrt(c0/chi)+1/abs(A))**2
        lf=math.sqrt(2/(math.pi*(pmin+R)))+math.sqrt(Z/math.e)
        pstar=1-(1+Z*(pmin+R))**-.5
        values={
            "A":A,"P0":P0,"Q":Q,"R":R,"Z":Z,
            "initial_send_factor":abs(A)*R/(P0+R),
            "initial_silence_factor":abs(A)*r0/(P0+r0),
            "all_history_send_factor_bound_t_ge_1":abs(A)*R/(Q+R),
            "all_history_silence_factor_bound_t_ge_1":abs(A)*r0/(Q+r0),
            "normalized_contraction_q":q,"conditional_bias_radius_coefficient_r_star":rs,
            "reference_b_ref":bref,"reference_delta_ref":dref,
            "C_zero_TV_delta_squared":cd,
            "C_nonzero_TV_delta_squared":2*c0/chi+2/(A*A),
            "C_nonzero_TV_epsilon":2*M/chi+r0,
            "pmin":pmin,"pmax":pmax,
        }
        if name=="A1_analytic_case":
            values.update({
                "k_min":kmin,"beta1_max":betamax,"p_star":pstar,
                "L_star":lf/kmin,"sufficient_delta_star":pstar/(lf/kmin),
                "fixed_b_delta_dominance_limit":4*bref*kmin/(1+betamax),
                "average_damage_lower_coefficient_for_small_delta":pstar/64,
                "witness_pathwise_upper_coefficient":1/16,
                "scope":"constants only; no sampled experiment for A=1",
            })
        model_constants[name]=values
        ck(name+"/constants_finite",all(math.isfinite(v) for v in values.values() if isinstance(v,(int,float))))
        ck(name+"/normalized_contraction",0<q<1)
    # Algebraic normalized covariance identity, at rational certificates only.
    for A in [F(41,50),F(26,25),F(6,5),F(-6,5)]:
        for pp in [F(1,25),F(4,25),F(3,5)]:
            Q=F(1,20);pm=A*A*pp+Q
            for ri in [F(1,5),F(7,10)]:
                beta=ri/(pm+ri);pn=beta*pm
                ck(f"normalization_identity/{A}/{pp}/{ri}",
                   A*A*beta*beta*pp/pn==beta*(1-Q/pm))
    ck("A1_repair_budget_identity",F(1,5)/(1+F(4,5))==F(1,9))
    result={
        "status":"PASS" if all(c["passed"] for c in checks) else "FAIL",
        "checks":checks,"generic_three_time_example":endpoints,"S1_three_time_example":s1end,
        "constants":model_constants,
        "verification_limit":"Exact rational examples and evaluated formula constants; mathematical proofs are in reports, not machine-certified.",
        "random_samples":0,"trajectory_simulations":0,"optimization_runs":0,
    }
    (HERE/"algebra_validation.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n")
    print(json.dumps({"status":result["status"],"checks":len(checks),"constants":model_constants},ensure_ascii=True,indent=2))
    if result["status"]!="PASS":raise SystemExit(1)

if __name__=="__main__":
    main()
