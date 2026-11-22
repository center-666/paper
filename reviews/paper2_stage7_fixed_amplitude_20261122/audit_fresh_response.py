"""Recompute the true-onset response on saved seeds and audit interval coverage."""
from __future__ import annotations
import json, math
from fractions import Fraction as F
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
STAGE6=HERE.parent/"paper2_stage6_vector_correction_20261122"
import sys
sys.path.insert(0,str(STAGE6))
from exact_linear import matrix,update,matmul,add,transpose,asfloat
from fixed_amplitude import interval_fraction
from interval_arithmetic import Interval as I


def audit_episode(result,protocol,model):
    b=result["b"];index=result["episode"];bi=protocol["attack_strengths"].index(b)
    t0=protocol["attack_start"];N=t0+max(protocol["evaluation_windows"])
    rngs=[np.random.default_rng(s) for s in np.random.SeedSequence(
        [protocol["seed"],bi,index]).spawn(3)]
    phys,events,phase=rngs
    A=np.array(model["A"],float);C=np.array(model["C"],float)
    Q=np.array(model["Q"],float);R=float(model["R"]);Z=float(model["Z"])
    delta=float(model["quantization_half_width"])
    Af,Cf,Qf=(matrix(model[k]) for k in ("A","C","Q"))
    P=matrix(model["P0_prior"]);Rrat=F(model["R"]);Zrat=F(model["Z"])
    error=np.linalg.cholesky(np.array(model["P0_prior"],float))@phys.normal(size=2)
    h=[F(0),F(0)];hi=[I.exact(0),I.exact(0)]
    cert_by_time={}
    for cert in result["successful_certificates"]:
        cert_by_time.setdefault(int(cert["time"]),[]).append(cert)
    checks=0;cert_checks=0;min_margin=None
    for t in range(N):
        v=math.sqrt(R)*phys.normal();w=np.linalg.cholesky(Q)@phys.normal(size=2)
        r=0. if t==0 else delta*(2*phase.random()-1)
        y=float((C@error).item()+v)
        sent=bool(events.random()>math.exp(-.5*Z*(y-r)**2))
        attack_input=b if sent and t>=t0 else 0.
        noise=F(0) if sent else 1/Zrat
        post,K,T=update(P,Cf,Rrat+noise)
        Fmat=matmul(T,Af)
        if t>=t0:
            h=[sum((Fmat[i][j]*h[j] for j in range(2)),F(0))+
               (K[i][0] if sent else F(0)) for i in range(2)]
            Fint=[[interval_fraction(x) for x in row] for row in Fmat]
            Kint=[interval_fraction(row[0]) for row in K]
            hi=[sum((Fint[i][j]*hi[j] for j in range(2)),I.exact(0))+
                (Kint[i] if sent else I.exact(0)) for i in range(2)]
            for j in range(2):
                if not (F(str(hi[j].lo))<=h[j]<=F(str(hi[j].hi))):
                    raise AssertionError((b,index,t,j,"true-onset response escaped outward interval"))
            checks+=2
        for cert in cert_by_time.get(t,[]):
            d=tuple(F(x) for x in cert["direction"]);z=F(cert["z"])
            q=sum((d[i]*sum((F(model["W"][i][j])*h[j] for j in range(2)),F(0))
                   for i in range(2)),F(0))
            margin=F(str(b))*q-z
            if margin<0:
                raise AssertionError((b,index,t,"successful certificate excludes truth",str(margin)))
            min_margin=margin if min_margin is None else min(min_margin,margin)
            cert_checks+=1
        Kfloat=np.asarray(asfloat(K),float).ravel();Tfloat=np.asarray(asfloat(T),float)
        post_error=error-Kfloat*(y+attack_input) if sent else error-Kfloat*r
        error=A@post_error+w
        P=add(matmul(matmul(Af,post),transpose(Af)),Qf)
    return {"b":b,"episode":index,"response_interval_steps":checks//2,
            "successful_certificate_constraints_checked":cert_checks,
            "minimum_certificate_margin":None if min_margin is None else str(min_margin)}


def main():
    protocol=json.loads((HERE/"fresh_protocol.json").read_text(encoding="utf8"))
    model=json.loads((STAGE6/"model.json").read_text(encoding="utf8"))
    rows=[json.loads(p.read_text(encoding="utf8")) for p in sorted(
        (HERE/"results"/"fresh_confirmation").glob("b*_episode*.json"))]
    if len(rows)!=36:raise AssertionError("Expected all 36 frozen independent episodes")
    audited=[audit_episode(r,protocol,model) for r in rows]
    minimum_margin=min((F(x["minimum_certificate_margin"])
        for x in audited if x["minimum_certificate_margin"] is not None),default=None)
    out={"status":"PASS","seed":protocol["seed"],"episodes":len(audited),
         "true_onset_interval_step_checks":sum(x["response_interval_steps"] for x in audited),
         "successful_certificate_truth_constraints":sum(x["successful_certificate_constraints_checked"] for x in audited),
         "all_successful_certificate_margins_nonnegative":minimum_margin is None or minimum_margin>=0,
         "minimum_certificate_margin_approx":None if minimum_margin is None else format(float(minimum_margin),".12g"),
         "random_samples_generated":False,
         "method":"regenerate only the already frozen NumPy streams, exact rational true-onset response and outward Decimal enclosure; no likelihood search or new seeds"}
    (HERE/"analysis"/"fresh_response_audit.json").write_text(json.dumps(out,indent=2)+"\n",encoding="utf8",newline="\n")
    print(json.dumps(out,indent=2))


if __name__=="__main__":main()
