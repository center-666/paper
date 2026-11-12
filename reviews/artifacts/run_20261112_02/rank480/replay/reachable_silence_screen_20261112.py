"""Exact-rank and independent Gaussian checks for a scoped damage-certificate extension."""
from fractions import Fraction as F
from itertools import product
from pathlib import Path
import csv
import hashlib
import json
import math
import shutil
import numpy as np
from scipy.special import roots_hermitenorm

ROOT=Path(__file__).resolve().parents[1]
PLAN=ROOT/'simulation/reachable_silence_plan_20261112.json'
OUT=ROOT/'simulation/checks/2026-11-12_reachable_silence_screen_v2'


def exact(x):return [[F(str(v)) for v in row] for row in x]
def eye(n):return [[F(int(i==j)) for j in range(n)] for i in range(n)]
def trans(A):return list(map(list,zip(*A)))
def add(A,B):return [[a+b for a,b in zip(r,s)] for r,s in zip(A,B)]
def neg(A):return [[-v for v in r] for r in A]
def mul(A,B):
    if not B or not B[0]:return [[] for _ in A]
    return [[sum(a*b for a,b in zip(r,c)) for c in zip(*B)] for r in A]
def inv(A):
    n=len(A);T=[list(A[i])+eye(n)[i] for i in range(n)]
    for j in range(n):
        pivot=next(i for i in range(j,n) if T[i][j])
        T[j],T[pivot]=T[pivot],T[j]
        v=T[j][j];T[j]=[x/v for x in T[j]]
        for i in range(n):
            if i!=j:
                v=T[i][j];T[i]=[x-v*y for x,y in zip(T[i],T[j])]
    return [r[n:] for r in T]
def rank(A):
    T=[r.copy() for r in A]
    if not T or not T[0]:return 0
    i=0
    for j in range(len(T[0])):
        p=next((k for k in range(i,len(T)) if T[k][j]),None)
        if p is None:continue
        T[i],T[p]=T[p],T[i];v=T[i][j];T[i]=[x/v for x in T[i]]
        for k in range(i+1,len(T)):
            v=T[k][j];T[k]=[x-v*y for x,y in zip(T[k],T[i])]
        i+=1
        if i==len(T):break
    return i
def flt(A):return np.asarray([[float(x) for x in r] for r in A],float)


def history(A,C,Q,P0,R,Z,h):
    n=len(A);P=P0;B=[[] for _ in range(n)]
    for bit in h:
        Ri=R if bit else add(R,inv(Z))
        K=mul(mul(P,trans(C)),inv(add(mul(mul(C,P),trans(C)),Ri)))
        M=add(eye(n),neg(mul(K,C)))
        B=mul(M,mul(A,B))
        if bit:
            B=[row+[-v for v in kr] for row,kr in zip(B,K)]
        Pplus=add(P,neg(mul(mul(K,C),P)))
        P=add(mul(mul(A,Pplus),trans(A)),Q)
    return Pplus,B


def gaussian_batch(A,C,Q,R,Z,P,L):
    n=len(A);m=len(C);Ap=[np.linalg.matrix_power(A,k) for k in range(L+1)]
    G=np.vstack([C@Ap[k] for k in range(1,L+1)])
    V=np.zeros((L*m,L*m))
    for i in range(1,L+1):
        for j in range(1,L+1):
            S=Ap[i]@P@Ap[j].T
            for r in range(1,min(i,j)+1):S+=Ap[i-r]@Q@Ap[j-r].T
            V[(i-1)*m:i*m,(j-1)*m:j*m]=C@S@C.T+(R if i==j else 0)
    Zb=np.kron(np.eye(L),Z)
    H=0.5*G.T@np.linalg.solve(V+np.linalg.inv(Zb),G)
    s=math.exp(-0.5*np.linalg.slogdet(np.eye(L*m)+V@Zb)[1])
    return s,(H+H.T)/2,G,V,Zb


def gaussian_recursive(A,C,Q,R,Z,P,d,L):
    prob=1.;I=np.eye(len(A))
    for _ in range(L):
        P=A@P@A.T+Q;d=A@d;S=C@P@C.T+R
        W=np.linalg.inv(S+np.linalg.inv(Z))
        prob*=math.exp(-0.5*np.linalg.slogdet(np.eye(len(C))+S@Z)[1]-0.5*d@C.T@W@C@d)
        K=P@C.T@W
        d=(I-K@C)@d;P=P-K@C@P
    return prob


def direct_hermite(mean,V,Z,order=20):
    d=len(mean);xs,ws=roots_hermitenorm(order)
    indices=np.asarray(list(product(range(order),repeat=d)),int)
    samples=xs[indices]@np.linalg.cholesky(V).T+mean
    weights=np.prod(ws[indices]/math.sqrt(2*math.pi),axis=1)
    return float(weights@np.exp(-0.5*np.einsum('bi,ij,bj->b',samples,Z,samples)))


def main():
    OUT.mkdir(parents=True,exist_ok=False)
    plan=json.loads(PLAN.read_text(encoding='utf-8'))
    shutil.copy2(PLAN,OUT/'plan.json');shutil.copy2(__file__,OUT/Path(__file__).name)
    qexact=exact(plan['Q']);rng=np.random.default_rng(plan['numeric_seed'])
    rows=[];summary=[];batch_recursive_error=0.;quadrature_error=0.;lower_bound_error=0.;quadrature_convergence=[]
    for model in plan['fixed_models']:
        A,C,P0=map(exact,(model['A'],model['C'],model['P0']))
        n=len(A);m=len(C)
        R=[[F(str(plan['measurement_noise_variance']))*v for v in r] for r in eye(m)]
        Z=[[F(str(plan['trigger_Z_scalar']))*v for v in r] for r in eye(m)]
        af,cf,qf,rf,zf=map(flt,(A,C,qexact,R,Z))
        O=C+mul(C,A)
        model_summary={'model':model['name'],'rank_C':rank(C),'rank_observability':rank(O),'targets':[]}
        for k in plan['target_k']:
            target_rows=[]
            for L in plan['lookahead_L']:
                valid=True;max_radius=0.;min_h=float('inf');max_w=0.;p_traces=[];bad=[]
                for bits in product((0,1),repeat=k+1):
                    P,B=history(A,C,qexact,P0,R,Z,bits);r=rank(B)
                    power=eye(n);G=[]
                    for _ in range(L):power=mul(power,A);G+=mul(C,power)
                    seen=rank(mul(G,B));ok=(seen==r);valid&=ok
                    if not ok:bad.append(''.join(map(str,bits)))
                    pf,bf=flt(P),flt(B)
                    s,H,Gf,V,Zb=gaussian_batch(af,cf,qf,rf,zf,pf,L)
                    p_traces.append(float(np.trace(pf)));max_w=max(max_w,1/s)
                    if r:
                        U=np.linalg.svd(bf,full_matrices=False)[0][:,:r]
                        hmin=float(np.linalg.eigvalsh(U.T@H@U)[0])
                        min_h=min(min_h,hmin)
                        radius=sum(float(np.linalg.norm(bf[:,j:j+m],2)) for j in range(0,bf.shape[1],m))
                        max_radius=max(max_radius,radius)
                        for _ in range(4):
                            coeff=rng.normal(size=bf.shape[1]);coeff/=max(1,np.linalg.norm(coeff))
                            d=bf@coeff
                            batch=s*math.exp(-d@H@d)
                            recursive=gaussian_recursive(af,cf,qf,rf,zf,pf,d,L)
                            batch_recursive_error=max(batch_recursive_error,abs(batch-recursive))
                            if ok:lower_bound_error=max(lower_bound_error,max(0,hmin*(d@d)-d@H@d))
                    else:hmin=0.;radius=0.
                    rows.append({'model':model['name'],'k':k,'L':L,'history':''.join(map(str,bits)),
                                 'reachable_rank':r,'observed_reachable_rank':seen,'restricted_coercivity':ok,
                                 'normal_silence_probability':s,'reachable_min_H':hmin,'unit_peak_bias_radius':radius})
                record={'k':k,'L':L,'all_histories_pass':bool(valid),'failed_histories':bad,
                        'min_restricted_H':min_h,'bias_radius_for_b1':max_radius,
                        'max_inverse_normal_probability':max_w}
                if valid and min_h>0 and max_radius>0:
                    q=-math.expm1(-min_h*max_radius**2)/(max_radius**2)
                    record.update(q_at_reference_b1=q,marked_damage_upper_constant=max_w/q+max(p_traces)-min(p_traces))
                target_rows.append(record)
            minimum=next((r['L'] for r in target_rows if r['all_histories_pass']),None)
            model_summary['targets'].append({'k':k,'minimum_tested_L':minimum,'details':target_rows})
        # Independent direct integration of a fixed posterior, one and two future outputs.
        for L in (1,2):
            s,H,G,V,Zb=gaussian_batch(af,cf,qf,rf,zf,flt(P0),L)
            d=np.array([.25,-.2]);quad20=direct_hermite(G@d,V,Zb,order=20)
            quad=direct_hermite(G@d,V,Zb,order=32)
            quadrature_convergence.append({'model':model['name'],'L':L,
                'order20_error':abs(quad20-s*math.exp(-d@H@d)),
                'order32_error':abs(quad-s*math.exp(-d@H@d))})
            quadrature_error=max(quadrature_error,abs(quad-s*math.exp(-d@H@d)))
        summary.append(model_summary)
    assert batch_recursive_error<1e-11,batch_recursive_error
    assert quadrature_error<1e-9,quadrature_error
    assert lower_bound_error<1e-11,lower_bound_error
    with (OUT/'history_ranks.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    result={'passed':True,'new_physical_trajectories':0,'history_window_cases':len(rows),
            'rank_arithmetic':'exact rational Gaussian elimination, not floating-point rank thresholds',
            'max_batch_recursive_probability_error':batch_recursive_error,
            'max_direct_Gauss_Hermite_probability_error':quadrature_error,
            'max_restricted_quadratic_lower_bound_error':lower_bound_error,
            'models':summary,'quadrature_convergence':quadrature_convergence,
            'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'plan_sha256':hashlib.sha256(PLAN.read_bytes()).hexdigest(),
            'novelty_confirmed':False,'scope':'diagnostics support the conditional lemma, not a proof of publication novelty or a detector performance study'}
    (OUT/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='models'},ensure_ascii=False,indent=2))
    print(json.dumps([{'model':x['model'],'rank_observability':x['rank_observability'],
                       'minimum_tested_L_by_k':[(y['k'],y['minimum_tested_L']) for y in x['targets']]} for x in summary],indent=2))


if __name__=='__main__':main()
