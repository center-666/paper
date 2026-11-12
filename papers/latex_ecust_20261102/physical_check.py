"""Independent physical-state reset simulation with paired random numbers.
Events are recomputed separately for the two actual predictors.
The 95% intervals below are normal approximations, not concentration guarantees.
"""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
from pathlib import Path
import hashlib,json
import numpy as np
from vector_core import arr,covariance_update,sym
from experiments import PARAMETERS
P=Path(__file__).resolve().parent

def run(model,policy,seed,N=400000,b=.2):
    rng=np.random.default_rng(seed);k=PARAMETERS['k']
    A,Q,R,Z,P0=(model[key] for key in ('A','Q','R','Z','P0'))
    direction=model['direction']/np.linalg.norm(model['direction'])
    x=rng.standard_normal((N,2))@np.linalg.cholesky(P0).T
    m=[np.zeros((N,2)),np.zeros((N,2))]
    words=[np.zeros(N,dtype=int),np.zeros(N,dtype=int)]
    sign=rng.choice([-1.,1.],N)
    cov={0:P0};nextcov={};cache={}
    for t in range(k+1):
        y=x+rng.standard_normal((N,2))@np.linalg.cholesky(R).T
        u=rng.random(N);nextcov={};cache={}
        for h,prior in cov.items():
            for g in (0,1):
                K,post,_=covariance_update(prior,R if g else R+np.linalg.inv(Z))
                cache[(h,g)]=K
                nextcov[2*h+g]=sym(A@post@A.T+Q)
        for branch in (0,1):
            innov=y-m[branch]
            prob=np.exp(-.5*np.einsum('ni,ij,nj->n',innov,Z,innov))
            send=u>prob
            attack=np.zeros((N,2))
            if branch==1:
                if policy=='persistent_fixed_direction':attack[:]=b*direction
                elif t==k:attack=sign[:,None]*b*direction
            # All updates use the original prior predictor and history.
            for h in cov:
                mask=(words[branch]==h)&send
                m[branch][mask]+=(innov[mask]+attack[mask])@cache[(h,1)].T
            words[branch]=2*words[branch]+send.astype(int)
        if t<k:
            x=x@A.T+rng.standard_normal((N,2))@np.linalg.cholesky(Q).T
            m=[a@A.T for a in m]
        cov=nextcov
    e0=np.sum((x-m[0])**2,axis=1);ea=np.sum((x-m[1])**2,axis=1)
    diff=ea-e0;est=float(diff.mean());se=float(diff.std(ddof=1)/np.sqrt(N))
    return dict(seed=seed,n=N,b=b,estimate=est,standard_error=se,
        normal_95_interval=[est-1.96*se,est+1.96*se],
        healthy_mse_estimate=float(e0.mean()),attacked_mse_estimate=float(ea.mean()))

def main():
    theory=json.loads((P/'vector_data/results.json').read_text())
    rows=[]
    for ci,(name,specific) in enumerate(PARAMETERS['cases'].items()):
        model=arr(dict(PARAMETERS['common'],**specific))
        for pi,policy in enumerate(('persistent_fixed_direction','compensated_rademacher')):
            # Both fixed models have kappa=1; k+1 compensation is after the MSE evaluation.
            assert theory['cases'][name]['constants']['kappa']==1.
            row=run(model,policy,202610170+ci*10+pi)
            exact=next(r['J'] for r in theory['rows'] if r['case']==name and r['policy']==policy and r['b']==.2)
            row.update(case=name,policy=policy,event_tree_J=exact,z_difference=(row['estimate']-exact)/row['standard_error'])
            rows.append(row)
    output=dict(rows=rows,method='Paired state-process reset simulation; separate trigger decisions.',
        note='Normal confidence intervals are diagnostics; no reruns or seed selection.',
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (P/'vector_data/physical_check.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(output,indent=2))

if __name__=='__main__':main()
