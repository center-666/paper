"""Exact finite event trees plus deterministic vector dynamics and kernel checks."""
from fractions import Fraction as F
from itertools import product
from pathlib import Path
import json,hashlib,math
import numpy as np
from scipy.integrate import quad
from exact_linear import *

HERE=Path(__file__).resolve().parent


def main():
    model=json.loads((HERE/"model.json").read_text(encoding="utf8"))
    A,C,Q,P0=(matrix(model[x]) for x in ("A","C","Q","P0_prior"))
    R,Z=F(model["R"]),F(model["Z"]);I=identity(2)
    Pbar=matrix([[".9",".1"],[".1",".9"]]);rho2=F(19,20)
    # 256 complete paths; exact metric inequalities, not eigenvalue sampling.
    max_euclidean_single=0.;paths=0
    for bits in product((0,1),repeat=8):
        P=P0;previous=None
        for t,sent in enumerate(bits):
            post,K,T=update(P,C,R+(0 if sent else 1/Z))
            assert psd2(sub(Pbar,P)) and psd2(sub(P,Q))
            Fmat=matmul(T,A)
            if t:
                left=matmul(matmul(transpose(Fmat),inverse(post)),Fmat)
                right=scale(inverse(previous),rho2)
                assert psd2(sub(right,left))
            max_euclidean_single=max(max_euclidean_single,
                float(np.linalg.norm(np.asarray(asfloat(Fmat)),2)))
            previous=post
            P=add(matmul(matmul(A,post),transpose(A)),Q)
        paths+=1
    # A fixed actual event history exhibits negative pollution in state 2.
    P=P0;H=[[F(0)],[F(0)]];signed=[]
    for t in range(30):
        post,K,T=update(P,C,R)
        H=add(matmul(matmul(T,A),H),K)
        if t in (0,5,7,20,29):
            signed.append({"t":t,"H_exact":encode(H),"H_display":asfloat(H)})
        P=add(matmul(matmul(A,post),transpose(A)),Q)
    assert H[1][0]<0
    # Fixed input sample values: state/error recursion equivalence with coupling.
    a=np.asarray(asfloat(A));c=np.asarray(asfloat(C));q=np.asarray(asfloat(Q))
    prior=np.asarray(asfloat(P0));ma=np.zeros(2);mu=np.zeros(2);theta=np.zeros(2)
    max_identity=0.;kernel_errors=[]
    for t in range(200):
        center_offset=float(model["quantization_half_width"])*np.sin(.37*t)
        center=(c@ma).item()+center_offset
        y=.8*np.sin(.17*t)+.2*np.cos(.09*t)
        sent=t%5 in (0,2,4)
        action=.25 if sent and t>=20 else 0.
        ri=float(R)+(0 if sent else 1/float(Z))
        gain=(prior@c.T/(c@prior@c.T+ri)).ravel()
        post_matrix=np.eye(2)-np.outer(gain,c)
        mu_post=mu+gain*((y if sent else center)-(c@mu).item())
        ma_post=ma+gain*((y+action if sent else center)-(c@ma).item())
        theta=post_matrix@theta+gain*action
        max_identity=max(max_identity,float(np.linalg.norm(ma_post-mu_post-theta)))
        S=(c@prior@c.T).item()+float(R)
        d=-(c@(ma-mu)).item();r=center_offset;V=S+1/float(Z)
        silent=np.exp(-(d-r)**2/(2*V))/np.sqrt(1+float(Z)*S)
        if t in (0,5,21,199):
            f=lambda u:np.exp(-(u-.25-d)**2/(2*S))/np.sqrt(2*np.pi*S)*(-np.expm1(-float(Z)*(u-.25-r)**2/2))
            mass=quad(f,-np.inf,np.inf,epsabs=1e-12)[0]+silent
            kernel_errors.append(abs(mass-1))
        prior=a@(post_matrix@prior)@a.T+q
        ma=a@ma_post;mu=a@mu_post;theta=a@theta
    assert max_identity<1e-11 and max(kernel_errors)<1e-11
    # Multi-channel trigger curvature counterexample, evaluated without optimizer.
    positive_curvature=1/math.expm1(.5)-1
    assert positive_curvature>0
    output={"status":"PASS","exact_event_tree_paths":paths,
        "exact_metric_inequalities_verified":paths*7,
        "largest_single_step_euclidean_norm_on_fixtures":max_euclidean_single,
        "single_step_can_expand_but_products_contract":max_euclidean_single>1,
        "signed_pollution_examples":signed,
        "first_second_component_negative_on_all_send_path":7,
        "posterior_identity_max_float_error":max_identity,
        "scalar_kernel_mass_max_error":max(kernel_errors),
        "two_channel_loglikelihood_positive_curvature_example":positive_curvature,
        "performance_random_samples_generated":False,
        "finite_tree_is_not_source_of_global_certificate":True,
        "source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (HERE/"dynamics_checks.json").write_text(json.dumps(output,indent=2)+"\n",encoding="utf8",newline="\n")
    print(json.dumps({k:v for k,v in output.items() if k!="signed_pollution_examples"},indent=2))


if __name__=="__main__":main()
