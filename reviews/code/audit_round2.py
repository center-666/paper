"""Independent, finite-model theorem audit. No original result is overwritten.

Run from repository root with .venv/Scripts/python.exe -X utf8
reviews/code/audit_round2.py --case CASE [--output NEW_DIRECTORY].
Each case runs independently. All-case mode is a convenience, not replication.
"""
from __future__ import annotations
import argparse
import csv
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import platform
import sys
import numpy as np
import scipy
from scipy.integrate import quad
from scipy.special import roots_hermitenorm

ROOT = Path(__file__).resolve().parents[2]
CASES = ('rank480', 'atoms16', 'erased', 'near_null', 'nonlinear',
         'rare', 'collision', 'mixture', 'causal_geometry')


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_old(name):
    p = ROOT / 'simulation' / name
    spec = importlib.util.spec_from_file_location(name.replace('.', '_'), p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def old_assets():
    dirs = [ROOT / 'simulation/checks/2026-11-12_reachable_silence_screen',
            ROOT / 'simulation/checks/2026-11-12_reachable_silence_screen_v2',
            ROOT / 'simulation/checks/2026-11-12_reachable_silence_atom_audit']
    return {p.relative_to(ROOT).as_posix(): digest(p)
            for d in dirs if d.exists() for p in sorted(d.rglob('*')) if p.is_file()}


def rank480(out):
    old = load_old('reachable_silence_screen_20261112.py')
    old.OUT = out / 'replay'
    old.main()
    result = json.loads((old.OUT / 'results.json').read_text(encoding='utf-8'))
    # Compare every rank/history flag, not only the total count.
    source = ROOT / 'simulation/checks/2026-11-12_reachable_silence_screen_v2'
    with (source / 'history_ranks.csv').open(encoding='utf-8-sig', newline='') as f:
        original = list(csv.DictReader(f))
    with (old.OUT / 'history_ranks.csv').open(encoding='utf-8-sig', newline='') as f:
        replay = list(csv.DictReader(f))
    keys = ('model', 'k', 'L', 'history', 'reachable_rank',
            'observed_reachable_rank', 'restricted_coercivity')
    assert [[r[k] for k in keys] for r in original] == [[r[k] for k in keys] for r in replay]
    return {'category': 'exact rational algebra plus numerical integration',
            'all_480_rank_rows_match': True,
            'physical_trajectories': 0,
            'max_quadrature_error': result['max_direct_Gauss_Hermite_probability_error'],
            'not_a_proof': True}


def atoms16(out):
    old = load_old('reachable_silence_atom_audit_20261112.py')
    old.OUT = out / 'replay'
    old.main()
    with (old.SOURCE.parent / '2026-11-12_reachable_silence_atom_audit/exact_target_damage.csv').open(encoding='utf-8-sig', newline='') as f:
        original = list(csv.DictReader(f))
    with (old.OUT / 'exact_target_damage.csv').open(encoding='utf-8-sig', newline='') as f:
        replay = list(csv.DictReader(f))
    assert original == replay
    return {'category': 'closed Gaussian formulas, evaluated in floating point',
            'all_16_rows_match': True, 'physical_trajectories': 0,
            'limitation': 'k=0 only; no nonlinear or adaptive history policy in the original 16 cases'}


def scalar(b=.25, A=.9):
    p, r, z = .5, .1, 2.
    gain = p / (p + r)
    ps = 1 / math.sqrt(1 + z * (p + r))
    post = p * r / (p + r)
    vf = A*A*post + .02 + r
    s = 1 / math.sqrt(1 + z*vf)
    H = .5*A*A / (vf + 1/z)
    B = gain  # reference peak = 1
    q = -math.expm1(-H*B*B) / (B*B) if H else 0.
    return dict(p=p, r=r, z=z, gain=gain, ps=ps, post=post,
                s=s, H=H, B=B, q=q, b=b, A=A)


def erased(out):
    # n=2, m=2, A=diag(0,.95), C=I, P0=diag(.5,.4), Q=.02 I,
    # R=.1 I, Z=2 I. Send at t=0, then attack along the first coordinate.
    p_send = 1 - 1/math.sqrt((1+2*.6)*(1+2*.5))
    b=.25
    J=p_send*(.5/.6*b)**2
    assert J > 0
    return {'category':'analytic counterexample to removal of the visibility assumption',
            'parameters': {'A':[[0,0],[0,.95]], 'C':[[1,0],[0,1]],
                           'P0':[[.5,0],[0,.4]], 'Q':[[.02,0],[0,.02]],
                           'R':[[.1,0],[0,.1]], 'Z':[[2,0],[0,2]], 'k':0, 'b':b},
            'policy':'a0=private_sign*b*e1 if gamma0=1; all other actions zero',
            'J':J, 'marked_TV':0., 'any_L_ge_1':True,
            'violated_condition':'ker G_L intersects range K_1(P0) in e1',
            'disproves_stated_conditional_theorem':False,
            'full_payload_log_TV_claimed_zero':False}


def near_null(out):
    rows=[]
    for a in (.5,.1,.01,.001,.0001,0.):
        v=scalar(A=a); d=v['gain']*v['b']
        J=(1-v['ps'])*d*d
        tv=(1-v['ps'])*v['s']*(-math.expm1(-v['H']*d*d))
        rows.append({'A_observed_eigenvalue':a, 'restricted_rank_pass':a!=0,
                     'J':J,'TV':tv,'J_over_TV':J/tv if tv else None,
                     'restricted_H':v['H']})
    return {'category':'conditioning stress test, not a counterexample at fixed model',
            'rows':rows,'conclusion':'no constant uniform over approaching-null system parameters'}


def nonlinear(out):
    v=scalar(); b=v['b']; S=v['p']+v['r']; K=v['gain']
    def fs(y):
        return math.exp(-y*y/(2*S))/math.sqrt(2*math.pi*S)*(-math.expm1(-v['z']*y*y/2))
    mass,err0=quad(fs,-b,b,epsabs=1e-13)
    m2,err2=quad(lambda y:y*y*fs(y),-b,b,epsabs=1e-13)
    m4,err4=quad(lambda y:y**4*fs(y),-b,b,epsabs=1e-13)
    loss,errl=quad(lambda y:fs(y)*(-math.expm1(-v['H']*K*K*y*y)),-b,b,epsabs=1e-13)
    J=K*K*m2
    tv=v['s']*loss
    # k=0 has two covariance labels, take the smaller future normal silence prob.
    p_silent=1/(1/v['p']+1/(v['r']+1/v['z']))
    s0=1/math.sqrt(1+v['z']*(v['A']**2*p_silent+.02+v['r']))
    M=1/min(s0,v['s']); omega=p_silent-v['post']
    upper=(M/v['q']+omega)*tv
    assert J <= upper + 1e-12
    cond_var=v['post']+K*K*m2/mass
    cumulant4=K**4*(m4/mass-3*(m2/mass)**2)
    assert cond_var > v['post'] and abs(cumulant4)>1e-10
    return {'category':'adaptive quadrature for a legal measurement-dependent nonlinear attack',
            'policy':'if gamma0=1 and abs(y0)<=b: a0=-y0; otherwise a0=0',
            'permissions':'uses only current truly sent y0; no unsent measurement/state',
            'parameters':v,'J':J,'TV':tv,'certificate_upper':upper,
            'maximum_reported_quad_error':max(err0,err2,err4,errl),
            'received_zero_atom_mass':mass,'reported_P_send':v['post'],
            'true_variance_given_received_zero_and_send':cond_var,
            'conditional_fourth_cumulant_nonzero':cumulant4,
            'conclusion':'extended true-history Gaussian is valid; received-log posterior need not be Gaussian'}


def rare(out):
    v=scalar(); rows=[]
    for amp in (.25,1.,4.,16.,64.):
        prob=.1/max(1.,amp*amp)
        J=(1-v['ps'])*prob*v['gain']**2*amp**2
        tv=(1-v['ps'])*prob*v['s']*(-math.expm1(-v['H']*v['gain']**2*amp**2))
        rows.append({'amplitude':amp,'private_attack_probability':prob,'J':J,'TV':tv,
                     'J_over_TV':J/tv,'legal_for_fixed_bref1':amp<=1})
    return {'category':'randomized rare-large-attack stress test', 'rows':rows,
            'conclusion':'bounded second moment alone cannot replace a fixed pathwise peak for a linear-TV bound',
            'disproves_fixed_reference_peak_theorem':False}


def collision_eval(order, attack):
    P0=.5; R=.1; Z=2.; b=.25
    xs,ws=roots_hermitenorm(order)
    ix=np.indices((order,order)).reshape(2,-1).T
    yy=xs[ix]@np.linalg.cholesky(np.array([[P0+R,P0],[P0,P0+R]])).T
    ww=np.prod(ws[ix]/math.sqrt(2*math.pi),axis=1)
    y0,y1=yy.T
    # Given both physical measurements, x is Gaussian, independently of event coins.
    pall=1/(1/P0+2/R); muall=pall/R*(y0+y1)
    law={}; mse=0.; bias2=0.; cov=0.; energy=0.; weighted=0.; hist={}
    for g0 in (0,1):
        pp0=1/(1/P0+1/(R if g0 else R+1/Z))
        K0=P0/(P0+R)
        a0=b*np.tanh(y0) if attack and g0 else np.zeros_like(y0)
        m1=K0*(y0+a0) if g0 else np.zeros_like(y0)
        D0=-K0*a0
        prob0=np.exp(-Z*y0*y0/2)
        prob0=prob0 if not g0 else 1-prob0
        for g1 in (0,1):
            # Exact rational key deliberately merges 01 and 10; histories remain separate diagnostics.
            rf=Fraction(1,10); rz=rf+Fraction(1,2)
            pf=1/(Fraction(2)+1/(rf if g0 else rz)+1/(rf if g1 else rz))
            pp1=float(pf); K1=pp0/(pp0+R)
            Kbranch=pp0/(pp0+(R if g1 else R+1/Z))
            a1=-.5*b*np.tanh(y1-m1) if attack and g1 else np.zeros_like(y0)
            m2=m1+K1*(y1+a1-m1) if g1 else m1
            D1=(1-Kbranch)*D0-g1*K1*a1
            p_s=np.exp(-Z*(y1-m1)**2/2)
            pw=ww*prob0*(p_s if not g1 else 1-p_s)
            # Integrate future event using the true Gaussian law given both raw y's.
            future=1/math.sqrt(1+Z*(pall+R))*np.exp(-.5*(muall-m2)**2/(pall+R+1/Z))
            s=1/math.sqrt(1+Z*(pp1+R))
            H=.5/(pp1+R+1/Z)
            for y in (0,1):
                law[(str(pf),y)]=law.get((str(pf),y),0.)+float(pw@(future if y else 1-future))
            hist[f'{g0}{g1}']=float(pw.sum())
            mse+=float(pw@(pall+(muall-m2)**2))
            bias2+=float(pw@(D1**2)); cov+=pp1*float(pw.sum())
            energy+=float(pw@(-np.expm1(-H*D1**2)))
            weighted+=float(pw@future)/s
    return dict(law=law,mse=mse,bias2=bias2,cov=cov,energy=energy,weighted=weighted,hist=hist)


def collision(out):
    rows=[]
    for order in (48,72,104):
        normal=collision_eval(order,False); attacked=collision_eval(order,True)
        tv=.5*sum(abs(attacked['law'][k]-normal['law'][k]) for k in normal['law'])
        err=abs((attacked['mse']-normal['mse'])-(attacked['bias2']+attacked['cov']-normal['cov']))
        witnesserr=abs((normal['weighted']-attacked['weighted'])-attacked['energy'])
        rows.append({'order_per_dimension':order,'TV_numerical_integration':tv,
                     'J_physical_integral':attacked['mse']-normal['mse'],
                     'bias_square':attacked['bias2'],'covariance_change':attacked['cov']-normal['cov'],
                     'physical_vs_decomposition_error':err,'normalized_witness_identity_error':witnesserr,
                     'probability_mass_error':abs(sum(attacked['law'].values())-1),
                     'normal_history_probabilities':normal['hist'],'attack_history_probabilities':attacked['hist']})
    assert rows[-1]['physical_vs_decomposition_error']<1e-10
    assert rows[-1]['normalized_witness_identity_error']<1e-10
    assert abs(rows[-1]['TV_numerical_integration']-rows[-2]['TV_numerical_integration'])<1e-10
    return {'category':'2-dimensional Gauss-Hermite physical-noise integration; not exact probability arithmetic',
            'parameters':{'A':1,'C':1,'Q':0,'P0':.5,'R':.1,'Z':2,'k':1,'L':1,'b':.25},
            'collision':'P(01)=P(10)=3/41 exactly',
            'policy':'a0=b*tanh(y0) on send; a1=-b/2*tanh(y1-m1) on send',
            'rows':rows,'merged_marked_atoms':len(normal['law']),
            'conclusion':'history weights change, but exact-P normalization prevents signed energy cancellation'}


def mixture(out):
    v=scalar(); rows=[]
    for plusprob in (0.,.1,.5,.9,1.):
        # Opposite biases have the same strictly nonnegative quadratic energy.
        D=v['gain']*v['b']; J=(1-v['ps'])*D*D
        deficit=(1-v['ps'])*(-math.expm1(-v['H']*D*D))
        tv=v['s']*deficit
        rows.append({'private_plus_probability':plusprob,'J':J,'TV':tv,'normalized_deficit':deficit})
    return {'category':'closed-form mixture non-cancellation test','rows':rows,
            'conclusion':'symmetric mixtures cancel first moments, not this positive quadratic witness'}


def causal_geometry(out):
    # The correlated, globally unobservable model from the old 480-rank plan.
    old=load_old('reachable_silence_screen_20261112.py')
    A=np.diag([.9,.95]); C=np.array([[1.,0.]])
    P=np.array([[.5,.1],[.1,.4]]); Q=.02*np.eye(2); R=.1; R0=.6
    G=C@A; K=P@C.T/(float((C@P@C.T).item())+R)
    v=A@K
    u=[]; gains=[]; c1=0.
    for g0 in (0,1):
        Kg=P@C.T/(float((C@P@C.T).item())+(R if g0 else R0))
        pp=P-Kg@C@P; prior=A@pp@A.T+Q
        for g1 in (0,1):
            Kb=prior@C.T/(float((C@prior@C.T).item())+(R if g1 else R0))
            if g0:
                u.append((np.eye(2)-Kb@C)@v)
                if g1: c1=abs(float((G@u[-1]).item()))
            if g1:gains.append(Kb)
        if g0:
            vf=float((C@prior@C.T).item())+R
            pmin=1/math.sqrt(1+2*vf)*math.exp(-.5*float((C@v).item())**2/(vf+.5))
    c0=abs(float((G@u[0]).item()))
    dmin=min(abs(float((G@kg).item())) for kg in gains)
    umax=max(np.linalg.norm(uv) for uv in u); kmax=max(np.linalg.norm(kg) for kg in gains)
    ca=1/(pmin*c0*c0)
    coercivity=2*umax**2*ca+4*kmax**2/(dmin*dmin)*(1+c1*c1*ca)
    _,B=old.history(old.exact(A),old.exact(C),old.exact(Q),old.exact(P),[[Fraction(1,10)]],[[Fraction(2)]],(1,1))
    rankB=old.rank(B); rankGB=old.rank(old.mul(old.exact(G),B))
    assert rankB==2 and rankGB==1 and pmin>0 and c0>0 and dmin>0
    # The alternative expectation argument gives a finite record certificate
    # despite the failure of the original pathwise rank criterion.
    beta_min=math.inf; zmax=0.; max_w=0.; traces=[]; histories=[]
    for g0 in (0,1):
        for g1 in (0,1):
            ph,bh=old.history(old.exact(A),old.exact(C),old.exact(Q),old.exact(P),
                              [[Fraction(1,10)]],[[Fraction(2)]],(g0,g1))
            ph=old.flt(ph);bh=old.flt(bh)
            V=float((C@(A@ph@A.T+Q)@C.T).item())+R
            beta_min=min(beta_min,.5/(V+.5));max_w=max(max_w,math.sqrt(1+2*V))
            zh=G@bh
            radius=float(np.abs(zh).sum()) if bh.shape[1] else 0.
            zmax=max(zmax,radius);traces.append(float(np.trace(ph)))
            histories.append({'history':f'{g0}{g1}','P':ph.tolist(),'B':bh.tolist(),
                              'visible_peak_radius_bref1':radius})
    qz=-math.expm1(-beta_min*zmax*zmax)/(zmax*zmax)
    ctv=coercivity*max_w/qz+max(traces)-min(traces)
    return {'category':'analytic non-necessity example; code evaluates proof constants only',
            'parameters':{'A':A.tolist(),'C':C.tolist(),'P0':P.tolist(),'Q':Q.tolist(),'R':R,'Z':2.,'k':1,'L':1,'bref':1.},
            'history_11_range_rank':rankB,'history_11_visible_rank':rankGB,
            'conditional_next_silence_probability_lower_bound':pmin,
            'c0':c0,'c1':c1,'dmin':dmin,'C_causal_energy':coercivity,
            'beta_min':beta_min,'zmax':zmax,'qz':qz,'max_inverse_silence_probability':max_w,
            'alternative_finite_J_over_TV_bound':ctv,'explicit_histories':histories,
            'proved_in_document':'E||D1||^2 <= C_causal_energy E||CA D1||^2 for all allowed policies',
            'conclusion':'pathwise range injectivity is sufficient but not necessary for a finite linear-TV bound',
            'not_an_empirical_necessity_claim':True}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--case',choices=CASES+('all',),required=True)
    ap.add_argument('--output',type=Path)
    args=ap.parse_args(); out=args.output or ROOT/'reviews/artifacts/numeric'/args.case
    out.mkdir(parents=True,exist_ok=False)
    before=old_assets(); results={}
    for name in CASES if args.case=='all' else (args.case,):
        caseout=out/name; caseout.mkdir()
        result=globals()[name](caseout)
        (caseout/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
        results[name]=result
        print(json.dumps({'case':name,'status':'completed'},ensure_ascii=False))
    assert before==old_assets(), 'Original experimental assets changed!'
    (out/'preserved_assets.json').write_text(json.dumps(before,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'run_manifest.json').write_text(json.dumps({'python':sys.version,'numpy':np.__version__,'scipy':scipy.__version__,
        'platform':platform.platform(),'script_sha256':digest(Path(__file__)),
        'case_names':list(results),'preserved_original_asset_count':len(before),
        'old_assets_unchanged':True,'new_physical_Monte_Carlo_trajectories':0},ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':main()
