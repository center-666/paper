"""Independent 100-digit scalar check of the new sufficient-age result."""
from decimal import Decimal,localcontext
from pathlib import Path
import json,hashlib
HERE=Path(__file__).resolve().parent
D=Decimal


def main():
    data=json.loads((HERE/"new_time_bounds.json").read_text(encoding="utf8"))
    checks=[]
    for row in data["rows"]:
        with localcontext() as ctx:
            ctx.prec=100
            A=D(".82") if row["model"]=="S1" else D("1.04")
            R=D(".2");Q=D(".05");Z=D(2)
            coefficient=R-Q-A*A*R
            pmin=(-coefficient+(coefficient**2+4*Q*R).sqrt())/2
            kmin=pmin/(pmin+R)
            r0=R+1/Z;rho=A*r0/(pmin+r0)
            gain=D(".8") if A<1 else kmin
            cB=gain/(1-A*(1-gain));B=D(".25")*cB
            sends=1-1/(1+Z*(pmin+R)).sqrt()
            L=0
            while cB*rho**L>kmin/2:L+=1
            n=row["new_sufficient_age"];a=D(".9999");eps=D(".001")
            pi=D(".5")/D(201*202*3)
            fail=(2*(n+200)*a**n+(L-1)*a**(n-L+1)+a**n)/(eps*pi).sqrt()
            v=(D(".25")*kmin/2)**2
            risk=v*(sends-eps-fail)-2*eps*B**2
            assert fail<=D(row["exclusion_probability_upper"])
            assert risk>=D(row["conditional_risk_improvement_expectation_lower"])>0
            assert D(n+201)/D(n+200)*a<1
            checks.append({"model":row["model"],"age":n,"high_precision_failure":str(fail),
                           "high_precision_gain":str(risk),"pass":True})
    out={"status":"PASS","checks":checks,"random_samples_generated":False,
         "input_sha256":hashlib.sha256((HERE/"new_time_bounds.json").read_bytes()).hexdigest()}
    (HERE/"independent_time_checks.json").write_text(json.dumps(out,indent=2)+"\n",encoding="utf8",newline="\n")
    print(json.dumps(out))


if __name__=="__main__":main()
