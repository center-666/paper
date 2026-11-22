"""Deterministic cache, derivative, tangent and fail-closed checks."""
from pathlib import Path
from decimal import Decimal,localcontext
import json,hashlib,time
from strong_concavity import CachedRecord,ExactRecord,Step,I,D
from check_certificate import MODELS,reference_point

HERE=Path(__file__).resolve().parent


def exact_derivative(model,steps,k,b):
    with localcontext() as c:
        c.prec=100
        A,Q,R,Z,P=(D(model[x]) for x in ("A","Q","R","Z","P0"))
        b=D(b);H=D(0);value=D(0);second=D(0)
        for t,step in enumerate(steps):
            r=D(step.r);S=P+R;V=S+1/Z;K=P/(P+R+(0 if step.sent else 1/Z))
            if t>=k:
                hp=A*H;a=1-hp
                if step.sent:
                    u=D(step.u);v=u-r-b;x=Z*v*v/2;e=x.exp()
                    value+=(a*u-a*a*b)/S-Z*v/(e-1)
                    second+=-a*a/S+Z*(e-1-2*x*e)/(e-1)**2
                else:
                    value+=(-r*hp-hp*hp*b)/V
                    second+=-hp*hp/V
                H=(1-K)*hp+(K if step.sent else 0)
            P=A*A*P*(1-K)+Q
        return +value,+second


def main():
    checks=[]
    def check(name,ok,detail=None):
        checks.append({"name":name,"pass":bool(ok),"detail":detail})
        if not ok:raise AssertionError(name+str(detail))
    benches=[]
    for model in MODELS:
        steps=[Step(True,".13",".001"),Step(False,None,"-.002"),Step(True,"-.21","0"),
               Step(True,".37",".003"),Step(False,None,"0"),Step(True,"-.09","-.001")]
        record=CachedRecord(model,steps)
        for k in range(7):
            for b in ("0",".05",".10",".25"):
                exact,H=reference_point(model,steps,k,b)
                check("cached_likelihood_encloses_100digit",record.log_likelihood(k,I.exact(b)).contains(exact))
                check("cached_H_encloses_100digit",record.coefficient(k).contains(H))
                if k>=len(steps):continue
                prime,second=exact_derivative(model,steps,k,b)
                check("interval_derivative_encloses_100digit",record.derivative(k,I.exact(b)).contains(prime))
                if record.cache[k][3]:
                    check("uniform_strong_curvature",second<=-D(1)/(D(model["P0"])+D(model["R"])))
        for k in (0,2,5):
            for segment in record.segments(k,I(D(0),D(".25"))):
                upper=record.segment_upper(k,segment)
                for j in range(1,10):
                    b=(segment.lo+(segment.hi-segment.lo)*D(j)/10)
                    exact,_=reference_point(model,steps,k,str(b))
                    check("strong_tangent_dominates_interior",upper>=exact)
        # Fixed short pole-neighborhood certification, identical target and budget.
        fixture=[Step(True,".00001","0") for _ in range(8)]
        old=ExactRecord(model,fixture);new=CachedRecord(model,fixture)
        for z in (".05",".099",".20"):
            before=old.certify(z,max_nodes=256)
            after=new.certify(z,max_nodes=256)
            check("certification_decisions_agree_on_fixture",before["certified"]==after["certified"],
                  {"model":model["id"],"z":z,"old_nodes":before["nodes"],"new_nodes":after["nodes"]})
        # A budget-exhausted result must remain zero, even with a positive true inf.
        unresolved=new.certify(".099",max_nodes=0)
        check("zero_budget_fail_closed",not unresolved["certified"] or unresolved["nodes"]==0)
        silent=CachedRecord(model,[Step(False,None,"0") for _ in range(6)])
        check("no_send_remains_healthy",not silent.certify(".01")["certified"])
        for length in (16,64,128):
            sequence=[Step(i%3!=1, str(D(".18")+D(i%11)/100) if i%3!=1 else None,
                           str(D((i%3)-1)/1000)) for i in range(length)]
            started=time.perf_counter();cached=CachedRecord(model,sequence);pre=time.perf_counter()-started
            old=ExactRecord(model,sequence)
            onsets=(0,length//2)
            grid=[str(D(".007")+D(j)/1000) for j in range(20)]
            started=time.perf_counter()
            values_old=[old.log_likelihood(k,I.exact(b)) for k in onsets for b in grid]
            old_sec=time.perf_counter()-started
            started=time.perf_counter()
            values_new=[cached.log_likelihood(k,I.exact(b)) for k in onsets for b in grid]
            cached_sec=time.perf_counter()-started
            check("benchmark_intervals_overlap",
                  all(x.lo<=y.hi and y.lo<=x.hi for x,y in zip(values_old,values_new)))
            benches.append({"model":model["id"],"record_length":length,"calls":len(grid)*len(onsets),
                            "cache_preparation_seconds":pre,"old_evaluation_seconds":old_sec,
                            "cached_evaluation_seconds":cached_sec,
                            "score_only_speed_ratio":old_sec/cached_sec,
                            "full_onset_cache_included_once":True})
    output={"status":"PASS","checks":checks,"check_count":len(checks),
            "benchmarks":benches,"random_samples_generated":False,
            "scope":"Fixed synthetic records, no certification-delay or MSE performance claim",
            "source_sha256":hashlib.sha256((HERE/"strong_concavity.py").read_bytes()).hexdigest()}
    (HERE/"optimizer_checks.json").write_text(json.dumps(output,indent=2)+"\n",encoding="utf8",newline="\n")
    print(json.dumps({"status":"PASS","checks":len(checks),"benchmarks":benches}))


if __name__=="__main__":main()
