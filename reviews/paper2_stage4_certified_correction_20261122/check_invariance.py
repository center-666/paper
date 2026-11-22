"""Exact rational coefficient checks on complete finite event trees."""
from fractions import Fraction as F
from itertools import product
import hashlib,json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def main():
    checks=[]
    for name,A in (("S1",F(82,100)),("U1",F(104,100))):
        Q,R,Z,P0=F(1,20),F(1,5),F(2),F(4,5)
        for bits in product((0,1),repeat=8):
            P=P0;coeffs=[F(0) for _ in range(9)]
            direct_terms=[[] for _ in range(9)]
            a_history=[];K_history=[]
            for t,sent in enumerate(bits):
                Ri=R+(0 if sent else 1/Z)
                K=P/(P+Ri);a=A*(1-K)
                a_history.append(a);K_history.append(K)
                for k in range(9):
                    coeffs[k]=a*coeffs[k]+(K if sent and t>=k else 0)
                    expanded=sum(
                        (K_history[j]*product_fraction(a_history[j+1:t+1])
                         for j in range(k,t+1) if bits[j]),F(0))
                    assert expanded==coeffs[k]
                assert all(coeffs[k]>=coeffs[k+1] for k in range(8))
                for k1 in range(t+1):
                    for k2 in range(k1+1,t+1):
                        # Direct posterior differences after the later onset
                        # contain only earlier injection terms and decay.
                        expected=sum(
                            (K_history[j]*product_fraction(a_history[j+1:t+1])
                             for j in range(k1,k2) if bits[j]),F(0))
                        assert coeffs[k1]-coeffs[k2]==expected
                P=A*A*P*(1-K)+Q
            checks.append({"model":name,"bits":"".join(map(str,bits)),"pass":True})
    out={"status":"PASS","arithmetic":"exact fractions","event_paths":len(checks),
         "claims":["expanded H equals recursive H","earlier onset monotonicity",
                   "common-history onset difference identity"],
         "random_samples_generated":False,
         "source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (HERE/"invariance_checks.json").write_text(json.dumps(out,indent=2)+"\n",encoding="utf8",newline="\n")
    print(json.dumps(out))


def product_fraction(items):
    value=F(1)
    for item in items:value*=item
    return value


if __name__=="__main__":
    main()
