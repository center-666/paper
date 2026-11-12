from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE=Path(__file__).resolve().parent
r=json.loads((HERE.parent/'ack_accuracy_matched_20261109/results.json').read_text(encoding='utf-8'))
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'pdf.fonttype':42})
fig,axs=plt.subplots(1,2,figsize=(9,3.7),layout='constrained')
for ax,(attack,title) in zip(axs,[('greedy','Causal greedy attack'),('calendar','Heterogeneous calendar')]):
    for key,label,color,marker,offset in [
        ('original','Immediate, 0.20','#777777','s',(6,-12)),
        ('full','Full memory, 0.20','#176f9c','*',(-12,14)),
        ('calibrated_immediate',f"Calibrated, {r[attack]['theta']:.2f}",'#b34d26','o',(-98,-18))]:
        v=r[attack][key]
        ax.scatter(v['mse'],v['attempts']/50,c=color,marker=marker,s=80 if key=='full' else 42,zorder=3)
        ax.annotate(label,(v['mse'],v['attempts']/50),xytext=offset,textcoords='offset points',
                    color=color,fontsize=8)
    ax.set_title(title);ax.set_xlabel('Mean squared error');ax.set_ylabel('Mean attempts per run')
    ax.grid(alpha=.22);ax.margins(x=.27,y=.19)
fig.suptitle('Original 50 test runs; baseline thresholds selected on 20 separate calibration runs',fontsize=10)
fig.savefig(HERE/'figures/matched_tradeoff.pdf',bbox_inches='tight')
fig.savefig(HERE/'figures/matched_tradeoff.png',dpi=180,bbox_inches='tight')
print('Matched comparison figure saved')
