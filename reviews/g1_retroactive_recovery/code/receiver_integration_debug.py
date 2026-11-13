"""One five-seed integration debugging session; NOT the independent final test.

The detector sees receiver-local innovation and received-packet records only.
Node write-back uses each node's own state and its own incoming raw caches.
Simulation truth/attack metadata are restricted to the oracle and evaluation.
Control traffic is delivered by reliable zero-main-step-latency micro-rounds.
"""
from __future__ import annotations
import csv, hashlib, json, sys, time
from pathlib import Path
import numpy as np

BRANCH = Path(__file__).resolve().parents[1]
ROOT = BRANCH.parents[1]
sys.path.insert(0,str(ROOT/'simulation'))
sys.path.insert(0,str(BRANCH/'code'))
from model import generate_data
from minimal_recovery_screen import build_model, common_schedule, TRAIN, CAL, R, D
import p0_verified as p0
import receiver_gls_writeback as local
from joint_recovery_debug import resume

RUN='g1r_receiver_integration_debug_20261113_v1'
OUT=BRANCH/'results'/RUN
DEBUG_SEEDS=np.arange(9911000,9911005)
BEGIN=176
RECEIVER=1
RECOVERY_END=260


def hash_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def observed_receptions(log, model, trial, begin, decision):
    """Only this receiver's recorded packet arrivals are read."""
    incoming=np.flatnonzero(model.edges[:,1]==RECEIVER)
    return [local.Reception(int(e),int(t)) for t in range(begin,decision+1)
            for e in incoming if log.clocks[trial,t,e]==t]


def innovation(log, model, trial, begin, decision):
    own=log.own[trial,begin:decision+1,RECEIVER]
    y=log.local_y[trial,begin:decision+1,RECEIVER]
    return y-np.einsum('ab,tb->ta',model.H[RECEIVER],own)


def make_normal(model,seeds):
    x,y=generate_data(model,seeds)
    schedule=common_schedule(model,len(seeds))
    _,log=p0.reference(model,x,y,seeds,schedule,'clean')
    observations=np.stack([innovation(log,model,i,BEGIN,D) for i in range(len(seeds))])
    return schedule,log,observations


def generate_detector(model):
    assert len(set(TRAIN)&set(CAL))==0
    assert not (set(DEBUG_SEEDS)&(set(TRAIN)|set(CAL)))
    st,lt,training=make_normal(model,TRAIN)
    sc,lc,calibration=make_normal(model,CAL)
    if not np.array_equal(st[0],sc[0]):
        raise ValueError('fixed training/calibration schedule mismatch')
    reception=observed_receptions(lt,model,0,BEGIN,D)
    if reception!=observed_receptions(lc,model,0,BEGIN,D):
        raise ValueError('training/calibration reception records mismatch')
    fit=local.fit_full_prefix(model,st[0],RECEIVER,BEGIN,D,reception,
                              training,calibration,ridge_fraction=.02,quantile=.95)
    return fit


def writeback_packets(model,run,log,trial,fit,decision):
    """Only node-local state/cache and received commands enter each write-back."""
    state=run.estimates[trial,D+1].copy()  # simulation driver holds physical node-local states
    raw=log.raw[trial,D].copy()            # simulation driver holds receiver-owned edge caches
    clock=log.clocks[trial,D].copy()
    packets,traffic=local.deliver_command(decision,model.edges,RECEIVER,model.cfg['N'])
    if decision is None:
        return state,raw,clock,traffic
    candidate=next(c for c in fit.candidates if c.event==decision.event)
    for node in range(model.cfg['N']):
        edges=np.flatnonzero(model.edges[:,1]==node)
        state[node],raw[edges]=local.apply_local_writeback(
            node,state[node],raw[edges],edges,packets[node],candidate,D,model.edges)
    return state,raw,clock,traffic


def discard_active_packet(model,log,trial,decision):
    """Discard only if the detected episode is still the live cache at D.

    Restore this receiving node's previous actually received cache and its
    reception time; if the episode has expired this is a no-op. There is no
    historical state replay and no access to the authentic replaced payload.
    """
    raw=log.raw[trial,D].copy(); clock=log.clocks[trial,D].copy()
    if decision is None:
        return raw,clock,False
    event=decision.event
    if clock[event.edge]!=event.time:
        return raw,clock,False
    if event.time<=0 or log.clocks[trial,event.time-1,event.edge]<0:
        raise ValueError('no earlier receiver-held cache for discard')
    raw[event.edge]=log.raw[trial,event.time-1,event.edge]
    clock[event.edge]=log.clocks[trial,event.time-1,event.edge]
    return raw,clock,True


def main():
    OUT.mkdir(parents=True,exist_ok=False)
    started=time.perf_counter()
    model=build_model()
    config={'run_id':RUN,'scope':'integration debug using same five seeds; no final test',
            'debug_seeds':DEBUG_SEEDS.tolist(),'train_seeds':TRAIN.tolist(),
            'calibration_seeds':CAL.tolist(),'window':[BEGIN,D],
            'candidate_scope':'all receiver 1 incoming receptions in [begin,decision)',
            'schedule':'existing gap8 exogenous phased schedule',
            'protocol':'4 directed control messages, ideal reliable 2 micro-rounds before next main step',
            'disclaimer':'not a statistically independent final test; no pretense of real-time transport',
            'sources':{str(p.relative_to(ROOT)):hash_file(p) for p in [Path(__file__),
               BRANCH/'code/receiver_gls_writeback.py',BRANCH/'code/joint_recovery_debug.py',
               BRANCH/'code/p0_verified.py',BRANCH/'code/compare_deghat_outputs.py',
               ROOT/'simulation/engine.py',ROOT/'simulation/model.py']}}
    (OUT/'config.json').write_text(json.dumps(config,indent=2)+'\n',encoding='utf-8')
    fit=generate_detector(model)
    meta={'threshold':fit.threshold,'candidate_events':[{'edge':c.event.edge,'time':c.event.time} for c in fit.candidates],
          'training_count':fit.training_count,'calibration_count':fit.calibration_count}
    (OUT/'fit.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
    x,y=generate_data(model,DEBUG_SEEDS); schedule=common_schedule(model,len(DEBUG_SEEDS))
    clean,clog=p0.reference(model,x,y,DEBUG_SEEDS,schedule,'clean')
    attack,alog=p0.reference(model,x,y,DEBUG_SEEDS,schedule,'replay_packet')
    target=int(np.flatnonzero(np.all(model.edges==[0,1],axis=1))[0])
    actual_event=local.Reception(target,R)
    # Oracle response is public model/schedule; true payload offset below is offline only.
    oracleS,oracle_raw=local._response(model,schedule[0],actual_event,D)
    rows=[]; logs=[]; trajectories={}
    for scenario,run,log in [('clean',clean,clog),('replay',attack,alog)]:
      for s,seed in enumerate(DEBUG_SEEDS):
        records=observed_receptions(log,model,s,BEGIN,D)
        obs=innovation(log,model,s,BEGIN,D)
        decision=local.attribute(fit,obs,records)
        initial=run.estimates[s,D+1].copy()
        raw=log.raw[s,D].copy(); clock=log.clocks[s,D].copy()
        state_j,raw_j,clock_j,traffic=writeback_packets(model,run,log,s,fit,decision)
        joint=resume(model,y[s],schedule[s],D+1,state_j,raw_j,clock_j,'normal',target)
        chosen_edge=target if decision is None else decision.event.edge
        isolate=resume(model,y[s],schedule[s],D+1,initial,raw,clock,
                       'normal' if decision is None else 'isolate',chosen_edge)
        raw_drop,clock_drop,drop_active=discard_active_packet(model,log,s,decision)
        dropped=resume(model,y[s],schedule[s],D+1,initial,raw_drop,clock_drop,'normal',target)
        shadow=run.estimates[s].copy()
        if decision is not None:
            chosen=next(c for c in fit.candidates if c.event==decision.event)
            shadow[D+1:]-=np.einsum('tinp,p->tin',chosen.state_response[D+1:],decision.theta)
        # Offline oracle only: simulator metadata and original sender states are forbidden to detector.
        delta=np.zeros(model.cfg['n'])
        if scenario=='replay':
            source=int(run.replay_source[s,R])
            if source<0 or not run.sends[s,source,0] or source>=R:
                raise AssertionError('oracle replay source is not a past sent packet')
            delta=run.estimates[s,source,0]-run.estimates[s,R,0]
        state_o=initial-np.einsum('inp,p->in',oracleS[D+1],delta)
        raw_o=raw-np.einsum('enp,p->en',oracle_raw,delta)
        oracle=resume(model,y[s],schedule[s],D+1,state_o,raw_o,clock,'normal',target)
        joint_shadow=float(np.max(np.abs(joint[D+1:]-shadow[D+1:])))
        oracle_nominal=float(np.max(np.abs(oracle[D+1:]-clean.estimates[s,D+1:])))
        if joint_shadow>1e-9 or oracle_nominal>1e-9:
            raise AssertionError((joint_shadow,oracle_nominal))
        methods={'yang':run.estimates[s],'isolate':isolate,'discard':dropped,
                 'shadow':shadow,'joint':joint,'oracle':oracle}
        for name,traj in methods.items():
            squared=np.sum((traj[D+1:RECOVERY_END+1]-x[s,D+1:RECOVERY_END+1,None,:])**2,axis=-1)
            rows.append({'scenario':scenario,'seed':int(seed),'method':name,
                         'receiver_mse':float(squared[:,RECEIVER].mean()),
                         'network_mse':float(squared.mean()),
                         'alarm':decision is not None,
                         'extra_payload_bytes':sum(t['payload_bytes'] for t in traffic) if name=='joint' else 0})
        logs.append({'scenario':scenario,'seed':int(seed),'alarm':decision is not None,
          'attributed_edge':None if decision is None else decision.event.edge,
          'attributed_time':None if decision is None else decision.event.time,
          'correct_attribution_offline':bool(scenario=='replay' and decision is not None and decision.event==actual_event),
          'active_discard':drop_active,'traffic':traffic,'joint_shadow_max':joint_shadow,
          'oracle_healthy_max':oracle_nominal})
        for name,traj in methods.items(): trajectories[f'{scenario}_{seed}_{name}']=traj[D+1:RECOVERY_END+1]
    with (OUT/'metrics.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    np.savez_compressed(OUT/'recovery_trajectories.npz',**trajectories)
    (OUT/'audit.json').write_text(json.dumps({'cases':logs,'elapsed_seconds':time.perf_counter()-started},indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'run_id':RUN,'fit':meta,'cases':logs},indent=2))

if __name__=='__main__':
    main()
