"""Recompute offline losses from saved target vectors using scalar arithmetic."""
import math


def validate_rows(config,rows):
    seen=set()
    for r in rows:
        key=(r['role'],r['seed'],tuple(r['event']) if r['event'] is not None else None,r['age'],r['method'])
        if key in seen: raise ValueError('duplicate E3 row')
        seen.add(key)
        if r['method'] not in config.methods: raise ValueError('unplanned E3 method')
        for name in ('true_state','healthy_estimate','attacked_estimate','delta','e0','u','u0'):
            if len(r[name])!=2 or not all(math.isfinite(v) for v in r[name]): raise ValueError('invalid E3 vector: '+name)
        x,h,a,u,u0=(r[k] for k in ('true_state','healthy_estimate','attacked_estimate','u','u0'))
        e=[h[j]-x[j] for j in range(2)]; d=[a[j]-h[j] for j in range(2)]
        close=lambda v,w: math.isclose(float(v),float(w),rel_tol=1e-10,abs_tol=1e-12)
        if not all(close(e[j],r['e0'][j]) and close(d[j],r['delta'][j]) for j in range(2)):
            raise ValueError('stored error or contamination sign/time mismatch')
        sq=lambda v:math.fsum(t*t for t in v)
        L0=sq(e); La=sq([a[j]-x[j] for j in range(2)])
        L0u=sq([h[j]-u0[j]-x[j] for j in range(2)]); Lau=sq([a[j]-u[j]-x[j] for j in range(2)])
        expected={'L0':L0,'La':La,'L0_u':L0u,'La_u':Lau,'attack_gain':La-Lau,'healthy_gain':L0-L0u,
            'normal_risk_change':L0u-L0,'pollution_gain':2*math.fsum(d[j]*u[j] for j in range(2))-sq(u),
            'healthy_cross_term':2*math.fsum(e[j]*u[j] for j in range(2)),
            'net_gain':La-Lau-L0+L0u}
        for name,value in expected.items():
            if not close(value,r[name]): raise ValueError('E3 saved loss inconsistent: '+name)
        norm=math.sqrt(sq(u))
        if not close(norm,r['action_norm']) or norm>config.shared.protocol['U_common']+1e-12:
            raise ValueError('E3 action norm/cap mismatch')
        if r['nonzero']!=(norm>1e-12): raise ValueError('nonzero must use actual post-gate action')
        if r['threshold']!=config.shared.thresholds[r['method']]: raise ValueError('E3 calibration threshold changed')
        if (r['proposal_status']!='VALID' or r['gate_status']!='EXECUTED') and norm>1e-12:
            raise ValueError('algorithm rejection has nonzero action')
        if r['role']=='attack':
            event=tuple(r['event']); age=r['age']
            if (event not in config.events or age not in config.ages
                    or r['replay_source_time']!=event[1]-age or r['actual_replay_age']!=age
                    or r['cache_replacement_time']!=event[1]+8):
                raise ValueError('E3 Replay source/age/cache mismatch')
    return len(rows)
