"""One independent final run. No recovery tuning or reruns after test output.

Fixed five-node Yang-form model, one historical transmitted packet replay,
receiver-local maximum full-prefix GLS and synchronous control micro-rounds.
Normal training/calibration fit is frozen before any final test is generated.
"""
from __future__ import annotations
import copy,csv,hashlib,json,sys,time
from pathlib import Path
import numpy as np
from scipy import stats

BRANCH=Path(__file__).resolve().parents[1]
ROOT=BRANCH.parents[1]
sys.path.insert(0,str(ROOT/'simulation'))
sys.path.insert(0,str(BRANCH/'code'))
from model import Model,generate_data
from minimal_recovery_screen import build_model,TRAIN,CAL,R
import p0_verified as p0
import receiver_gls_writeback as local
from joint_recovery_debug import resume

RUN='g1r_final_replay_20261113_v1'
OUT=BRANCH/'results'/RUN
TEST=np.arange(9930000,9930100)
DEBUG=np.arange(9911000,9911005)
RECEIVER=1
NWIN=41
HORIZON=44
# These are the full set of analyses, declared before test data generation.
SCENARIOS=(('age32',8,4),('main',8,8),('age96',8,12),
           ('gap4',4,8),('gap12',12,8))


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def schedule_for(model,count,gap):
    t=np.arange(model.cfg['T']); a=np.zeros((count,len(t),model.cfg['N']),dtype=bool)
    for j in range(model.cfg['N']): a[:,:,j]=(t%gap)==((R+j)%gap)
    a[:,0,:]=True
    return a

def build(gap,lag):
    cfg=copy.deepcopy(build_model().cfg)
    cfg['attack']['replay_packet_lag']=int(lag)
    cfg['attack']['start']=cfg['attack']['end_inclusive']=int(R)
    return Model.build(cfg)

def records(log,model,s,begin,decision):
    inc=np.flatnonzero(model.edges[:,1]==RECEIVER)
    return [local.Reception(int(e),int(t)) for t in range(begin,decision+1)
            for e in inc if log.clocks[s,t,e]==t]

def innovation(log,model,s,begin,decision):
    return (log.local_y[s,begin:decision+1,RECEIVER]
            -np.einsum('ab,tb->ta',model.H[RECEIVER],log.own[s,begin:decision+1,RECEIVER]))

def fit_for_gap(gap):
    m=build(gap,8); d=R+2*gap; begin=d-NWIN+1
    def normal(seeds):
        x,y=generate_data(m,seeds); sch=schedule_for(m,len(seeds),gap)
        _,log=p0.reference(m,x,y,seeds,sch,'clean')
        return sch,log,np.stack([innovation(log,m,i,begin,d) for i in range(len(seeds))])
    st,lt,tr=normal(TRAIN); sc,lc,cal=normal(CAL)
    if not np.array_equal(st[0],sc[0]): raise ValueError('normal schedule mismatch')
    rec=records(lt,m,0,begin,d)
    if rec!=records(lc,m,0,begin,d): raise ValueError('normal receive mismatch')
    fit=local.fit_full_prefix(m,st[0],RECEIVER,begin,d,rec,tr,cal,.02,.95)
    return fit

def writeback(model,run,log,s,fit,decision,d):
    state=run.estimates[s,d+1].copy(); raw=log.raw[s,d].copy(); last=log.clocks[s,d].copy()
    packets,traffic=local.deliver_command(decision,model.edges,RECEIVER,model.cfg['N'])
    if decision is not None:
        c=next(c for c in fit.candidates if c.event==decision.event)
        for node in range(model.cfg['N']):
            inc=np.flatnonzero(model.edges[:,1]==node)
            state[node],raw[inc]=local.apply_local_writeback(node,state[node],raw[inc],inc,
                                                             packets[node],c,d,model.edges)
    return state,raw,last,traffic

def discard(log,s,d,decision):
    raw=log.raw[s,d].copy(); last=log.clocks[s,d].copy()
    if decision is None: return raw,last,False
    ev=decision.event
    if last[ev.edge]!=ev.time: return raw,last,False
    if ev.time<=0 or log.clocks[s,ev.time-1,ev.edge]<0:
        raise ValueError('cannot discard without a previously received cache')
    raw[ev.edge]=log.raw[s,ev.time-1,ev.edge]; last[ev.edge]=log.clocks[s,ev.time-1,ev.edge]
    return raw,last,True

def ci(vals):
    a=np.asarray(vals,float); mu=float(np.mean(a)); half=float(stats.t.ppf(.975,len(a)-1)*stats.sem(a))
    return {'n':len(a),'mean':mu,'ci95':[mu-half,mu+half]}

def recovery_time(traj,healthy,start,end):
    # Offline paired-track discrepancy; 5 consecutive iterations below 0.1.
    diff=np.linalg.norm(traj[start:end+1,RECEIVER]-healthy[start:end+1,RECEIVER],axis=-1)
    for k in range(len(diff)-4):
        if np.all(diff[k:k+5]<=.1): return int(k)
    return None

def main():
    OUT.mkdir(parents=True,exist_ok=False); start_clock=time.perf_counter()
    if set(TRAIN)&set(CAL) or set(TEST)&(set(TRAIN)|set(CAL)|set(DEBUG)):
        raise AssertionError('training, calibration, debug and final test seeds overlap')
    model=build(8,8)
    fits={g:fit_for_gap(g) for g in (4,8,12)}
    paths=[Path(__file__),BRANCH/'code/receiver_gls_writeback.py',BRANCH/'code/joint_recovery_debug.py',
           BRANCH/'code/p0_verified.py',BRANCH/'code/compare_deghat_outputs.py',
           BRANCH/'code/minimal_recovery_screen.py',ROOT/'simulation/engine.py',ROOT/'simulation/model.py',
           ROOT/'simulation/config.json',ROOT/'simulation/reference_exploration_plan.json']
    freeze={'run_id':RUN,'stage':'FROZEN BEFORE FINAL TEST DATA GENERATION',
      'scope':'single actual historical-packet replay; exogenous fixed schedule',
      'scenarios':[{'id':name,'gap':gap,'historical_packet_lag':lag,'decision':int(R+2*gap)} for name,gap,lag in SCENARIOS],
      'baseline_attack_time':int(R),'recovery_horizon':HORIZON,
      'methods':['yang','isolate','discard','shadow','joint','oracle'],
      'train_seeds':TRAIN.tolist(),'calibration_seeds':CAL.tolist(),'test_seeds':TEST.tolist(),
      'debug_seeds':DEBUG.tolist(),'candidate_window_steps':NWIN,'covariance_ridge_fraction':.02,
      'calibration_quantile':.95,'thresholds':{str(g):fits[g].threshold for g in fits},
      'candidate_events':{str(g):[[c.event.edge,c.event.time] for c in fits[g].candidates] for g in fits},
      'controls':'four 21-byte directed payloads; two reliable synchronous micro-rounds; frame/authentication/retransmission excluded',
      'amplitude_analysis':'observational post-stratification into within-scenario tertiles of offline actual replay payload difference, not a causal amplitude intervention',
      'recovery_time':'first of five consecutive paired-clean receiver state differences <= 0.1 in 44 steps; right-censor otherwise',
      'intervals':'paired t intervals over seed; exploratory, no multiplicity adjustment',
      'normal_gate':'single decision time; maximum over eligible receptions calibrated on independent normal runs',
      'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in paths}}
    (OUT/'frozen_plan.json').write_text(json.dumps(freeze,indent=2)+'\n',encoding='utf-8')
    # Only after the plan, thresholds and code hashes are frozen, create final test data.
    x,y=generate_data(model,TEST)
    cases=[]; rows=[]; traces={}; healthy_by_gap={}
    for gap in (4,8,12):
        m=build(gap,8); sch=schedule_for(m,len(TEST),gap)
        cr,cl=p0.reference(m,x,y,TEST,sch,'clean')
        healthy_by_gap[gap]=(cr,cl,sch)
    for scenario,gap,lag in SCENARIOS:
        m=build(gap,lag); d=R+2*gap; end=d+HORIZON
        fit=fits[gap]; clean,clog,sch=healthy_by_gap[gap]
        run,log=p0.reference(m,x,y,TEST,sch,'replay_packet')
        target=int(np.flatnonzero(np.all(m.edges==[0,1],axis=1))[0]); event=local.Reception(target,R)
        oracleS,oracle_raw=local._response(m,sch[0],event,d)
        for condition,active,lg in [('clean',clean,clog),('replay',run,log)]:
          # Avoid duplicate healthy trials: evaluate normal cost once for each gap.
          if condition=='clean' and scenario not in ('main','gap4','gap12'): continue
          for s,seed in enumerate(TEST):
            obs=innovation(lg,m,s,d-NWIN+1,d)
            dec=local.attribute(fit,obs,records(lg,m,s,d-NWIN+1,d))
            state=active.estimates[s,d+1].copy(); raw=lg.raw[s,d].copy(); last=lg.clocks[s,d].copy()
            js,jr,jl,traffic=writeback(m,active,lg,s,fit,dec,d)
            joint=resume(m,y[s],sch[s],d+1,js,jr,jl,'normal',target)
            edge=target if dec is None else dec.event.edge
            isolate=resume(m,y[s],sch[s],d+1,state,raw,last,'normal' if dec is None else 'isolate',edge)
            dr,dl,dropped=discard(lg,s,d,dec)
            disc=resume(m,y[s],sch[s],d+1,state,dr,dl,'normal',target)
            shadow=active.estimates[s].copy()
            if dec is not None:
                candidate=next(c for c in fit.candidates if c.event==dec.event)
                shadow[d+1:]-=np.einsum('tinp,p->tin',candidate.state_response[d+1:],dec.theta)
            delta=np.zeros(m.cfg['n']); source=-1
            if condition=='replay':
                source=int(active.replay_source[s,R])
                if not (0<=source<R and active.sends[s,source,0]): raise AssertionError('invalid historical packet')
                delta=active.estimates[s,source,0]-active.estimates[s,R,0]
            os=state-np.einsum('inp,p->in',oracleS[d+1],delta)
            oraw=raw-np.einsum('enp,p->en',oracle_raw,delta)
            oracle=resume(m,y[s],sch[s],d+1,os,oraw,last,'normal',target)
            discrepancy=float(np.max(np.abs(joint[d+1:]-shadow[d+1:])))
            oracle_error=float(np.max(np.abs(oracle[d+1:]-clean.estimates[s,d+1:])))
            if discrepancy>1e-9 or oracle_error>1e-9: raise AssertionError((discrepancy,oracle_error))
            methods={'yang':active.estimates[s],'isolate':isolate,'discard':disc,
                     'shadow':shadow,'joint':joint,'oracle':oracle}
            start=d+1; truth=x[s,start:end+1]
            for name,traj in methods.items():
                sq=np.sum((traj[start:end+1]-truth[:,None,:])**2,axis=-1)
                healthy_sq=np.sum((clean.estimates[s,start:end+1]-truth[:,None,:])**2,axis=-1)
                rows.append({'scenario':scenario,'condition':condition,'gap':gap,'lag':lag,'seed':int(seed),
                   'method':name,'receiver_mse':float(sq[:,RECEIVER].mean()),'network_mse':float(sq.mean()),
                   'receiver_excess_vs_healthy':float((sq[:,RECEIVER]-healthy_sq[:,RECEIVER]).mean()),
                   'network_excess_vs_healthy':float((sq-healthy_sq).mean()),
                   'recovery_time_steps':recovery_time(traj,clean.estimates[s],start,end),
                   'alarm':dec is not None,'payload_bytes':sum(t['payload_bytes'] for t in traffic) if name=='joint' else 0,
                   'scheduled_edge_payload_bytes':int(sch[s,:,m.edges[:,0]].sum()*m.cfg['n']*8)})
                traces[f'{scenario}_{condition}_{seed}_{name}']=traj[start:end+1].astype(np.float32)
            cases.append({'scenario':scenario,'condition':condition,'seed':int(seed),'alarm':dec is not None,
               'chosen_edge':None if dec is None else dec.event.edge,'chosen_time':None if dec is None else dec.event.time,
               'correct_attribution_offline':condition=='replay' and dec is not None and dec.event==event,
               'attack_source_time_offline':source,'attack_age_offline':None if source<0 else int(R-source),
               'attack_payload_norm_offline':float(np.linalg.norm(delta)),'active_discard':dropped,
               'joint_shadow_max':discrepancy,'oracle_healthy_max':oracle_error,'traffic':traffic})
    with (OUT/'metrics.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    np.savez_compressed(OUT/'trajectories.npz',**traces)
    (OUT/'cases.json').write_text(json.dumps(cases,indent=2)+'\n',encoding='utf-8')
    summary=[]
    for scenario,gap,lag in SCENARIOS:
      for condition in (('clean','replay') if scenario in ('main','gap4','gap12') else ('replay',)):
        z=[q for q in rows if q['scenario']==scenario and q['condition']==condition]
        by_method={name:sorted((q for q in z if q['method']==name),key=lambda q:q['seed']) for name in freeze['methods']}
        for name,items in by_method.items():
          base=by_method['yang']; dif=[a['receiver_mse']-b['receiver_mse'] for a,b in zip(items,base)]
          difn=[a['network_mse']-b['network_mse'] for a,b in zip(items,base)]
          summary.append({'scenario':scenario,'condition':condition,'method':name,
            'receiver_mse':ci([a['receiver_mse'] for a in items]),'network_mse':ci([a['network_mse'] for a in items]),
            'receiver_difference_vs_yang':ci(dif),'network_difference_vs_yang':ci(difn),
            'recovered_within_44':sum(a['recovery_time_steps'] is not None for a in items),
            'mean_extra_payload_bytes':float(np.mean([a['payload_bytes'] for a in items]))})
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    (OUT/'completion.json').write_text(json.dumps({'completed':True,'n_case':len(cases),
       'n_metric_rows':len(rows),'elapsed_seconds':time.perf_counter()-start_clock},indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'run_id':RUN,'n_cases':len(cases),'metrics':len(rows),'seconds':time.perf_counter()-start_clock}))
if __name__=='__main__': main()
