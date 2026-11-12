"""Fixed 2D experiments. Float evaluations of analytic formulas, not interval proofs.
Run: python experiments.py. No model fitting, attack optimization, or data selection.
"""
from pathlib import Path
import csv, hashlib, json, math, sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator, FixedFormatter, NullFormatter
from vector_core import arr, sym, covariance_update, silence, run_tree, quadrature_check

HERE=Path(__file__).resolve().parent
OUT=HERE/'vector_data'
PARAMETERS={
    'k':4, 'b_ref':0.2, 'b_values':[0.025,0.05,0.1,0.2],
    'budget_peak':0.1, 'epsilon_values':[1e-5,1e-4,1e-3,1e-2,1e-1],
    'confidence_alpha':0.05, 'sample_size_per_group':10000,
    'planning_margin_in_damage_units':0.01,
    'cases':{
      'S':{'A':[[0.82,0.18],[-0.10,0.72]]},
      'U':{'A':[[1.04,0.12],[0.03,0.91]]},
    },
    'common':{
      'P0':[[0.8,0.12],[0.12,0.6]],'Q':[[0.05,0.01],[0.01,0.04]],
      'R':[[0.2,0.03],[0.03,0.3]],'Z':[[2.0,0.25],[0.25,1.5]],
      'direction':[1.,-1.], 'quadrature_bias':[0.13,-0.17],
    }
}

def constants(model,k,bref):
    A,Q,R,Z=(model[x] for x in ('A','Q','R','Z'))
    nodes=[(1.,model['P0'])]
    r=0.; ells=[]; radii=[]; posterior=[]; lower=[]
    v=model['direction']/np.linalg.norm(model['direction'])
    for t in range(k+1):
        al=[];be=[];next_nodes=[];ell=np.linalg.norm(A,2)*r if t else 0.
        for mass,P in nodes:
            s=silence(P,np.zeros(2),R,Z)[0]
            for i,prob in ((0,s),(1,1-s)):
                K,post,_=covariance_update(P,R if i else R+np.linalg.inv(Z))
                al.append(np.linalg.norm(np.eye(2)-K,2))
                if i: be.append(np.linalg.norm(K,2))
                next_nodes.append((mass*prob,sym(A@post@A.T+Q)))
                if t==k:
                    posterior.append(post)
                    if i:
                        S=P+R;Ti=np.linalg.inv(S)+Z;ui=A@K@v
                        f1=np.sqrt(2/np.pi)*(np.sqrt(v@np.linalg.solve(S,v))+s*np.sqrt(v@Ti@v))
                        f2=2*(v@np.linalg.solve(S,v)+s*(v@Ti@v))
                        az=ui@Z@ui
                        Bh=f2+2*f1*2*np.sqrt(az/np.e)+(1-s)*2*az
                        lower.append((mass,(1-s)*np.linalg.norm(K@v)**2,Bh,np.linalg.norm(ui)))
        r=max(al)*ell+max(be);ells.append(ell);radii.append(r);nodes=next_nodes
    omega=max(np.trace(p) for p in posterior)-min(np.trace(p) for p in posterior)
    hs=[];ws=[]
    for P in posterior:
        Sigma=A@P@A.T+Q+R
        H=.5*A.T@np.linalg.solve(np.linalg.inv(Z)+Sigma,A)
        hs.append(np.linalg.eigvalsh(sym(H)).min())
        ws.append(1/silence(A@P@A.T+Q,np.zeros(2),R,Z)[0])
    h=min(hs);M=max(ws);B=r*bref;q=-np.expm1(-h*B*B)/(B*B)
    Cpeak=r*r+omega*np.linalg.norm(Z,2)*sum(e*e for e in ells)/2
    Cpm=sum(m*bh for m,l,bh,u in lower)/4
    Lv=sum(m*l for m,l,bh,u in lower)
    kappa=1/max(1,max(u for m,l,bh,u in lower))
    return dict(r_k=float(r),h_star=float(h),M=float(M),q=float(q),Omega=float(omega),
        C_peak=float(Cpeak),C_record=float(M/q+omega),L=float(M+q*omega),
        p_max=float(max(np.trace(p) for p in posterior)),
        C_pm=float(Cpm),L_v=float(Lv),kappa=float(kappa),radii=list(map(float,radii)))

def score_moments(tree,model,c):
    A,Q,R,Z=(model[x] for x in ('A','Q','R','Z'))
    mean=second=randomvar=0.
    for mass,P,D,h in tree['target_nodes']:
        ps,base,_=silence(A@P@A.T+Q,A@D,R,Z)
        t0=c['q']*(c['p_max']-np.trace(P))/c['L']
        t1=t0+1/(base*c['L'])
        assert -1e-12<=t0<=t1<=1+1e-12
        mean+=mass*((1-ps)*t0+ps*t1)
        second+=mass*((1-ps)*t0*t0+ps*t1*t1)
        randomvar+=mass*((1-ps)*t0*(1-t0)+ps*t1*(1-t1))
    vart=second-mean*mean;varb=mean*(1-mean)
    assert abs(varb-vart-randomvar)<1e-12
    return dict(mean=float(mean),variance_T=float(vart),variance_B=float(varb),added_variance=float(randomvar))

def main():
    OUT.mkdir(exist_ok=True);(HERE/'figures').mkdir(exist_ok=True)
    (OUT/'parameters.json').write_text(json.dumps(PARAMETERS,indent=2)+'\n',encoding='utf-8')
    rows=[];budgets=[];cases={}
    for name,specific in PARAMETERS['cases'].items():
        model=arr(dict(PARAMETERS['common'],**specific));k=PARAMETERS['k']
        assert abs(np.linalg.det(model['A']))>1e-8
        for key in ('P0','Q','R','Z'): assert np.linalg.eigvalsh(model[key]).min()>0
        healthy=run_tree(model,k,0.,'healthy');c=constants(model,k,PARAMETERS['b_ref'])
        hs=score_moments(healthy,model,c)
        case=dict(constants=c,rho_A=float(max(abs(np.linalg.eigvals(model['A'])))),
             healthy_mse=healthy['e_trace'],healthy_score=hs,
             P0_R_commutator=float(np.linalg.norm(model['P0']@model['R']-model['R']@model['P0'])),
             quadrature=[quadrature_check(model,o) for o in (24,40)])
        assert case['quadrature'][-1]['silent_covariance_error_fro']<1e-9
        for policy in ('persistent_fixed_direction','compensated_rademacher'):
            for b in PARAMETERS['b_values']:
                actual_amp=b*c['kappa'] if policy=='compensated_rademacher' else b
                tree=run_tree(model,k,actual_amp,policy)
                dc=tree['e_trace']-healthy['e_trace'];J=tree['e_bias2']+dc
                tv=.5*sum(abs(tree['bits'][h]-healthy['bits'][h]) for h in healthy['bits'])
                sc=score_moments(tree,model,c);delta=hs['mean']-sc['mean'];cert=c['C_record']*delta
                assert J<=c['C_peak']*b*b+1e-12
                assert J<=c['C_record']*tv+1e-12
                assert J<=cert+1e-12
                assert tree['diagnostics']['peak_attack_norm']<=b*(1+1e-12)
                assert tree['diagnostics']['witness_residual']<1e-12
                analytic_bound=None
                if policy=='compensated_rademacher':
                    assert abs(dc)<1e-12
                    assert abs(J-c['L_v']*actual_amp**2)<1e-12
                    analytic_bound=c['C_pm']*actual_amp**2
                    assert tv<=analytic_bound+1e-12
                row=dict(case=name,policy=policy,b=b,J=J,bias2=tree['e_bias2'],covariance_change=dc,
                         J_over_b2=J/b**2,event_word_TV=tv,
                         full_log_TV_analytic_upper=analytic_bound,
                         score_gap=delta,population_certificate=cert,**sc,**tree['diagnostics'])
                rows.append(row)
                if policy=='compensated_rademacher' and b==PARAMETERS['budget_peak']:
                    case['budget_base_row']=row
                    n=PARAMETERS['sample_size_per_group'];alpha=PARAMETERS['confidence_alpha']
                    radius=math.sqrt(math.log(1/alpha)/(2*n))
                    margin=PARAMETERS['planning_margin_in_damage_units'];m=margin/c['C_record']
                    case['sampling']=dict(n=n,alpha=alpha,known_radius=radius,two_radius=radius*math.sqrt(2),
                        centered_known_bound=cert+c['C_record']*radius,
                        centered_two_bound=cert+c['C_record']*radius*math.sqrt(2),
                        target_tau=cert+margin,planning_margin=margin,
                        centered_known_planning_n=math.ceil(math.log(1/alpha)/(2*m*m)),
                        centered_two_planning_each_n=math.ceil(math.log(1/alpha)/(m*m)))
        base=case['budget_base_row']
        for eps in PARAMETERS['epsilon_values']:
            lam=min(1,eps/base['full_log_TV_analytic_upper'])
            budgets.append(dict(case=name,b=base['b'],epsilon=eps,mixture_probability=lam,
                achievable_J=lam*base['J'],event_word_TV=lam*base['event_word_TV'],
                full_log_TV_analytic_upper=lam*base['full_log_TV_analytic_upper'],
                worst_case_upper=min(c['C_peak']*base['b']**2,c['C_record']*eps)))
        cases[name]=case
    result=dict(status='passed_float_formula_checks',parameters=PARAMETERS,cases=cases,
                rows=rows,budget_rows=budgets,python=sys.version,numpy=np.__version__,
                source_sha256={p:hashlib.sha256((HERE/p).read_bytes()).hexdigest()
                    for p in ('experiments.py','vector_core.py')},
                limitations=['No continuous-payload TV integration; full-log feasibility uses the analytic sufficient bound.',
                'No interval certificate for floating-point tables; no maximization over the causal attack class.',
                'No asserted covariance-label injectivity; exact event words are enumerated.',
                'Centered confidence values are illustrations, not sampled observations or success probabilities.'])
    (OUT/'results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    for fn,data in [('results.csv',rows),('budgets.csv',budgets)]:
        with (OUT/fn).open('w',encoding='utf-8',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(data[0]));writer.writeheader();writer.writerows(data)
    plt.rcParams.update({'font.family':'serif','font.serif':['Times New Roman'],
        'font.size':9,'axes.labelsize':9,'legend.fontsize':8,'pdf.fonttype':42,
        'lines.linewidth':1.2,'figure.constrained_layout.use':True})
    fig,axes=plt.subplots(1,2,figsize=(6.9,2.7))
    for ax,(name,case) in zip(axes,cases.items()):
        for policy,style,label in [('persistent_fixed_direction','o-','Persistent'),
                                  ('compensated_rademacher','s--','Two-step private sign')]:
            rr=[r for r in rows if r['case']==name and r['policy']==policy]
            ax.loglog([r['b'] for r in rr],[r['J'] for r in rr],style,label=label,color='black' if policy.startswith('persistent') else '0.45')
        ax.set(xlabel='Peak bound b',ylabel='True MSE increase J',title=f'Case {name}')
        ax.xaxis.set_major_locator(FixedLocator(PARAMETERS['b_values']))
        ax.xaxis.set_major_formatter(FixedFormatter(['0.025','0.05','0.1','0.2']))
        ax.xaxis.set_minor_formatter(NullFormatter())
        ax.grid(True,which='both',alpha=.2);ax.legend()
    fig.savefig(HERE/'figures/vector_damage.pdf');plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(6.9,2.7))
    for ax,(name,case) in zip(axes,cases.items()):
        rr=[r for r in budgets if r['case']==name]
        ax.loglog([r['epsilon'] for r in rr],[r['achievable_J'] for r in rr],'o-',color='black',label='Feasible construction')
        ax.loglog([r['epsilon'] for r in rr],[r['worst_case_upper'] for r in rr],'s--',color='0.45',label='All-policy upper bound')
        ax.set(xlabel='Full-log TV budget',ylabel='Damage',title=f'Case {name}, b = 0.1');ax.grid(True,which='both',alpha=.2);ax.legend()
    fig.savefig(HERE/'figures/vector_budget.pdf');plt.close(fig)
    # Generated table fragments bind all displayed numbers to the result JSON.
    lines=[]
    for name,case in cases.items():
        for policy,short in [('persistent_fixed_direction','持续定向'),('compensated_rademacher','两拍符号')]:
            r=next(r for r in rows if r['case']==name and r['policy']==policy and r['b']==.1)
            dc=0. if abs(r['covariance_change'])<1e-14 else r['covariance_change']
            lines.append(f"{name} & {short} & {r['bias2']:.7f} & {dc:.7f} & {r['J']:.7f} & {r['event_word_TV']:.7f} "+r'\\')
    (OUT/'damage_table.tex').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    lines=[]
    for name,case in cases.items():
        r=case['budget_base_row'];s=case['sampling'];c=case['constants']
        lines.append(f"{name} & {c['C_record']:.3f} & {r['population_certificate']:.6f} & {s['centered_known_bound']:.3f} & {s['centered_two_bound']:.3f} "+r'\\')
    (OUT/'certificate_table.tex').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    lines=[]
    for name,case in cases.items():
        r=case['budget_base_row'];s=case['sampling']
        lines.append(f"{name} & {r['variance_T']:.6f} & {r['variance_B']:.6f} & {r['added_variance']:.6f} "+r'\\')
    (OUT/'variance_table.tex').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    lines=[]
    for name,case in cases.items():
        c=case['constants'];s=case['sampling']
        lines.append(f"{name} & {c['L_v']:.6f} & {c['C_pm']:.6f} & {c['C_peak']:.6f} & {c['kappa']:.6f} "+r'\\')
    (OUT/'constant_table.tex').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=result['status'],cases={name:dict(constants=v['constants'],sampling=v['sampling']) for name,v in cases.items()}),indent=2))

if __name__=='__main__': main()
