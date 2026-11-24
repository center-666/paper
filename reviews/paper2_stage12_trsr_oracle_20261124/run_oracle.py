"""Validate the TRSR identities and evaluate six policies on paired V2 records."""
import csv
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import platform
import sys

import numpy as np
import scipy
from scipy.stats import t as student_t

from trsr import Filter, Packet, State, recovery_weight, replay

HERE = Path(__file__).resolve().parent
STAGE6 = HERE.parent / 'paper2_stage6_vector_correction_20261122'
sys.path.insert(0, str(STAGE6))
from exact_linear import add, matmul, matrix, sub, transpose, update

POLICIES = ('M0', 'M1', 'M2', 'M3', 'M4', 'M5')


def preflight(spec):
    model = spec['model']
    prior_model = json.loads((STAGE6/'model.json').read_text(encoding='utf8'))
    for key, legacy in [('A','A'),('C','C'),('Q','Q'),('R','R'),('Z','Z'),('W','W'),
                        ('P0','P0_prior'),('feedback_half_width','quantization_half_width')]:
        assert model[key] == prior_model[legacy]
    A,C,Q = (matrix(model[k]) for k in ('A','C','Q'))
    R,Z = F(model['R']),F(model['Z'])
    exact_checks = 0
    for bias,start,pattern in [(F(1,4),0,'101101'),(F(-1,10),2,'011011'),(F(1,10),1,'110101')]:
        prior = matrix(model['P0'])
        m, candidate, H = ([[F(0)],[F(0)]] for _ in range(3))
        for t,flag in enumerate(pattern):
            sent = flag == '1'
            post,K,T = update(prior,C,R if sent else R+1/Z)
            active = start <= t < start+3 and sent
            obs = F(t-2,12) if sent else F(1,100)
            mpost = add(matmul(T,m),matmul(K,[[obs]]))
            cpost = add(matmul(T,candidate),matmul(K,[[obs-bias*active]]))
            Hpost = add(matmul(T,H),matmul(K,[[int(active)]]))
            assert sub(mpost,cpost) == [[bias*x[0]] for x in Hpost]
            m,candidate,H = (matmul(A,z) for z in (mpost,cpost,Hpost))
            prior = add(matmul(matmul(A,post),transpose(A)),Q)
            exact_checks += 1

    kf = Filter(model)
    log = [Packet(.01,.32),Packet(-.01,None),Packet(.004,.7),Packet(.002,-.1)]
    def checked_replay(seq,checkpoint_time=-1,prior=kf.initial):
        return replay(kf,seq,checkpoint_time,prior,1,3)
    result = checked_replay(log)
    changed = log.copy()
    changed[2] = Packet(log[2].center,125.)
    assert np.array_equal(result.mean,checked_replay(changed).mean)
    assert np.array_equal(result.covariance,checked_replay(changed).covariance)
    for index,packet in [(1,Packet(.15,None)),(3,Packet(.002,.4))]:
        changed = log.copy()
        changed[index] = packet
        assert not np.allclose(result.mean,checked_replay(changed).mean)
    first,_ = kf.update(kf.initial,log[0])
    assert np.array_equal(checked_replay(log,0,kf.predict(first)).mean,result.mean)
    # The scalar example in the proposal; zero, partial, full, and null-action cases.
    for h,ds,expected in [(.6,[.4,.8],2/3),(.6,[-.2,.8],0),(.6,[1.,2.],1),(0,[.4],0)]:
        lam,bound = recovery_weight(np.array([h]),np.array(ds)[:,None],np.eye(1))
        assert math.isclose(lam,expected,abs_tol=2e-15)
        assert math.isclose(bound,min(x*x-(x-lam*h)**2 for x in ds),abs_tol=2e-15)
    return {'exact_response_updates':exact_checks,'replay_checks':5,'weight_examples':4}


def episode(kf, spec, group, number):
    seed = spec['master_seed']
    streams = np.random.SeedSequence([seed,group,number]).spawn(3)
    physics, phase_rng, trigger_rng = [np.random.default_rng(s) for s in streams]
    onset_rng = np.random.default_rng(np.random.SeedSequence([seed,group,number,177]))
    start = int(onset_rng.integers(40,81))
    duration = spec['cells'][group]['duration']
    bias = spec['cells'][group]['amplitude']
    end = start+duration
    horizon = spec['protocol']['post_stop_steps']
    stride = spec['protocol']['checkpoint_stride']
    delta = float(spec['model']['feedback_half_width'])
    proc_factor = np.linalg.cholesky(kf.Q)
    x = np.linalg.cholesky(kf.initial.covariance) @ physics.normal(size=2)
    monitor = corrected = kf.initial
    # All states below are priors at loop entry. Save posterior s as the
    # equivalent prior for s+1. The initial checkpoint precedes the first packet.
    checkpoints = {-1:kf.initial}
    history = []
    H = np.zeros(2)
    summed_loss = np.zeros(6)
    paired_gain = np.zeros(6)
    conditional = np.zeros(6)
    early_gain = np.zeros(6)
    counts = np.zeros(3,dtype=int)
    total_weight = 0.
    attack_sends = 0
    max_response_error = 0.
    max_scaled_error = 0.
    for t in range(end+horizon):
        if t == end:
            anchor = max(s for s in checkpoints if s < start)
            recovery = replay(kf,history,anchor,checkpoints[anchor],start,end)
            rollback = np.linalg.matrix_power(kf.A,end-anchor-1) @ checkpoints[anchor].mean
        prediction = kf.C @ monitor.mean
        phase = 0. if t == 0 else phase_rng.uniform(-delta,delta)
        center = phase + 2*delta*math.floor((prediction-phase+delta)/(2*delta))
        y = kf.C @ x + math.sqrt(kf.R)*physics.normal()
        sent = trigger_rng.random() > math.exp(-.5*kf.Z*(y-center)**2)
        active_send = sent and start <= t < end
        attack_sends += int(active_send)
        offset = bias if active_send else 0.
        packet = Packet(center,y+offset if sent else None)
        post,gain = kf.update(monitor,packet)
        oracle_packet = Packet(center,packet.payload-offset if sent else None)
        corrected_post,_ = kf.update(corrected,oracle_packet)
        Hpost = H - gain*(kf.C@H) + gain*int(active_send)
        d = bias*Hpost
        reference_error = np.max(np.abs((post.mean-corrected_post.mean)-d))
        max_response_error = max(max_response_error,reference_error)
        # Both output components use the first-component innovation. Cancellation
        # there can affect a small second component in this coupled V2 system.
        scale = max(1.,np.max(np.abs(monitor.mean)),np.max(np.abs(post.mean)),abs(y))
        max_scaled_error = max(max_scaled_error,reference_error/scale)
        assert reference_error/scale < 128*np.finfo(float).eps
        monitor = kf.predict(post)
        corrected = kf.predict(corrected_post)
        H = kf.A @ Hpost
        if t < end:
            history.append(packet)
            if t % stride == 0:
                checkpoints[t] = monitor
        else:
            rpost,_ = kf.update(recovery,packet)
            h = post.mean-rpost.mean
            lam,bound = recovery_weight(h,[d],kf.W)
            outputs = np.stack((post.mean,rollback,rpost.mean,post.mean-.5*h,post.mean-lam*h,post.mean-d))
            # Compute paired differences before summation. Verify the gain
            # against the independently corrected receiver on the same record.
            errors = outputs-x
            loss = np.einsum('ij,jk,ik->i',errors,kf.W,errors)
            offsets = outputs-post.mean
            gains = -2*(offsets @ (kf.W @ errors[0])) - np.einsum('ij,jk,ik->i',offsets,kf.W,offsets)
            cond = -2*(offsets @ (kf.W @ d)) - np.einsum('ij,jk,ik->i',offsets,kf.W,offsets)
            assert abs(cond[4]-bound) < 2e-11 and cond[4] >= -2e-11
            assert cond[4] <= d @ kf.W @ d + 2e-11
            summed_loss += loss
            paired_gain += gains
            conditional += cond
            if t < end+20:
                early_gain += gains
            total_weight += lam
            counts[0 if lam==0 else 2 if lam==1 else 1] += 1
            recovery = kf.predict(rpost)
            rollback = kf.A @ rollback
        x = kf.A @ x + proc_factor @ physics.normal(size=2)
    assert sum(counts) == horizon and np.all(np.isfinite(summed_loss))
    data = {'group':group,'episode':number,'b':bias,'duration':duration,'start':start,
            'first_clean':end,'checkpoint':anchor,'suspect_sends':attack_sends,
            'mean_lambda':total_weight/horizon,'zero':counts[0],'partial':counts[1],'full':counts[2],
            'max_response_error':max_response_error,'max_scaled_error':max_scaled_error}
    for i,name in enumerate(POLICIES):
        data[name+'_loss'] = summed_loss[i]
        data[name+'_gain'] = paired_gain[i]
        data[name+'_first20_gain'] = early_gain[i]
        data[name+'_conditional_gain'] = conditional[i]
    return data


def summary(groups):
    """Equal-cell paired mean, variance and diagnostic t interval."""
    means = [np.mean(g) for g in groups]
    terms = np.array([np.var(g,ddof=1)/len(g) for g in groups])/len(groups)**2
    avg = float(np.mean(means))
    se = math.sqrt(sum(terms))
    if se == 0:
        return {'mean':avg,'se':0.,'t95':[avg,avg]}
    df = terms.sum()**2 / sum(v*v/(len(g)-1) for v,g in zip(terms,groups))
    radius = float(student_t.ppf(.975,df))*se
    return {'mean':avg,'se':se,'t95':[avg-radius,avg+radius]}


def describe(groups):
    out = {}
    for name in POLICIES:
        out[name] = {stat:summary([[row[name+'_'+stat] for row in g] for g in groups])
                     for stat in ('loss','gain','conditional_gain','first20_gain')}
    return out


def main():
    spec = json.loads((HERE/'protocol.json').read_text(encoding='utf8'))
    checks = preflight(spec)
    if sys.argv[1:] == ['--check']:
        print(checks)
        return
    if sys.argv[1:]:
        raise ValueError('Only --check is supported')
    model = Filter(spec['model'])
    groups = []
    for i,cell in enumerate(spec['cells']):
        group = [episode(model,spec,i,j) for j in range(spec['episodes_per_cell'])]
        groups.append(group)
        print('Completed cell',cell,flush=True)
    rows = [row for group in groups for row in group]
    with (HERE/'episodes.csv').open('w',newline='',encoding='utf8') as stream:
        writer = csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    out = {'checks':checks,'n':len(rows),'by_cell':[describe([g]) for g in groups],
           'equal_cell':describe(groups),'python':platform.python_version(),'numpy':np.__version__,
           'scipy':scipy.__version__,'lambda_counts':[int(sum(r[s] for r in rows)) for s in ('zero','partial','full')],
           'max_response_error':float(max(r['max_response_error'] for r in rows)),
           'max_scaled_error':float(max(r['max_scaled_error'] for r in rows)),
           'sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in
                     [HERE/'trsr.py',Path(__file__),HERE/'protocol.json',STAGE6/'model.json',
                      STAGE6/'exact_linear.py',HERE/'episodes.csv']}}
    (HERE/'oracle_results.json').write_text(json.dumps(out,indent=2,allow_nan=False)+'\n',
                                           encoding='utf8',newline='\n')
    print('M4 gain',out['equal_cell']['M4']['gain'])


if __name__ == '__main__':
    main()
