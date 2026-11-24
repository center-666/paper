"""Frozen Oracle pilot for synthetic V2 receiver recovery; offline scoring only."""
import argparse
import csv
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import platform
import sys
import time

import numpy as np
import scipy
from scipy.stats import t as student_t

from receiver import V2Filter, decide

BASE = Path(__file__).resolve().parents[1]
PROTOCOL = BASE/'trsr_protocol.json'
MODEL = BASE.parent/'paper2_stage6_vector_correction_20261122'/'model.json'
METHODS = [f'M{i}' for i in range(6)]
SCALAR_EPS = np.finfo(float).eps


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_csv(path, rows):
    with path.open('w', newline='', encoding='utf8') as out:
        writer = csv.DictWriter(out, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf8', newline='\n')


def exogenous(kf, root, cell, count, steps, delta):
    """Each independent episode owns three child generators. Its sham reuses that draw."""
    n = steps
    measurements = np.empty((n,count))
    positions = np.empty((n,count,2))
    offsets = np.zeros((n,count))
    tosses = np.empty((n,count))
    for run in range(count):
        states, phase, trigger = [np.random.default_rng(s) for s in
                                  np.random.SeedSequence([root,cell,run]).spawn(3)]
        x = np.linalg.cholesky(kf.P0) @ states.normal(size=2)
        process = states.normal(size=(steps,2)) @ np.linalg.cholesky(kf.Q).T
        sensor = math.sqrt(kf.R)*states.normal(size=steps)
        offsets[1:,run] = phase.uniform(-delta, delta, size=steps-1)
        tosses[:,run] = trigger.random(size=steps)
        for i in range(steps):
            positions[i,run] = x
            measurements[i,run] = kf.C @ x + sensor[i]
            x = kf.A @ x + process[i]
    return positions, measurements, offsets, tosses


def make_batch(kf, root, cell, n, k0, duration, bias, horizon, stride, delta):
    """Return offline traces for a cell. First n rows are faulty, next n matched healthy."""
    k1 = k0+duration
    steps = k1+horizon
    x, y, offsets, tosses = exogenous(kf,root,cell,n,steps,delta)
    count = 2*n
    biases = np.r_[np.full(n,bias),np.zeros(n)]
    mean,cov = kf.initial(count)
    correct, pc = kf.initial(count)
    H = np.zeros_like(mean)
    record_center = np.empty((steps,count))
    record_payload = np.empty((steps,count))
    checkpoints = {-1:kf.initial(count)}
    loss = np.zeros((horizon,count,6))
    gains = np.zeros_like(loss)
    conditional = np.zeros_like(loss)
    actions = np.zeros(loss.shape, bool)
    weights = np.zeros((horizon,count))
    fallback = np.zeros((horizon,count), bool)
    cosine = np.zeros((horizon,count))
    energy = np.zeros_like(cosine)
    attack_monitor_loss = np.zeros(count)
    attack_sends = np.zeros(count,int)
    example = []
    max_err = 0.
    max_scaled = 0.
    max_gain_discrepancy = 0.
    rebuild_ns = 0
    replay_update_ns = 0
    decision_ns = 0
    core_begin = time.perf_counter_ns()
    for t in range(steps):
        if t == k1:
            anchor = max(s for s in checkpoints if s<k0)
            mcp, pcp = checkpoints[anchor]
            tick = time.perf_counter_ns()
            replay,pr = kf.replay(anchor,mcp,pcp,record_center[:t],record_payload[:t],k0,k1)
            rebuild_ns = time.perf_counter_ns()-tick
            exponent = t if anchor == -1 else t-anchor
            open_loop = mcp @ np.linalg.matrix_power(kf.A,exponent).T
        obs = np.tile(y[t],2)
        center = mean @ kf.C + np.tile(offsets[t],2)
        silent_probability = np.exp(-0.5*kf.Z*np.square(obs-center))
        sent = np.tile(tosses[t],2)>silent_probability
        active = k0<=t<k1
        payload = np.where(sent,obs+biases*active,np.nan)
        record_center[t],record_payload[t] = center,payload
        monitor,postP,K = kf.update(mean,cov,center,payload)
        # Independent oracle filter uses only the same received record and the
        # declared Oracle fixture's known parameter, never the hidden measurement.
        corrected,post_correct,_ = kf.update(correct,pc,center,payload-biases*active)
        H = kf.response(H,K,sent,active)
        d = H*biases[:,None]
        mismatch = np.max(np.abs((monitor-corrected)-d),axis=1)
        scale = np.maximum(1.,np.maximum(np.max(np.abs(monitor),axis=1),np.abs(obs)))
        max_err = max(max_err, float(mismatch.max()))
        max_scaled = max(max_scaled,float((mismatch/scale).max()))
        truth = np.tile(x[t],(2,1))
        monitor_error = monitor-truth
        base_loss = np.einsum('ni,ij,nj->n',monitor_error,kf.W,monitor_error)
        if active:
            attack_monitor_loss += base_loss
            attack_sends += sent
        if t < k1 and t % stride == 0:
            checkpoints[t] = monitor.copy(),postP.copy()
        if t >= k1:
            i = t-k1
            tick = time.perf_counter_ns()
            replay_post,rp,_ = kf.update(replay,pr,center,payload)
            replay,pr = kf.predict(replay_post,rp)
            replay_update_ns += time.perf_counter_ns()-tick
            h = monitor-replay_post
            tick = time.perf_counter_ns()
            published,weights[i],lower,fallback[i] = decide(monitor,replay_post,d[:,None,:],kf.W)
            decision_ns += time.perf_counter_ns()-tick
            outputs = np.stack([monitor,open_loop,replay_post,monitor-.5*h,published,monitor-d],axis=1)
            offset = outputs-monitor[:,None,:]
            sq = np.einsum('nki,ij,nkj->nk',offset,kf.W,offset)
            gains[i] = -2*np.einsum('nki,ij,nj->nk',offset,kf.W,monitor_error)-sq
            conditional[i] = -2*np.einsum('nki,ij,nj->nk',offset,kf.W,d)-sq
            e = outputs-truth[:,None,:]
            loss[i] = np.einsum('nki,ij,nkj->nk',e,kf.W,e)
            actions[i] = np.any(outputs!=monitor[:,None,:], axis=2)
            energy[i] = np.einsum('ni,ij,nj->n',d,kf.W,d)
            # Describes the unconstrained nonnegative ray using the same direction.
            q = np.einsum('ni,ij,nj->n',h,kf.W,h)
            g = np.einsum('ni,ij,nj->n',h,kf.W,d)
            cosine[i] = np.divide(np.maximum(0.,g)**2, q, out=np.zeros_like(q),where=q>0)
            max_gain_discrepancy = max(max_gain_discrepancy,float(np.max(np.abs(conditional[i,:,4]-lower))))
            if np.any(conditional[i,:,4] < -1e-12) or np.any(conditional[i,:,4] > energy[i]+1e-12):
                raise ArithmeticError("Conditional gain outside Oracle bounds")
            open_loop = open_loop @ kf.A.T
        if cell==7:
            row={'t':t,'start':k0,'stop':k1,'sent':int(sent[0]),'center':center[0],
                 'truth0':truth[0,0],'truth1':truth[0,1],'M0_x0':monitor[0,0],'M0_x1':monitor[0,1]}
            for m,name in enumerate(METHODS[1:],1):
                mvalue = outputs[0,m] if t>=k1 else monitor[0]
                row[name+'_x0'],row[name+'_x1'] = mvalue
            row['lambda'] = weights[t-k1,0] if t>=k1 else 0.
            row['oracle_energy'] = float(d[0]@kf.W@d[0])
            example.append(row)
        mean,cov = kf.predict(monitor,postP)
        correct,pc = kf.predict(corrected,post_correct)
    if max_scaled > 128*SCALAR_EPS or max_gain_discrepancy > 1e-12:
        raise ArithmeticError(f"Oracle identity mismatch ({max_scaled}, {max_gain_discrepancy})")
    if not (np.isfinite(loss).all() and np.isfinite(gains).all() and np.isfinite(conditional).all()):
        raise ArithmeticError("Nonfinite score")
    group_data = dict(loss=loss,gain=gains,conditional=conditional,actions=actions,weights=weights,
                      fallback=fallback,cosine=cosine,energy=energy,attack_monitor_loss=attack_monitor_loss,
                      attack_sends=attack_sends,checkpoint=anchor,post_steps=horizon)
    cost = {'simulation_and_oracle_batch_ms':(time.perf_counter_ns()-core_begin)/1e6,
            'batch_size_trajectories':count,'steps_including_before_restore':steps,
            'replay_rebuild_batch_ms':rebuild_ns/1e6,'replay_update_batch_ms_total':replay_update_ns/1e6,
            'risk_decision_batch_ms_total':decision_ns/1e6,
            'max_abs_oracle_mean_error':max_err,'max_scale_relative_oracle_mean_error':max_scaled,
            'max_risk_identity_delta':max_gain_discrepancy}
    return group_data,cost,example


def reduce_windows(data, cell, duration, bias, onset, n, delays, primary, secondary):
    """All five delays reuse the same output-only proposals and fixed physical path."""
    out = []
    curve = []
    for group, condition in enumerate(('attack','sham')):
        idx = slice(group*n,(group+1)*n)
        win_data = {k:data[k][:,idx] for k in ('loss','gain','conditional','actions','weights','fallback','cosine','energy')}
        for delay in delays:
            for label,start,end in [('stop64',0,primary),('stop512',0,secondary),
                                    ('activation64',delay,delay+primary)]:
                live = slice(min(end,max(delay,start)),end)
                sum_gain = win_data['gain'][live].sum(axis=0)
                sum_cond = win_data['conditional'][live].sum(axis=0)
                sum_actions = win_data['actions'][live].sum(axis=0)
                # Use separate loss summation (squared residuals). Before activation
                # all methods publish the same monitor estimate.
                before = win_data['loss'][start:live.start,:,0].sum(axis=0)
                sum_loss = before[:,None]+win_data['loss'][live].sum(axis=0)
                w = win_data['weights'][live]
                weights = w.sum(axis=0)
                full = (w==1).sum(axis=0)
                partial = ((w>0)&(w<1)).sum(axis=0)
                zero = (w==0).sum(axis=0)
                fb = win_data['fallback'][live].sum(axis=0)
                cosine = win_data['cosine'][live].sum(axis=0)
                oracle_energy = win_data['energy'][start:end].sum(axis=0)
                available_energy = win_data['energy'][live].sum(axis=0)
                for i in range(n):
                    row = dict(cell=cell, episode=i, condition=condition, delay=delay, window=label,
                               b=bias if group==0 else 0., matched_b=bias, duration=duration,start=onset,
                               stop=onset+duration, post_steps=end-start, eligible=end-live.start,
                               lambda_sum=weights[i],partial=int(partial[i]),full=int(full[i]),
                               weight_zero=int(zero[i]),fallback=int(fb[i]),cosine_energy=cosine[i],
                               oracle_energy=oracle_energy[i],available_oracle_energy=available_energy[i],
                               attack_monitor_loss=data['attack_monitor_loss'][group*n+i],checkpoint=data['checkpoint'],
                               attack_sends=int(data['attack_sends'][group*n+i]),status='ok')
                    for j,name in enumerate(METHODS):
                        row[name+'_loss'] = sum_loss[i,j]
                        row[name+'_gain'] = sum_gain[i,j]
                        row[name+'_conditional'] = sum_cond[i,j]
                        row[name+'_actions'] = int(sum_actions[i,j])
                    out.append(row)
        for t in range(secondary):
            row={'cell':cell,'b':bias,'duration':duration,'condition':condition,'post_step':t,
                 'sample_size':n,'mean_lambda':float(win_data['weights'][t].mean()),
                 'mean_ray_energy':float(win_data['cosine'][t].mean()),'mean_oracle_energy':float(win_data['energy'][t].mean())}
            for j,name in enumerate(METHODS):
                row[name+'_mean_loss'] = float(win_data['loss'][t,:,j].mean())
                row[name+'_mean_gain'] = float(win_data['gain'][t,:,j].mean())
                row[name+'_mean_conditional'] = float(win_data['conditional'][t,:,j].mean())
            curve.append(row)
    return out,curve


def stats(groups):
    avg = float(np.mean([np.mean(x) for x in groups]))
    terms = [np.var(x,ddof=1)/len(x)/len(groups)**2 for x in groups]
    se = math.sqrt(sum(terms))
    if se == 0:
        return {'mean':avg,'se':0.,'t95':[avg,avg]}
    df = sum(terms)**2 / sum(v*v/(len(x)-1) for v,x in zip(terms,groups))
    r = float(student_t.ppf(.975,df))*se
    return {'mean':avg,'se':se,'t95':[avg-r,avg+r]}


def summarize(rows):
    by_group = {}
    for row in rows:
        key = (row['condition'],row['delay'],row['window'])
        by_group.setdefault(key,{}).setdefault(row['cell'],[]).append(row)
    result = {}
    for (condition,delay,label),groups in by_group.items():
        aggregate={}
        for name in METHODS:
            metrics={}
            for kind in ('loss','gain','conditional'):
                metrics[kind] = stats([[r[name+'_'+kind] for r in g] for g in groups.values()])
            metrics['loss_increase_fraction'] = float(np.mean([r[name+'_gain']<0 for g in groups.values() for r in g]))
            metrics['no_action_fraction'] = float(np.mean([r[name+'_actions']==0 for g in groups.values() for r in g]))
            aggregate[name]=metrics
        cell_results = {}
        for k,g in groups.items():
            oracle = sum(r['oracle_energy'] for r in g)
            projected = sum(r['M4_conditional'] for r in g)
            cell_results[k]={'b':g[0]['matched_b'],'duration':g[0]['duration'],'n':len(g),
                             'M4_gain':stats([[r['M4_gain'] for r in g]]),
                             'M4_conditional':stats([[r['M4_conditional'] for r in g]]),
                             'M5_energy_mean':oracle/len(g),
                             'opportunity_captured':projected/oracle if oracle else None}
        result[f'{condition}/{delay}/{label}']={'overall':aggregate,'cells':cell_results}
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=BASE/'results'/'oracle_v1')
    args=parser.parse_args()
    destination=args.output
    if destination.exists():
        raise FileExistsError(f"Choose a new run directory: {destination}")
    spec=json.loads(PROTOCOL.read_text(encoding='utf8'))
    p=spec['oracle_pilot']
    n=p['episodes_per_cell']
    root=p['seed_root_proposed']
    k0=spec['attack']['onset']
    primary=p['post_stop_primary_steps']
    secondary=p['secondary_steps']
    delays=p['delay_steps']
    kf=V2Filter(json.loads(MODEL.read_text(encoding='utf8')))
    delta=float(json.loads(MODEL.read_text(encoding='utf8'))['quantization_half_width'])
    cells=[(b,d) for b in spec['attack']['pilot_amplitudes'] for d in spec['attack']['durations']]
    cost=[]
    rows=[]
    curves=[]
    example=[]
    tick=time.perf_counter()
    for cell,(b,duration) in enumerate(cells):
        data,timing,ex=make_batch(kf,root,cell,n,k0,duration,b,secondary,spec['checkpoint_period'],delta)
        scored,curve=reduce_windows(data,cell,duration,b,k0,n,delays,primary,secondary)
        rows.extend(scored)
        curves.extend(curve)
        example.extend(ex)
        cost.append(timing)
        print('completed cell',cell,b,duration,flush=True)
    summary=summarize(rows)
    # Write through a sibling directory so partial runs never look complete.
    import tempfile
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as parent:
        scratch=Path(parent)/'complete'
        scratch.mkdir()
        series=scratch/'episodes.csv.gz'
        with series.open('wb') as binary, gzip.GzipFile(filename='',fileobj=binary,mode='wb',mtime=0) as zipped:
            with io.TextIOWrapper(zipped,encoding='utf8',newline='') as out:
                writer=csv.DictWriter(out,fieldnames=list(rows[0]),lineterminator='\n')
                writer.writeheader()
                writer.writerows(rows)
        save_csv(scratch/'timecourse.csv',curves)
        save_csv(scratch/'example.csv',example)
        write_json(scratch/'summary.json',summary)
        write_json(scratch/'manifest.json',{'protocol':str(PROTOCOL.relative_to(BASE)),'seed_root':root,
                  'independent_pairs':n*len(cells),'attack_sham_trajectories':2*n*len(cells),
                  'rows':len(rows),'failures':0,'timings':cost,'wall_seconds':time.perf_counter()-tick,
                  'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__,
                  'representative':'cell 7 episode 0 specified before run',
                  'sha256':{i.name:digest(i) for i in [Path(__file__),Path(__file__).with_name('receiver.py'),MODEL,
                    PROTOCOL,BASE/'oracle_registration.md',series,scratch/'timecourse.csv',scratch/'example.csv',scratch/'summary.json']}})
        scratch.rename(destination)
    for delay in (0,20):
        s=summary[f'attack/{delay}/stop64']['overall']
        print('delay',delay,'M4 gain',s['M4']['gain'],'M4 conditional',s['M4']['conditional']['mean'])


if __name__=='__main__':
    main()
