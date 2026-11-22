"""Deterministic cache/suffix/directional certificates and cost preflight."""
from pathlib import Path
from fractions import Fraction as F
from decimal import localcontext
import hashlib,json,time
from vector_record import VectorRecord,I,D,interval_fraction
from exact_linear import matrix,matmul,transpose,add,update

HERE=Path(__file__).resolve().parent


def reference_likelihood(model,rows,k,b):
    """100-digit independent scalar likelihood using exact physical gains."""
    A,C,Q,P=(matrix(model[x]) for x in ("A","C","Q","P0_prior"))
    R,Z=F(model["R"]),F(model["Z"])
    with localcontext() as ctx:
        ctx.prec=100
        dec=lambda x:D(x.numerator)/D(x.denominator)
        h=[D(0),D(0)];total=D(0);b=D(b)
        for t,(sent,u,r) in enumerate(rows):
            post,K,T=update(P,C,R+(0 if sent else 1/Z))
            hp=[sum(dec(A[i][j])*h[j] for j in range(2)) for i in range(2)]
            S=dec(matmul(matmul(C,P),transpose(C))[0][0]+R);V=S+1/dec(Z)
            if t>=k:
                d=-sum(dec(C[0][j])*hp[j] for j in range(2))*b
                if sent:
                    u=D(u);r=D(r);shift=b+d
                    lh=lambda x:(1-(-dec(Z)*x*x/2).exp()).ln()
                    total+=(u*shift-shift*shift/2)/S+lh(u-b-r)-lh(u-r)
                else:
                    r=D(r);total+=(r*d-d*d/2)/V
                h=[sum(dec(T[i][j])*hp[j] for j in range(2))+(dec(K[i][0]) if sent else 0)
                   for i in range(2)]
            P=add(matmul(matmul(A,post),transpose(A)),Q)
        return +total,tuple(+x for x in h)


def main():
    model=json.loads((HERE/"model.json").read_text(encoding="utf8"))
    rows=[(True,".13",".001"),(False,None,"-.002"),(True,"-.21","0"),(True,".37",".003"),
          (False,None,"0"),(True,"-.09","-.001")]
    record=VectorRecord(model)
    for row in rows:record.append(*row)
    checks=[]
    def check(name,ok):
        checks.append({"name":name,"pass":bool(ok)})
        if not ok:raise AssertionError(name)
    for b in ("0",".05",".1",".25"):
        suffix=record.all_likelihoods(I.exact(b))
        for k in range(len(rows)):
            ref,H=reference_likelihood(model,rows,k,b)
            direct=record.likelihood(k,I.exact(b))
            check("point_likelihood_encloses_100digits",direct.contains(ref) and suffix[k].contains(ref))
            check("vector_H_encloses_100digits",all(h.contains(x) for h,x in zip(record.candidates[k]["H"],H)))
    fixture=VectorRecord(model)
    for _ in range(8):fixture.append(True,".00001","0")
    positive=fixture.certify_direction((1,0),".05")
    opposite=fixture.certify_direction((-1,0),".05",max_nodes=2)
    check("positive_direction_certificate",positive["certified"])
    check("opposite_direction_not_wrongly_certified",not opposite["certified"])
    checks_out={"positive":positive,"opposite":opposite}
    negative=VectorRecord(model)
    for _ in range(8):negative.append(False,None,"0")
    check("health_class_retained_no_action",not negative.certify_direction((1,0),".025")["certified"])
    # Verify halfspace propagation algebra exactly, including adverse input sign.
    A=matrix(model["A"]);C=matrix(model["C"]);Q=matrix(model["Q"]);P=matrix(model["P0_prior"])
    from exact_linear import inverse
    for sent in (False,True):
        post,K,T=update(P,C,F(model["R"])+(0 if sent else 1/F(model["Z"])))
        Fmat=matmul(T,A);d=[[F(1)],[F(-2)]];z=F(1,10)
        nxt=matmul(transpose(inverse(Fmat)),d)
        scalar=matmul(transpose(nxt),K)[0][0] if sent else F(0)
        znew=z+min(F(0),scalar*F(1,4))
        for th1,th2 in ((F(3,10),F(1,10)),(F(1),F(1,5)),(F(0),F(-1))):
            theta=[[th1],[th2]]
            if matmul(transpose(d),theta)[0][0]<z:continue
            for b in (F(0),F(1,10),F(1,4)):
                future=add(matmul(Fmat,theta),[[row[0]*b if sent else F(0)] for row in K])
                check("halfspace_transport_valid",matmul(transpose(nxt),future)[0][0]>=znew)
    # Predeclared deterministic cost check before selecting any random sample.
    started=time.perf_counter();cost_record=VectorRecord(model)
    for t in range(128):
        cost_record.append(t%3==0,".2" if t%3==0 else None,"0")
    build_seconds=time.perf_counter()-started
    started=time.perf_counter()
    cost_result=cost_record.certify_direction((1,0),".025",max_nodes=64)
    cert_seconds=time.perf_counter()-started
    output={"status":"PASS","checks":checks,"check_count":len(checks),
            "directional_fixtures":checks_out,"cost_preflight":{"length":128,
                "maintenance_seconds":build_seconds,"certificate_seconds":cert_seconds,
                "certificate_reason":cost_result["reason"],"full_cost_includes_reference_and_all_onset_cache":True},
            "performance_random_samples_generated":False,
            "source_sha256":hashlib.sha256((HERE/"vector_record.py").read_bytes()).hexdigest()}
    (HERE/"vector_record_checks.json").write_text(json.dumps(output,indent=2)+"\n",encoding="utf8",newline="\n")
    print(json.dumps({"status":"PASS","checks":len(checks),"cost":output["cost_preflight"]}))


if __name__=="__main__":main()
