"""Read-only analysis of the frozen final run; never regenerates trajectories."""
from pathlib import Path
import csv,json,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import stats
B=Path(__file__).resolve().parents[1]
SRC=B/'results/g1r_final_replay_20261113_v1'
OUT=B/'results/g1r_final_analysis_20261113_v1'

def ci(a):
 a=np.asarray(a,float); m=float(a.mean()); h=float(stats.t.ppf(.975,len(a)-1)*a.std(ddof=1)/np.sqrt(len(a)))
 return {'n':len(a),'mean':m,'ci95':[m-h,m+h]}
def wilson(k,n):
 z=stats.norm.ppf(.975); p=k/n; q=1+z*z/n
 mid=(p+z*z/(2*n))/q; h=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/q
 return [float(mid-h),float(mid+h)]

def main():
 OUT.mkdir(exist_ok=False)
 frozen=json.loads((SRC/'frozen_plan.json').read_text()); cases=json.loads((SRC/'cases.json').read_text()); summary=json.loads((SRC/'summary.json').read_text())
 with (SRC/'metrics.csv').open(encoding='utf-8',newline='') as f: metrics=list(csv.DictReader(f))
 root=B.parents[1]; failures=[]
 for name,expected in frozen['source_sha256'].items():
  f=root/Path(name.replace('\\','/')); actual=hashlib.sha256(f.read_bytes()).hexdigest()
  if actual!=expected: failures.append(name)
 assert not failures,failures
 seeds=set(frozen['test_seeds']); assert len(seeds)==100
 for name in ('train_seeds','calibration_seeds','debug_seeds'): assert not seeds.intersection(frozen[name])
 assert len(cases)==800 and len(metrics)==4800
 assert all({x['seed'] for x in cases if x['scenario']==s and x['condition']=='replay'}==seeds for s in ['main','age32','age96','gap4','gap12'])
 assert (SRC/'frozen_plan.json').stat().st_mtime_ns < (SRC/'metrics.csv').stat().st_mtime_ns
 lookup={(r['scenario'],r['condition'],int(r['seed']),r['method']):r for r in metrics}
 groups=[]; counts=[]
 for scenario in ['main','age32','age96','gap4','gap12']:
  cc=[x for x in cases if x['scenario']==scenario and x['condition']=='replay']
  cc=sorted(cc,key=lambda x:(x['attack_payload_norm_offline'],x['seed']))
  for b,idx in enumerate(np.array_split(np.arange(len(cc)),3),1):
   subset=[cc[int(j)] for j in idx]; paired=[]
   for x in subset:
    key=(scenario,'replay',x['seed']); a=lookup[key+('joint',)]; y=lookup[key+('yang',)]
    paired.append(float(a['receiver_mse'])-float(y['receiver_mse']))
   groups.append({'scenario':scenario,'tertile':b,'n':len(subset),'norm_min':subset[0]['attack_payload_norm_offline'],
      'norm_max':subset[-1]['attack_payload_norm_offline'],'alarm_rate':sum(x['alarm'] for x in subset)/len(subset),
      'correct_attribution_rate':sum(x['correct_attribution_offline'] for x in subset)/len(subset),
      'receiver_difference_joint_minus_yang':ci(paired)})
  for cond in ('clean','replay'):
   cc2=[x for x in cases if x['scenario']==scenario and x['condition']==cond]
   if not cc2: continue
   n=len(cc2); alarms=sum(x['alarm'] for x in cc2)
   counts.append({'scenario':scenario,'condition':cond,'n':n,'alarm':alarms,'alarm_wilson95':wilson(alarms,n),
    'correct_attribution':sum(x['correct_attribution_offline'] for x in cc2),
    'wrong_attribution':sum(x['alarm'] and not x['correct_attribution_offline'] for x in cc2) if cond=='replay' else None,
    'joint_shadow_max':max(x['joint_shadow_max'] for x in cc2),'oracle_healthy_max':max(x['oracle_healthy_max'] for x in cc2)})
 (OUT/'amplitude_tertiles.json').write_text(json.dumps(groups,indent=2)+'\n',encoding='utf-8')
 (OUT/'detection_counts.json').write_text(json.dumps(counts,indent=2)+'\n',encoding='utf-8')
 (OUT/'validation.json').write_text(json.dumps({'source_hashes_match':not failures,'seed_splits_disjoint':True,'test_n':100,'case_rows':len(cases),'metric_rows':len(metrics),'frozen_before_metrics':True,'source_run':str(SRC.name)},indent=2)+'\n',encoding='utf-8')
 by={(x['scenario'],x['condition'],x['method']):x for x in summary}
 methods=['yang','isolate','discard','shadow','joint','oracle']
 colors=['#555555','#d36a38','#c6a550','#3878b1','#36a16a','#875db4']
 fig,ax=plt.subplots(figsize=(9,4.2)); x=np.arange(len(methods))
 for k,name in enumerate(methods):
  z=by[('main','replay',name)]['receiver_mse']; lo,hi=z['ci95']; ax.bar(k,z['mean'],color=colors[k],width=.65); ax.errorbar(k,z['mean'],yerr=[[z['mean']-lo],[hi-z['mean']]],color='black',capsize=3,fmt='none')
 ax.set_xticks(x,methods,rotation=12);ax.set_ylabel('Receiver recovery-window MSE');ax.set_title('Single replay: gap 8, historical age 64');fig.tight_layout();fig.savefig(OUT/'main_mse.png',dpi=180);plt.close(fig)
 fig,axs=plt.subplots(1,2,figsize=(10,4))
 for ax,scens,labels,title in [(axs[0],['age32','main','age96'],['32','64','96'],'Historical packet age (steps)'),(axs[1],['gap4','main','gap12'],['4','8','12'],'Communication gap (steps)')]:
  for method,col in [('yang','#555555'),('joint','#36a16a'),('shadow','#3878b1')]:
   zz=[by[(s,'replay',method)]['receiver_mse'] for s in scens]; means=np.array([v['mean'] for v in zz]); lo=np.array([v['ci95'][0] for v in zz]); hi=np.array([v['ci95'][1] for v in zz]); ax.errorbar(np.arange(3),means,yerr=[means-lo,hi-means],marker='o',capsize=3,label=method,color=col)
  ax.set_xticks(np.arange(3),labels);ax.set_xlabel(title);ax.set_ylabel('Receiver recovery-window MSE');ax.legend()
 fig.tight_layout();fig.savefig(OUT/'sensitivity_mse.png',dpi=180);plt.close(fig)
 main_counts=[x for x in counts if x['scenario']=='main']; print(json.dumps({'out':str(OUT),'main_counts':main_counts,'main_tertiles':[x for x in groups if x['scenario']=='main']},indent=2))
if __name__=='__main__': main()
