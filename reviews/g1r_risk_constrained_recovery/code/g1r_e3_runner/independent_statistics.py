"""Independent core E3 risk audit, reconstructed from target vectors, not saved loss columns."""
from __future__ import annotations
import math
import numpy as np


def core_from_vectors(config, rows, indices):
    methods=config.methods; events=config.events; seeds=config.attack_seeds
    si=methods.index('set_constrained_chebyshev')
    table={(r['seed'],tuple(r['event']),r['method']):r for r in rows if r['role']=='attack' and r['age']==64}
    n=len(seeds); risk=np.empty((n,len(events),len(methods)+1))
    for i,seed in enumerate(seeds):
        for j,event in enumerate(events):
            for k,method in enumerate(methods):
                r=table[seed,event,method]
                error=[r['attacked_estimate'][d]-r['true_state'][d]-r['u'][d] for d in range(2)]
                risk[i,j,k]=math.fsum(v*v for v in error)
            raw=[r['attacked_estimate'][d]-r['true_state'][d] for d in range(2)]
            risk[i,j,-1]=math.fsum(v*v for v in raw)
    main=events.index(config.shared.main_event)
    relative=1-risk[:,main,si].mean()/risk[:,main,-1].mean()
    margins={}
    for baseline in config.shared.protocol['e3_main_comparators']:
        bi=methods.index(baseline)
        point=.99*max(math.fsum(risk[:,j,bi])/n for j in range(len(events)))-max(math.fsum(risk[:,j,si])/n for j in range(len(events)))
        # Frequency weights preserve all cases within each sampled seed, without the main tensor-indexing implementation.
        samples=[]
        for ix in indices:
            weights=np.bincount(ix,minlength=n)/n
            b=max(float(weights@risk[:,j,bi]) for j in range(len(events)))
            s=max(float(weights@risk[:,j,si]) for j in range(len(events)))
            samples.append(.99*b-s)
        margins[baseline]={'point':float(point),'lower_97_5':float(np.percentile(samples,2.5,method='linear'))}
    return {'relative_yang_improvement':float(relative),'margins':margins,
            'algorithm':'scalar target-error reconstruction and bootstrap multinomial frequency weights'}


def compare(config, rows, indices, result):
    independent=core_from_vectors(config,rows,indices)
    diffs=[abs(independent['relative_yang_improvement']-result['yang_primary']['relative_improvement'])]
    for method,values in independent['margins'].items():
        for key in ('point','lower_97_5'):
            diffs.append(abs(values[key]-result['confirmatory_worst_event_age64'][method][key]))
    if max(diffs)>1e-10: raise ValueError('independent E3 vector/statistics audit differs')
    return {**independent,'max_absolute_difference':max(diffs),'status':'PASS_INDEPENDENT_VECTOR_RISK_AND_FREQUENCY_WEIGHT_BOOTSTRAP'}
