"""Pure offline loss evaluation; only accepts already persisted proposal tickets."""
from __future__ import annotations
import numpy as np
from .storage import PersistedProposal


def losses(e0, delta, u, u0):
    e0,delta,u,u0=(np.asarray(v,dtype=float) for v in (e0,delta,u,u0))
    if any(a.shape!=(2,) or not np.isfinite(a).all() for a in (e0,delta,u,u0)):
        raise ValueError('loss inputs require finite two-dimensional vectors')
    sq=lambda x:float(x@x)
    L0=sq(e0); La=sq(e0+delta); L0u=sq(e0-u0); Lau=sq(e0+delta-u)
    pollution=2*float(delta@u)-sq(u); cross=2*float(e0@u)
    attack_gain=La-Lau; healthy_gain=L0-L0u; net=attack_gain-healthy_gain
    if not np.isclose(attack_gain,pollution+cross,rtol=1e-11,atol=1e-12):
        raise ValueError('loss decomposition identity failed')
    return {'L0':L0,'La':La,'L0_u':L0u,'La_u':Lau,'attack_gain':attack_gain,
            'healthy_gain':healthy_gain,'normal_risk_change':-healthy_gain,
            'pollution_gain':pollution,'healthy_cross_term':cross,'net_gain':net}


def evaluate(truth, proposal, healthy_proposal, *, cap):
    if type(proposal) is not PersistedProposal or type(healthy_proposal) is not PersistedProposal:
        raise TypeError('offline truth joins only after proposal is persisted')
    p=proposal.read(); hp=healthy_proposal.read()
    if p['method']!=hp['method']: raise ValueError('paired method differs')
    u=np.asarray(p['final_action']); u0=np.asarray(hp['final_action'])
    x=np.asarray(truth.true_state); h=np.asarray(truth.healthy_estimate); a=np.asarray(truth.attacked_estimate)
    if any(v.shape!=(2,) or not np.isfinite(v).all() for v in (x,h,a)):
        raise ValueError('invalid target states')
    delta=a-h
    if not np.allclose(delta,truth.delta,rtol=0,atol=1e-12): raise ValueError('Delta != attacked - healthy')
    for payload in (p,hp):
        action=np.asarray(payload['final_action'],dtype=float); norm=float(np.linalg.norm(action))
        if not np.isfinite(action).all() or norm>cap+1e-12: raise ValueError('invalid action')
        if (payload['proposal_status']!='VALID' or payload['gate_status']!='EXECUTED') and norm>1e-12:
            raise ValueError('rejected proposal has nonzero action')
    metrics=losses(h-x,delta,u,u0)
    role='normal' if truth.group=='normal' else ('paired_healthy' if truth.event is None else 'attack')
    return {'seed':truth.seed,'role':role,'method':p['method'],'event':truth.event,'age':truth.age,
            'true_state':x.tolist(),'healthy_estimate':h.tolist(),'attacked_estimate':a.tolist(),
            'delta':delta.tolist(),'e0':(h-x).tolist(),'u':u.tolist(),'u0':u0.tolist(),
            'corrected_attacked_estimate':(a-u).tolist(),'corrected_healthy_estimate':(h-u0).tolist(),
            'corrected_attack_error':(a-u-x).tolist(),'corrected_healthy_error':(h-u0-x).tolist(),
            'pairing_sha256':truth.pairing_sha256,'replay_source_time':truth.replay_source_time,
            'actual_replay_age':truth.actual_replay_age,'cache_replacement_time':truth.cache_replacement_time,
            'raw_status':p['raw_status'],'proposal_status':p['proposal_status'],'gate_status':p['gate_status'],
            'score':p['score'],'threshold':p['threshold'],'action_norm':float(np.linalg.norm(u)),
            'nonzero':bool(np.linalg.norm(u)>1e-12),'saturated':bool(np.linalg.norm(u)>=cap-1e-12),
            'proposal_file':proposal.path.name,'proposal_file_sha256':proposal.sha256,
            'healthy_proposal_file':healthy_proposal.path.name,'healthy_proposal_file_sha256':healthy_proposal.sha256,
            **metrics}
