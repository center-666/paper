"""Deterministic budget and finite-tree checks; no random samples."""
from __future__ import annotations

from fractions import Fraction as F
from itertools import product
import hashlib
import json
import math
from pathlib import Path

HERE=Path(__file__).resolve().parent


def root(A,Q,R):
    c=R-Q-A*A*R
    return (-c+math.sqrt(c*c+4*Q*R))/2


def main():
    checks=[]
    def check(name,condition,detail=None):
        checks.append({"name":name,"pass":bool(condition),"detail":detail})
        if not condition:
            raise AssertionError(name)

    bmax=.25
    epsilon=.01
    models=[{"id":"S1","A":.82},{"id":"U1","A":1.04}]
    rows=[]
    for model in models:
        A=model["A"];Q=.05;R=.2;Z=2.;P0=.8
        r0=R+1/Z
        pmin=root(A,Q,R)
        pmax=max(P0,root(A,Q,r0))
        kmin=pmin/(pmin+R)
        kmax=pmax/(pmax+R)
        gamma=A*r0/(pmin+r0)
        selected=kmax if A<=1 else kmin
        cB=selected/(1-A*(1-selected))
        B=cB*bmax
        check(model["id"]+"_silent_contraction",gamma<1,gamma)
        check(model["id"]+"_send_denominator_positive",1-A*(1-kmin)>0)
        # Algebraic endpoint check on the invariant map, not a Monte Carlo test.
        for gain in (kmin,kmax):
            check(model["id"]+"_send_invariance",A*(1-gain)*B+gain*bmax<=B+1e-14)
        rows.append({
            "model":model["id"],"A":A,"Q":Q,"R":R,"Z":Z,"P0":P0,
            "prior_covariance_lower":pmin,"prior_covariance_upper":pmax,
            "send_gain_lower":kmin,"send_gain_upper":kmax,
            "silent_contraction_upper":gamma,"bias_multiplier":cB,
            "b_max":bmax,"confidence_failure":epsilon,
            "B_max":B,"B_max_squared":B*B,
            "general_attack_penalty_per_step":2*epsilon*B*B,
            "healthy_cost_upper_per_step":epsilon*B*B,
            "general_attack_penalty_T512":2*epsilon*512*B*B,
            "general_attack_penalty_T2048":2*epsilon*2048*B*B,
            "certificate_RMS_sufficient_threshold_for_general_expected_gain":math.sqrt(2*epsilon)*B})

    # Exact finite event-tree check: arbitrary normalized predictable Q can be
    # used even when it is not one of the two data-generating models.
    # Success probability under each model depends on the previous bit.
    eps=F(1,5);depth=7
    def prob_one(theta,prefix):
        if theta==0:
            return F(1,3) if not prefix or prefix[-1]==0 else F(2,5)
        return F(3,4) if not prefix or prefix[-1]==0 else F(3,5)
    def q_one(prefix):
        return F(4,5) if sum(prefix)%2==0 else F(1,5)
    for theta in (0,1):
        mass=F(0);failure_mass=F(0);eq_error=F(0)
        for path in product((0,1),repeat=depth):
            lp=F(1);lq=F(1);failed=False
            for t,y in enumerate(path):
                prefix=path[:t]
                pp=prob_one(theta,prefix);qq=q_one(prefix)
                pbranch=pp if y else 1-pp
                qbranch=qq if y else 1-qq
                # Conditional density-ratio increment has mean exactly one.
                eq_error=max(eq_error,abs(pp*(qq/pp)+(1-pp)*((1-qq)/(1-pp))-1))
                lp*=pbranch;lq*=qbranch
                if lp<=eps*lq:
                    failed=True
            mass+=lp
            if failed:failure_mass+=lp
        check(f"reference_Q_tree_mass_theta{theta}",mass==1)
        check(f"reference_Q_density_martingale_theta{theta}",eq_error==0)
        check(f"reference_Q_anytime_coverage_theta{theta}",failure_mass<=eps,
              {"failure_probability":float(failure_mass),"bound":float(eps),
               "exact_fraction":str(failure_mass),"tree_leaves":2**depth})

    # Risk certificate algebra and optimality at L. These use exact rationals.
    for L,U in ((F(0),F(1)),(F(1,4),F(3,4)),(F(1,2),F(1,2))):
        for c in (F(0),L/2,L,(L+U)/2,U,2*U):
            minimum_gain=2*L*c-c*c
            check("minimax_gain_identity",L*L-minimum_gain==(c-L)**2)
        for theta in (L,(L+U)/2,U):
            check("covered_gain_at_L",2*theta*L-L*L>=L*L)
    # Outside coverage, theta>=0 gives -L^2<=gain. Therefore gain>=L^2-2*B^2
    # when L<=B; also check a case attaining the sharp coefficient two.
    B=F(3,4);L=B;theta=F(0)
    check("failure_budget_two_is_attained",
          2*theta*L-L*L==L*L-2*B*B)
    result={
        "status":"PASS","performance_random_samples_generated":False,
        "numerical_scope":"deterministic formulas and exact rational finite fixtures; not interval certification or performance evidence",
        "source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "rows":rows,"checks":checks}
    (HERE/"risk_budgets.json").write_text(
        json.dumps(result,indent=2)+"\n",encoding="utf8",newline="\n")
    print(json.dumps({"status":"PASS","checks":len(checks),"rows":rows},indent=2))


if __name__=="__main__":
    main()
