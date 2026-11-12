"""Publication-quality plots of the fixed MH record comparison."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter

HERE=Path(__file__).resolve().parent
data=json.loads((HERE/'results.json').read_text(encoding='utf-8'))
plt.rcParams.update({'font.family':'DejaVu Serif','font.size':9,'axes.labelsize':9,
    'axes.titlesize':10,'legend.fontsize':8,'pdf.fonttype':42,'ps.fonttype':42,
    'axes.linewidth':.7,'lines.linewidth':1.4,'xtick.direction':'in','ytick.direction':'in'})
fig,axes=plt.subplots(1,2,figsize=(7.1,2.65),layout='constrained')
colors={'S':'#1f5a99','U':'#b34b28'}
markers={'S':'o','U':'s'}
for case in ['S','U']:
    rows=[r for r in data['rows'] if r['case']==case]
    b=[r['b'] for r in rows]
    axes[0].plot(b,[r['damage_J_float'] for r in rows],color=colors[case],marker=markers[case],
        markersize=4,label=f'{case}: damage')
    axes[0].plot(b,[r['population_score_certificate_float'] for r in rows],color=colors[case],
        linestyle='--',label=f'{case}: population certificate')
    axes[1].plot(b,[r['extended_event_word_TV_float'] for r in rows],color=colors[case],marker=markers[case],
        markersize=4,label=rf'{case}: events through $k+1$')
axes[1].plot([.025,.05,.1,.2],[0,0,0,0],color='#333333',linestyle=':',marker='x',markersize=4,
             label=r'Full log through $k$ (analytic)')
for ax in axes:
    ax.set_xlabel(r'Modification bound $b$')
    ax.set_xticks([.025,.05,.1,.2],['0.025','0.05','0.10','0.20'])
    ax.grid(axis='y',alpha=.23,linewidth=.5)
    formatter=ScalarFormatter(useMathText=True);formatter.set_powerlimits((0,0))
    ax.yaxis.set_major_formatter(formatter)
    ax.legend(frameon=False,loc='upper left',handlelength=1.7)
axes[0].set_title('(a) Estimation damage and certificate')
axes[0].set_ylabel(r'MSE increment / upper bound')
axes[1].set_title('(b) Dependence on the observation horizon')
axes[1].set_ylabel('Total variation distance')
axes[0].set_ylim(bottom=0)
axes[1].set_ylim(bottom=-.00003)
fig.savefig(HERE/'record_conditions.pdf',bbox_inches='tight')
fig.savefig(HERE/'record_conditions.png',dpi=180,bbox_inches='tight')
plt.close(fig)
print('record_conditions.pdf and record_conditions.png written')
