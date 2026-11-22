"""Deterministic boundaries: stable modes, covariance metric and vector curvature."""
from pathlib import Path
import json,hashlib
from fractions import Fraction as F
import numpy as np
from exact_linear import *

HERE=Path(__file__).resolve().parent


def main():
    # Generic stable matrices do not imply stable arbitrary switching.
    B1=matrix([[".5","2"],["0",".5"]])
    B2=matrix([[".5","0"],["2",".5"]])
    prod=matmul(B2,B1)
    eig=np.linalg.eigvals(np.array(asfloat(prod)))
    assert max(abs(eig))>1
    # The two-state candidate has an unobservable unstable failure variant.
    badA=matrix([["1.02","0"],["0","1.01"]]);C=matrix([["1","0"]])
    obs=[C[0],matmul(C,badA)[0]]
    assert det2(obs)==0
    Q=scale(identity(2),F(1,20));P=scale(identity(2),F(4,5))
    series=[]
    for t in range(20):
        post,K,T=update(P,C,F(7,10))
        Fmat=matmul(T,badA)
        assert Fmat[1][1]==F(101,100)
        series.append(float(P[1][1]))
        P=add(matmul(matmul(badA,post),transpose(badA)),Q)
    assert series[-1]>series[0]
    # Identical nonzero contamination length alone cannot certify a direction.
    theta1=np.array([.2,.1]);theta2=-theta1
    chosen=theta1
    opposite_gain=float(2*theta2@chosen-chosen@chosen)
    assert opposite_gain<0
    result={"status":"PASS","performance_random_samples_generated":False,
            "generic_individually_stable_switching_pair":{
                "B1":encode(B1),"B2":encode(B2),"each_spectrum":["1/2","1/2"],
                "product":encode(prod),"product_spectral_radius_display":float(max(abs(eig))),
                "not_claimed_as_realizable_filter_matrices":True},
            "unobservable_variant":{"A":encode(badA),"C":encode(C),
                "observability_determinant":"0","unobserved_F_eigenvalue":"101/100",
                "prior_variance_first":series[0],"prior_variance_after19":series[-1]},
            "wrong_point_correction_gain_for_opposite_candidate":opposite_gain,
            "source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (HERE/"counterexample_checks.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf8",newline="\n")
    print(json.dumps(result,indent=2))


if __name__=="__main__":main()
