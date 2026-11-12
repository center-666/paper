"""Independent physical-noise map and exact marked-distribution target-MSE check."""
from pathlib import Path
import csv,hashlib,json,math,shutil
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'simulation/checks/2026-11-12_reachable_silence_screen_v2'
OUT=ROOT/'simulation/checks/2026-11-12_reachable_silence_atom_audit'


def posterior(P,C,R):
    return np.linalg.inv(np.linalg.inv(P)+C.T@np.linalg.solve(R,C))


def silence_from_noise_maps(A,C,Q,R,Z,P,d,L):
    n=len(A);m=len(C);G=np.vstack([C@np.linalg.matrix_power(A,j) for j in range(1,L+1)])
    W=np.zeros((L*m,L*n))
    for j in range(1,L+1):
        for r in range(1,j+1):W[(j-1)*m:j*m,(r-1)*n:r*n]=C@np.linalg.matrix_power(A,j-r)
    V=G@P@G.T+W@np.kron(np.eye(L),Q)@W.T+np.kron(np.eye(L),R)
    zb=np.kron(np.eye(L),Z)
    s=math.exp(-0.5*np.linalg.slogdet(np.eye(L*m)+V@zb)[1])
    mean=G@d
    attacked=s*math.exp(-0.5*mean@np.linalg.solve(V+np.linalg.inv(zb),mean))
    return s,attacked


def main():
    OUT.mkdir(parents=True,exist_ok=False)
    plan=json.loads((SOURCE/'plan.json').read_text(encoding='utf-8'))
    results=json.loads((SOURCE/'results.json').read_text(encoding='utf-8'))
    rows=[];max_bound_violation=0.;max_mass_error=0.
    b=.25
    for model in plan['fixed_models']:
        A,C,P=map(lambda v:np.asarray(v,float),(model['A'],model['C'],model['P0']))
        n=len(A);m=len(C);Q=np.asarray(plan['Q']);R=.1*np.eye(m);Z=2*np.eye(m)
        S=C@P@C.T+R;K=P@C.T@np.linalg.inv(S)
        p_silent=math.exp(-.5*np.linalg.slogdet(np.eye(m)+S@Z)[1]);p_send=1-p_silent
        P_send=posterior(P,C,R);P_silent=posterior(P,C,R+np.linalg.inv(Z))
        v=np.eye(m)[:,0];d=-b*K@v
        # Attack is +/-b*v after the first real sending decision, zero thereafter.
        J=p_send*float(d@d)
        for L in plan['lookahead_L']:
            s1,a1=silence_from_noise_maps(A,C,Q,R,Z,P_send,d,L)
            s0,a0=silence_from_noise_maps(A,C,Q,R,Z,P_silent,np.zeros(n),L)
            normal=np.array([p_silent*s0,p_silent*(1-s0),p_send*s1,p_send*(1-s1)])
            attacked=np.array([p_silent*a0,p_silent*(1-a0),p_send*a1,p_send*(1-a1)])
            delta=.5*float(np.abs(attacked-normal).sum())
            max_mass_error=max(max_mass_error,abs(normal.sum()-1),abs(attacked.sum()-1))
            M=next(x for x in results['models'] if x['model']==model['name'])
            detail=next(x for x in M['targets'][0]['details'] if x['L']==L)
            constant=detail.get('marked_damage_upper_constant')
            if constant is not None:max_bound_violation=max(max_bound_violation,J-constant*delta)
            rows.append({'model':model['name'],'target_k':0,'L':L,'peak_b':b,
                         'true_target_mse_increment':J,'marked_record_TV':delta,
                         'certified_upper_constant_at_bref1':constant,
                         'certificate_upper':None if constant is None else constant*delta,
                         'actual_J_over_delta':None if delta==0 else J/delta,
                         'source':'exact four-atom marked distribution; physical-noise map covariance'})
    erased=[r for r in rows if r['model']=='singular_A_erases_attack']
    assert all(r['true_target_mse_increment']>0 and r['marked_record_TV']==0 for r in erased)
    assert max_bound_violation<1e-11 and max_mass_error<1e-12
    with (OUT/'exact_target_damage.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    summary={'passed':True,'cases':len(rows),'new_state_trajectories':0,
             'max_positive_bound_violation':max_bound_violation,'max_atom_mass_error':max_mass_error,
             'singular_A_positive_damage_zero_marked_TV':True,
             'note':'The TV record is (exact posterior covariance tag, all-silent future-window bit), not the full received-payload log. This does not prove a minimax matching lower bound.',
             'source_results_sha256':hashlib.sha256((SOURCE/'results.json').read_bytes()).hexdigest(),
             'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (OUT/'audit.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    shutil.copy2(__file__,OUT/Path(__file__).name)
    print(json.dumps(summary,indent=2));print(json.dumps(rows[:4],indent=2))


if __name__=='__main__':main()
