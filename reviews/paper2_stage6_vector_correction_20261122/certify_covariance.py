"""Exact rational covariance supersolution and uniform contraction certificate."""
from pathlib import Path
import json,hashlib,math
from exact_linear import *

HERE=Path(__file__).resolve().parent


def main():
    data=json.loads((HERE/"model.json").read_text(encoding="utf8"))
    A,C,Q,P0=(matrix(data[name]) for name in ("A","C","Q","P0_prior"))
    R,Z=F(data["R"]),F(data["Z"])
    I=identity(2)
    # Rational supersolution chosen and verified directly, no floating DARE
    # solution or finite history enumeration is the source of this guarantee.
    Pbar=matrix([[".9",".1"],[".1",".9"]])
    allsilent,K0,T0=update(Pbar,C,R+1/Z)
    propagated=add(matmul(matmul(A,allsilent),transpose(A)),Q)
    slack=sub(Pbar,propagated)
    lower=inverse(add(inverse(Q),scale(matmul(transpose(C),C),1/R)))
    checks={
        "observable_det_nonzero":det2([C[0],matmul(C,A)[0]])!=0,
        "initial_covariance_above_Q":psd2(sub(P0,Q)),
        "initial_covariance_below_supersolution":psd2(sub(Pbar,P0)),
        "supersolution_slack_positive_definite":spd2(slack),
        "prior_upper_le_identity":psd2(sub(I,Pbar)),
        "Q_equals_one_twentieth_identity":Q==scale(I,F(1,20)),
        "posterior_lower_ge_one_twenty_fifth_identity":psd2(sub(lower,scale(I,F(1,25)))),
        "posterior_upper_le_identity":psd2(sub(I,allsilent)),
    }
    assert all(checks.values())
    contraction_square=F(19,20)
    M_square=F(25)
    output={
        "status":"PASS","arithmetic":"exact Fraction; no rounded eigenvalues used for acceptance",
        "observability_matrix":encode([C[0],matmul(C,A)[0]]),
        "observability_determinant":str(det2([C[0],matmul(C,A)[0]])),
        "open_loop_eigenvalues":["1.02","0.97"],
        "prior_supersolution":encode(Pbar),
        "supersolution_minus_all_silent_riccati":encode(slack),
        "slack_leading_principal_minor":str(slack[0][0]),"slack_determinant":str(det2(slack)),
        "posterior_covariance_lower":encode(lower),
        "posterior_covariance_upper":encode(allsilent),
        "prior_eigenvalue_upper":"1","Q_eigenvalue_lower":"1/20",
        "posterior_eigenvalue_lower":"1/25",
        "metric_contraction_squared":str(contraction_square),
        "rho_decimal_display":math.sqrt(float(contraction_square)),
        "euclidean_prefactor_squared":str(M_square),"M_decimal_display":5.,
        "product_bound":"||F_t ... F_s||_2 <= 5 * sqrt(19/20)^(t-s+1), s>=1",
        "checks":checks,"performance_random_samples_generated":False,
        "source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (HERE/"covariance_certificate.json").write_text(json.dumps(output,indent=2)+"\n",encoding="utf8",newline="\n")
    print(json.dumps(output,indent=2))


if __name__=="__main__":main()
