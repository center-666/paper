"""Seed-clustered E3 inference. No RNG is touched until explicit statistics execution."""
from __future__ import annotations
import json
import numpy as np

YANG='yang'
SET='set_constrained_chebyshev'


def resample_indices(seed, n, resamples):
    return np.random.default_rng(seed).integers(0,n,size=(resamples,n))


def worst_event_margin(baseline, candidate, indices):
    # Inputs: seed x event. E(max loss) would be a different quantity.
    b=np.asarray(baseline); s=np.asarray(candidate)
    if b.shape!=s.shape or b.ndim!=2: raise ValueError('seed x event required')
    point=.99*b.mean(axis=0).max()-s.mean(axis=0).max()
    boot=np.array([.99*b[ix].mean(axis=0).max()-s[ix].mean(axis=0).max() for ix in indices])
    return float(point),boot


def interval(values, alpha=.05):
    return np.quantile(values,[alpha/2,1-alpha/2],method='linear').tolist()


def gate_decision(yang_gain, margins, net_advantages):
    if yang_gain<.01 or any(m['point']<0 or m['lower_97_5']<0 for m in margins.values()):
        return 'NO_GO_PERFORMANCE'
    if any(n['point']<=0 and n['interval_95'][1]<=0 for n in net_advantages.values()):
        return 'NO_MECHANISM_GO'
    if any(n['interval_95'][0]<=0 for n in net_advantages.values()):
        return 'INCONCLUSIVE'
    return 'GO_PROTOCOL_E3'


def summarize(config, rows, *, indices=None, formal=False, receipt=None):
    if formal:
        from .authorization_guard import require
        require(config, receipt)
    methods=tuple(config.methods)+(YANG,)
    n=len(config.attack_seeds); nn=len(config.normal_seeds)
    index={(r['role'],int(r['seed']),tuple(r['event']) if r['event'] is not None else None,r['age'],r['method']):r for r in rows}
    expected=set()
    for seed in config.normal_seeds:
        for m in config.methods: expected.add(('normal',seed,None,None,m))
    for seed in config.attack_seeds:
        for m in config.methods:
            expected.add(('paired_healthy',seed,None,None,m))
            for e in config.events:
                for a in config.ages: expected.add(('attack',seed,e,a,m))
    if len(index)!=len(rows) or set(index)!=expected:
        raise ValueError('missing, duplicate, or unplanned E3 rows; no rows may be deleted')
    shape=(n,len(config.events),len(config.ages),len(methods))
    losses=np.empty(shape); clean=np.empty((n,len(methods))); normal=np.empty((nn,len(methods)))
    net=np.empty(shape); pollution=np.empty(shape); cross=np.empty(shape)
    for i,seed in enumerate(config.attack_seeds):
        pairing=set()
        for j,e in enumerate(config.events):
            for k,a in enumerate(config.ages):
                for l,m in enumerate(config.methods):
                    r=index['attack',seed,e,a,m]; pairing.add(r['pairing_sha256'])
                    losses[i,j,k,l]=r['La_u']; net[i,j,k,l]=r['net_gain']; pollution[i,j,k,l]=r['pollution_gain']; cross[i,j,k,l]=r['healthy_cross_term']
                losses[i,j,k,-1]=r['La']; net[i,j,k,-1]=pollution[i,j,k,-1]=cross[i,j,k,-1]=0
        for l,m in enumerate(config.methods):
            r=index['paired_healthy',seed,None,None,m]; pairing.add(r['pairing_sha256']); clean[i,l]=r['L0_u']
        clean[i,-1]=r['L0']
        if len(pairing)!=1: raise ValueError('attack seed pairing lost')
    for i,seed in enumerate(config.normal_seeds):
        for l,m in enumerate(config.methods): normal[i,l]=index['normal',seed,None,None,m]['L0_u']
        normal[i,-1]=index['normal',seed,None,None,config.methods[0]]['L0']
    if not all(np.isfinite(a).all() for a in (losses,clean,normal,net,pollution,cross)):
        raise ValueError('nonfinite E3 losses')
    if formal and (n!=200 or nn!=200): raise ValueError('formal E3 requires 200+200 seeds')
    if indices is None:
        if not formal: raise PermissionError('preparation statistics require explicit synthetic resampling indices')
        indices=resample_indices(config.bootstrap_seed,n,config.bootstrap_resamples)
    indices=np.asarray(indices)
    if indices.ndim!=2 or indices.shape[1]!=n or np.any(indices<0) or np.any(indices>=n):
        raise ValueError('invalid whole-seed resampling')
    if formal and indices.shape[0]!=1999: raise ValueError('1999 frozen bootstrap resamples required')
    mi=config.events.index(config.shared.main_event); age64=config.ages.index(64); si=methods.index(SET)
    primary=losses[:,mi,age64,:]; yang=float(primary[:,-1].mean()); setloss=float(primary[:,si].mean())
    if yang<=0 or np.any(primary[indices][:,:,-1].mean(axis=1)<=0): raise ValueError('undefined Yang relative gain')
    primary_boot=primary[indices].mean(axis=1)
    gains=(primary_boot[:,-1]-primary_boot[:,si])/primary_boot[:,-1]
    gain=(yang-setloss)/yang
    margins={}; net_diagnostic={}
    nominal=losses[:,:,age64,:]
    for b in config.shared.protocol['e3_main_comparators']:
        bi=methods.index(b); point,boot=worst_event_margin(nominal[:,:,bi],nominal[:,:,si],indices)
        low=float(np.quantile(boot,.025,method='linear'))
        margins[b]={'point':point,'lower_97_5':low,'pass':point>=0 and low>=0,
                    'R_b':float(nominal[:,:,bi].mean(axis=0).max()),'R_set':float(nominal[:,:,si].mean(axis=0).max())}
        # Exploratory healthy-adjusted worst-event advantage (no .99 scaling).
        npoint=float(nominal[:,:,bi].mean(axis=0).max()-nominal[:,:,si].mean(axis=0).max()-(clean[:,bi]-clean[:,si]).mean())
        nboot=np.array([nominal[ix,:,bi].mean(axis=0).max()-nominal[ix,:,si].mean(axis=0).max()-(clean[ix,bi]-clean[ix,si]).mean() for ix in indices])
        main_net=net[:,mi,age64,si]-net[:,mi,age64,bi]
        net_diagnostic[b]={'point':npoint,'interval_95':interval(nboot),
                          'main_event_net_advantage':float(main_net.mean()),
                          'main_event_net_advantage_interval_95':interval(main_net[indices].mean(axis=1)),
                          'event_net_advantages_age64':{
                              f'{e[0]}:{e[1]}':{'point':float((net[:,j,age64,si]-net[:,j,age64,bi]).mean()),
                              'interval_95':interval((net[:,j,age64,si]-net[:,j,age64,bi])[indices].mean(axis=1))}
                              for j,e in enumerate(config.events)},
                          'scope':'exploratory paired healthy-adjusted diagnostics; not confirmatory family'}
    per_case={}
    for j,e in enumerate(config.events):
        for k,a in enumerate(config.ages):
            cell={}
            for l,m in enumerate(methods):
                rs=[index['attack',s,e,a,m] for s in config.attack_seeds] if m!=YANG else []
                ns=net[:,j,k,l]
                cell[m]={'mse':float(losses[:,j,k,l].mean()),'attack_gain':float((losses[:,j,k,-1]-losses[:,j,k,l]).mean()),
                         'healthy_gain_paired':float((clean[:,-1]-clean[:,l]).mean()),
                         'net_gain':float(ns.mean()),'net_gain_interval_95':interval(ns[indices].mean(axis=1)),
                         'pollution_gain':float(pollution[:,j,k,l].mean()),'healthy_cross_term':float(cross[:,j,k,l].mean()),
                         'nonzero_rate':sum(r['nonzero'] for r in rs)/n,'saturation_rate':sum(r['saturated'] for r in rs)/n,
                         'zero_action_rate':sum(not r['nonzero'] for r in rs)/n if rs else 1.,
                         'rejection_rate':sum(r['proposal_status']!='VALID' or r['gate_status']!='EXECUTED' for r in rs)/n}
            per_case[f'{e[0]}:{e[1]}@{a}']=cell
    normals={m:{'mse':float(normal[:,l].mean()),'mse_change_vs_yang':float((normal[:,l]-normal[:,-1]).mean()),
        'relative_change_vs_yang':float((normal[:,l].mean()-normal[:,-1].mean())/normal[:,-1].mean()),
        'nonzero_rate':sum(index['normal',s,None,None,m]['nonzero'] for s in config.normal_seeds)/nn if m!=YANG else 0.,
        'zero_action_rate':sum(not index['normal',s,None,None,m]['nonzero'] for s in config.normal_seeds)/nn if m!=YANG else 1.,
        'rejection_rate':sum(index['normal',s,None,None,m].get('proposal_status','VALID')!='VALID' or index['normal',s,None,None,m].get('gate_status','EXECUTED')!='EXECUTED' for s in config.normal_seeds)/nn if m!=YANG else 0.,
        'saturation_rate':sum(index['normal',s,None,None,m].get('saturated',False) for s in config.normal_seeds)/nn if m!=YANG else 0.} for l,m in enumerate(methods)}
    return {'scope':'FORMAL_E3' if formal else 'SYNTHETIC_DETERMINISTIC_ONLY',
            'decision':gate_decision(gain,margins,net_diagnostic),'n_attack_seeds':n,'n_normal_seeds':nn,
            'bootstrap_resamples':len(indices),'resampling_unit':'whole seed; same indices across all events, ages and methods',
            'bootstrap_indices_sha256':__import__('hashlib').sha256(indices.astype('<i8').tobytes()).hexdigest(),
            'yang_primary':{'relative_improvement':gain,'interval_95_descriptive':interval(gains),'pass':gain>=.01},
            'confirmatory_worst_event_age64':margins,'exploratory_net_advantages':net_diagnostic,
            'normal':normals,'per_event_age':per_case,
            'matched_prior_age64':{m:float(.5*normal[:,l].mean()+.5*nominal[:,:,l].mean()) for l,m in enumerate(methods)},
            'interpretation':'Bootstrap intervals are approximate, not finite-sample exact guarantees.'}


def recompute(config, directory, *, formal=False, indices=None, receipt=None):
    from .storage import verify_manifest
    from .execution_state import require_resumable_or_complete
    require_resumable_or_complete(directory, config, allow_complete=True)
    verify_manifest(directory)
    rows=[]
    for path in sorted((directory/'seeds').glob('*.json')): rows.extend(json.loads(path.read_text())['rows'])
    from .integrity_checker import validate_rows
    validate_rows(config,rows)
    return summarize(config,rows,formal=formal,indices=indices,receipt=receipt)
