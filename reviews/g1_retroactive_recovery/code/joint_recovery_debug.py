"""Five-seed debug of fixed-mode global state/cache write-back; not a deployment protocol."""
import csv, hashlib, json, sys, time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
BRANCH=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'simulation'))
sys.path.insert(0,str(BRANCH/'code'))
from model import generate_data
from minimal_recovery_screen import build_model, common_schedule, CAL, R, D
import p0_verified as p0
import compare_deghat_outputs as channels

RUN='g1r_joint_recovery_debug_20261113_v1'
OUT=BRANCH/'results'/RUN
SEEDS=np.arange(9911000,9911005)
EDGE=(0,1)

def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def resume(model,y,schedule,start,state,raw,last,mode,target):
    """Continue using actual local states and edge caches, with no attack input."""
    T,N,n=model.cfg['T'],model.cfg['N'],model.cfg['n']
    ecount=len(model.edges); src,dst=model.edges.T
    state=state.copy(); raw=raw.copy(); last=last.copy()
    out=np.zeros((T+1,N,n)); out[start]=state
    for t in range(start,T):
        fresh=schedule[t,src]
        raw[fresh]=state[src[fresh]]
        last[fresh]=t
        aligned=np.stack([model.powers[t-last[e]]@raw[e] for e in range(ecount)])
        innov=y[t]-np.einsum('imn,in->im',model.H,state)
        base=state@model.A.T+np.einsum('imn,in->im',model.gains[t],innov)
        terms=aligned-state[dst]
        if mode=='isolate': terms[target]=0
        cons=np.zeros_like(state)
        for e,i in enumerate(dst): cons[i]+=terms[e]
        state=base+model.cfg['epsilon']*(cons@model.A.T)
        out[t+1]=state
    return out

def main():
    OUT.mkdir(parents=True,exist_ok=False)
    start=time.perf_counter(); model=build_model(); target=next(i for i,e in enumerate(model.edges) if tuple(e)==EDGE)
    old=BRANCH/'results/g1r_p0_verified_20261113_v1/model_response_and_fits.npz'
    f=np.load(old); S=f['state_response']; C=f['cache_response']; gain=f['full_prefix_local_gain']; mean=f['full_prefix_local_mean']; precision=f['full_prefix_local_precision']
    schedule=common_schedule(model,len(SEEDS)); times=np.arange(R,D+1)
    J=channels.feature_sensitivity(S,C,model,times,False); info=J.T@precision@J
    # Reproduce the prior calibration; CAL is independent of the new five debug seeds.
    xc,yc=generate_data(model,CAL); sc=common_schedule(model,len(CAL))
    _,lc=p0.reference(model,xc,yc,CAL,sc,'clean')
    zc=(lc.local_y[:,times,1]-np.einsum('ab,stb->sta',model.H[1],lc.own[:,times,1])).reshape(len(CAL),-1)-mean
    ac=zc@gain.T; scores=np.einsum('si,ij,sj->s',ac,info,ac)
    threshold=float(np.quantile(scores,.95,method='higher'))
    x,y=generate_data(model,SEEDS); clean,clog=p0.reference(model,x,y,SEEDS,schedule,'clean')
    attack,alog=p0.reference(model,x,y,SEEDS,schedule,'replay_packet')
    metrics=[]; audit=[]; trajectories={}
    for scenario,run,log in [('clean',clean,clog),('replay',attack,alog)]:
      for s,seed in enumerate(SEEDS):
        innov=(log.local_y[s,times,1]-np.einsum('ab,tb->ta',model.H[1],log.own[s,times,1])).reshape(-1)
        theta=gain@(innov-mean); score=float(theta@info@theta); alarm=score>threshold
        theta=theta if alarm else np.zeros_like(theta)
        start_t=D+1; before=run.estimates[s,start_t].copy(); raw=log.raw[s,D].copy(); last=log.clocks[s,D].copy()
        raw_response=np.stack([np.linalg.matrix_power(model.A,D-last[e]) for e in range(len(last))])
        # Convert aligned response at D back to raw packet coordinates via a solve.
        raw_sens=np.stack([np.linalg.solve(raw_response[e],C[D,e]) for e in range(len(last))])
        joint=resume(model,y[s],schedule[s],start_t,before-np.einsum('inp,p->in',S[start_t],theta),raw-np.einsum('enp,p->en',raw_sens,theta),last,'normal',target)
        isolate=resume(model,y[s],schedule[s],start_t,before,raw,last,'isolate',target)
        # At D the suspect episode at R has been superseded; discarding it has no active cache to delete.
        drop=resume(model,y[s],schedule[s],start_t,before,raw,last,'normal',target)
        shadow=run.estimates[s]-np.einsum('tinp,p->tin',S,theta)
        if scenario=='replay':
            source=int(run.replay_source[s,R]) # OFFLINE ORACLE AND AUDIT ONLY.
            delta=run.estimates[s,source,0]-run.estimates[s,R,0]
        else: source=-1; delta=np.zeros(model.cfg['n'])
        oracle=resume(model,y[s],schedule[s],start_t,before-np.einsum('inp,p->in',S[start_t],delta),raw-np.einsum('enp,p->en',raw_sens,delta),last,'normal',target)
        err=float(np.max(np.abs(joint[start_t:]-shadow[start_t:])))
        oracle_err=float(np.max(np.abs(oracle[start_t:]-clean.estimates[s,start_t:])))
        if err>1e-9 or oracle_err>1e-9: raise AssertionError((err,oracle_err))
        methods={'yang':run.estimates[s], 'isolate':isolate,'discard_expired':drop,'shadow':shadow,'joint':joint,'oracle':oracle}
        for name,v in methods.items():
            sq=np.sum((v[start_t:261]-x[s,start_t:261,None,:])**2,axis=-1)
            metrics.append({'scenario':scenario,'seed':int(seed),'method':name,'alarm':int(alarm),'score':score,'receiver_mse':float(sq[:,1].mean()),'network_mse':float(sq.mean())})
        audit.append({'scenario':scenario,'seed':int(seed),'alarm':bool(alarm),'source_time_offline_only':source,'joint_vs_shadow_max':err,'oracle_vs_healthy_max':oracle_err,'theta':theta.tolist()})
        trajectories[f'{scenario}_{seed}_joint']=joint[start_t:261]; trajectories[f'{scenario}_{seed}_shadow']=shadow[start_t:261]
    with (OUT/'metrics.csv').open('w',newline='',encoding='utf-8') as fp:
        w=csv.DictWriter(fp,fieldnames=metrics[0].keys()); w.writeheader();w.writerows(metrics)
    np.savez_compressed(OUT/'trajectories.npz',**trajectories)
    meta={'run_id':RUN,'seeds':SEEDS.tolist(),'calibration_seeds_reused':CAL.tolist(),'threshold':threshold,'event_hypothesis':{'edge':EDGE,'reception_time':R,'decision_time':D,'source':'preselected reception window, not inferred unknown event'},'joint_protocol':'ideal atomic reliable network-wide delivery of correction, not implemented as distributed communication','message_cost':'not yet quantified; transport, synchronization, authentication assumptions unresolved','protected_hashes':{str(p.relative_to(ROOT)):digest(p) for p in [ROOT/'simulation/engine.py',ROOT/'simulation/model.py']},'code_sha256':digest(__file__),'fit_sha256':digest(old),'audits':audit,'time_seconds':time.perf_counter()-start,'limitations':['only five debug seeds','no unknown-location localization','no practical broadcast or delay model','expired packet discard is a no-op','fixed exogenous schedule only']}
    (OUT/'config_and_audit.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'run':RUN,'threshold':threshold,'max_shadow_diff':max(a['joint_vs_shadow_max'] for a in audit),'max_oracle_diff':max(a['oracle_vs_healthy_max'] for a in audit),'replay_alarms':sum(a['alarm'] for a in audit if a['scenario']=='replay'),'clean_alarms':sum(a['alarm'] for a in audit if a['scenario']=='clean')},indent=2))
if __name__=='__main__': main()
