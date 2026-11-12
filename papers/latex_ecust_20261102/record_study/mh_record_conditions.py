"""Same-model record ablation for the existing one-step MH attack.

No imports from the manuscript's numerical modules. The overlap integral uses
Gauss-Legendre quadrature on a whitened finite square. Values are floating-point
approximations, not rigorous interval certificates. Cutoff-log equality is an
analytic consequence of detailed balance, not an empirical TV estimate.
"""
from pathlib import Path
import csv
import hashlib
import json
import math
import platform
import sys

import numpy as np
from scipy.special import ndtr, roots_legendre

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FROZEN = ROOT if (ROOT/'vector_data/parameters.json').exists() else ROOT/'latex_detail_audit_20261019'
CONFIG = {
    'target_k': 4, 'amplitudes': [0.025, 0.05, 0.1, 0.2],
    'orders_per_dimension': [128, 256, 512], 'box_half_width': 9.0,
    'attack_after_target': 'zero', 'b_ref': 0.2,
    'integral_relative_change_tolerance': 0.002,
    'description': 'Fixed original S/U cases; target-time single MH transition only.',
}

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def sym(M):
    return (M+M.T)/2

def gain_post(P, noise):
    K = np.linalg.solve((P+noise).T, P.T).T
    return K, sym(P-K@P)

def silent_base(P, R, Z):
    _, a = np.linalg.slogdet(Z)
    _, b = np.linalg.slogdet(np.linalg.inv(Z)+P+R)
    return float(np.exp(-0.5*(a+b)))

def enumerate_prefixes(model, k):
    A,R,Z,Q = [model[x] for x in ['A','R','Z','Q']]
    nodes = [((), 1.0, model['P0'])]
    for _ in range(k):
        nxt=[]
        for hist, mass, P in nodes:
            s = silent_base(P,R,Z)
            for gamma, prob in [(0,s),(1,1-s)]:
                _,post = gain_post(P,R if gamma else R+np.linalg.inv(Z))
                nxt.append((hist+(gamma,),mass*prob,sym(A@post@A.T+Q)))
        nodes=nxt
    assert abs(sum(x[1] for x in nodes)-1)<1e-12
    return nodes

def overlap_mass(S, Z, v, b, order, width):
    # z=Lx, u=z-bv/2; include the Jacobian in the normal density in x.
    nodes,weights=roots_legendre(order)
    nodes=nodes*width;weights=weights*width
    xx,yy=np.meshgrid(nodes,nodes,indexing='ij')
    x=np.stack([xx,yy],axis=-1)
    L=np.linalg.cholesky(S)
    z=x@L.T
    shift=b*v/2
    a=np.linalg.solve(L,shift)
    f=[]
    for sign in [-1,1]:
        shifted_x=x+sign*a
        u=z+sign*shift
        gaussian=np.exp(-0.5*np.sum(shifted_x**2,axis=-1))/(2*np.pi)
        trigger=-np.expm1(-0.5*np.einsum('...i,ij,...j->...',u,Z,u))
        f.append(gaussian*trigger)
    product=weights[:,None]*weights[None,:]
    overlap=float(np.sum(product*np.minimum(f[0],f[1])))
    mass=float(np.sum(product*f[0]))
    tail=float(sum(ndtr(-width-a)+ndtr(a-width)))
    return overlap,mass,tail

def main():
    params=json.loads((FROZEN/'vector_data/parameters.json').read_text(encoding='utf-8'))
    prior=json.loads((FROZEN/'vector_data/results.json').read_text(encoding='utf-8'))
    source_before={f:sha(FROZEN/f) for f in ['vector_data/parameters.json','vector_data/results.json','vector_proof.tex','theory.tex']}
    (HERE/'parameters.json').write_text(json.dumps(dict(study=CONFIG,original_parameters=params),indent=2)+'\n',encoding='utf-8')
    prefix_rows=[];summary=[];checks=[]
    for case,specific in params['cases'].items():
        model={k:np.asarray(v,dtype=float) for k,v in dict(params['common'],**specific).items()}
        A,R,Z,Q=[model[x] for x in ['A','R','Z','Q']]
        v=model['direction']/np.linalg.norm(model['direction'])
        c=prior['cases'][case]['constants']
        prefixes=enumerate_prefixes(model,CONFIG['target_k'])
        for b in CONFIG['amplitudes']:
            J=event_tv=witness=lower_J=0.0
            max_rel=mass_error=tail_max=0.0
            for history,mass,P in prefixes:
                S=P+R;K,post=gain_post(P,R)
                s=silent_base(P,R,Z);p=1-s
                nxt=silent_base(sym(A@post@A.T+Q),R,Z)
                kv=K@v
                H=.5*A.T@np.linalg.solve(np.linalg.inv(Z)+A@post@A.T+Q+R,A)
                exponent=b*b*float(kv@H@kv)
                deficit=-np.expm1(-exponent)
                integrals=[]
                for order in CONFIG['orders_per_dimension']:
                    integral,checkmass,tail=overlap_mass(S,Z,v,b,order,CONFIG['box_half_width'])
                    integrals.append(integral)
                    mass_error=max(mass_error,abs(checkmass-p));tail_max=max(tail_max,tail)
                relative=abs(integrals[-1]-integrals[-2])/integrals[-1]
                max_rel=max(max_rel,relative)
                acceptance=integrals[-1]
                # Existing analytic derivative bound: A_h >= p_h-b F_1,h/2.
                F1=math.sqrt(2/math.pi)*(math.sqrt(float(v@np.linalg.solve(S,v)))+
                    s*math.sqrt(float(v@(np.linalg.inv(S)+Z)@v)))
                acceptance_lower=max(0.0,p-b*F1/2)
                j=b*b*mass*acceptance*float(kv@kv)
                tv=mass*acceptance*nxt*deficit
                wg=mass*acceptance*deficit
                J+=j;event_tv+=tv;witness+=wg
                lower_J+=b*b*mass*acceptance_lower*float(kv@kv)
                assert 0<acceptance<=p+1e-11
                assert acceptance>=acceptance_lower-1e-10
                prefix_rows.append(dict(case=case,b=b,history=''.join(map(str,history)),
                    healthy_prefix_mass=mass,target_send_probability=p,
                    accepted_mass_128=integrals[0],accepted_mass_256=integrals[1],accepted_mass_512=integrals[2],
                    relative_change_256_to_512=relative,accepted_mass_analytic_lower_float=acceptance_lower,
                    next_silence_base=nxt,next_bias_exponent=exponent,
                    damage_contribution=j,event_tv_contribution=tv,witness_contribution=wg))
            score_certificate=witness/c['q']
            tv_bound=c['C_record']*event_tv
            assert J>0 and event_tv>0 and lower_J>0
            assert J<=score_certificate+1e-12 and J<=tv_bound+1e-12
            assert max_rel<CONFIG['integral_relative_change_tolerance']
            assert mass_error<1e-11 and tail_max<1e-16
            row=dict(case=case,k=CONFIG['target_k'],b=b,
                cutoff_full_log_TV_analytic=0.0,cutoff_event_word_TV_analytic=0.0,
                damage_J_float=J,damage_over_b_squared=J/(b*b),
                analytic_damage_lower_float=lower_J,
                extended_event_word_TV_float=event_tv,
                last_event_TV_float=event_tv,
                extended_full_log_TV_lower_float=event_tv,
                weighted_next_silence_gap_float=witness,
                population_score_certificate_float=score_certificate,
                population_score_certificate_over_J=score_certificate/J,
                event_TV_damage_upper_float=tv_bound,
                damage_percent_of_healthy_mse=100*J/prior['cases'][case]['healthy_mse'],
                max_prefix_overlap_relative_change_256_to_512=max_rel,
                max_send_mass_integration_error=mass_error,
                gaussian_box_tail_upper_float=tail_max)
            summary.append(row)
            print(json.dumps(row),flush=True)
    for filename,rows in [('results.csv',summary),('prefix_integrals.csv',prefix_rows)]:
        with (HERE/filename).open('w',encoding='utf-8',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    assert source_before=={f:sha(FROZEN/f) for f in source_before}
    result=dict(passed=True,date='2026-10-19',parameters=CONFIG,rows=summary,
        source_sha256=source_before,script_sha256=sha(Path(__file__)),python=platform.python_version(),
        numpy=np.__version__,no_monte_carlo=True,rigorous_interval_validation=False,
        numerical_modules_of_original_paper_imported=False,
        limits=['Cutoff-law equality is analytic, not inferred from numerical samples.',
                'Only extended event TV is evaluated; extended full-log TV is bounded below by it.',
                'Last-event TV equals event-word TV for this target-only attack; this experiment does not prove historical information necessary.',
                'Quadrature convergence and a tail bound do not provide a rigorous bound on the discretization error.',
                'Analytic lower bounds are evaluated in ordinary floating point.',
                'No claim of superiority to other attacks or globally optimal bounds.'])
    (HERE/'results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':
    main()
