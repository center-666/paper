"""Plot the analytic budget bounds, including their exact crossover points."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent
data=json.loads((HERE/'vector_data/results.json').read_text(encoding='utf-8'))
plt.rcParams.update({'font.family':'serif','font.serif':['Times New Roman'],
    'font.size':9,'axes.labelsize':9,'legend.fontsize':8,'pdf.fonttype':42,
    'lines.linewidth':1.2,'figure.constrained_layout.use':True})
fig,axes=plt.subplots(1,2,figsize=(6.9,2.8))
checks={}
for ax,name in zip(axes,('S','U')):
    rows=[r for r in data['budget_rows'] if r['case']==name]
    c=data['cases'][name]['constants'];b=data['parameters']['budget_peak']
    eps=np.asarray([r['epsilon'] for r in rows])
    lower_knee=c['C_pm']*c['kappa']**2*b*b
    upper_knee=c['C_peak']*b*b/c['C_record']
    # Each bound is piecewise linear in log-log coordinates. Include every
    # crossover so no line segment cuts below the actual theoretical upper bound.
    knots=np.unique(np.r_[eps,[e for e in (lower_knee,upper_knee) if eps.min()<e<eps.max()]])
    lower=lambda e:c['L_v']*np.minimum(c['kappa']**2*b*b,e/c['C_pm'])
    upper=lambda e:np.minimum(c['C_peak']*b*b,c['C_record']*e)
    assert np.allclose(lower(eps),[r['achievable_J'] for r in rows],rtol=1e-12,atol=1e-15)
    assert np.allclose(upper(eps),[r['worst_case_upper'] for r in rows],rtol=1e-12,atol=1e-15)
    dense=np.geomspace(eps.min(),eps.max(),500)
    for fun in (lower,upper):
        interpolated=np.exp(np.interp(np.log(dense),np.log(knots),np.log(fun(knots))))
        assert np.allclose(interpolated,fun(dense),rtol=1e-12,atol=1e-15)
    ax.loglog(knots,lower(knots),'-',color='black',label='Constructive lower bound')
    ax.loglog(knots,upper(knots),'--',color='0.45',label='Upper bound for all attacks')
    ax.plot(eps,lower(eps),'o',color='black',markersize=4)
    ax.plot(eps,upper(eps),'s',color='0.45',markersize=4)
    ax.set(xlabel='Full-log TV budget',ylabel='True MSE increase',
           title=f'Case {name}, b = 0.1, k = 4')
    ax.grid(True,which='both',alpha=.2)
    ax.legend(loc='lower right')
    checks[name]=dict(lower_crossover=lower_knee,upper_crossover=upper_knee,
                     plotted_epsilon=knots.tolist(),lower=lower(knots).tolist(),upper=upper(knots).tolist(),
                     original_budget_rows_match=True,log_interpolation_matches_analytic_bounds=True)
fig.savefig(HERE/'figures/vector_budget.pdf')
plt.close(fig)
(HERE/'review_checks/figure_budget_check.json').write_text(json.dumps(checks,indent=2)+'\n',encoding='utf-8')
print('Figure 3: original data retained; exact analytic crossovers included.')
