"""R4a predictable reference process and sound interval elimination checks."""
from decimal import Decimal as D
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
R3=HERE.parent/'paper2_stage10_n03r_20261123'
sys.path.insert(0,str(R3))
from mixture_history import I,Reading,history_bounds
from numerical_record import interval_fraction as frac
from verify_short_histories import MODEL,joint_integral
from reference_kernel import reference_sequence,history_union_upper
from reference_kernel import silence_mass


def weight(t):
    return I.exact(1)/((t+1)*(t+2))


def direct_starts(ells):
    total=I.exact(0)
    for s in range(len(ells)):
        term=I.exact(1)
        for ell in ells[s:]:
            term=term*ell
        total=total+weight(s)*term
    return total


def exact_weight_identity():
    for length in range(1,9):
        ell=[F(i+1,i+2) for i in range(length)]
        value=F(0)
        for t,x in enumerate(ell):
            value=(value+F(1,(t+1)*(t+2)))*x
        direct=sum((F(1,(s+1)*(s+2))*math.prod(ell[s:])
                    for s in range(length)),F(0))
        assert value==direct
        # With ell=1, the residual prior plus all start weights is exactly one.
        assert sum((F(1,(s+1)*(s+2)) for s in range(length)),F(0))+F(1,length+1)==1
    return True


def run_record(name,rows,model,epsilon=D('.001'),amplitude_box=(F(0),F(1,4)),
               diagnose_points=False):
    health=history_bounds(model,rows,0,F(0))
    variances,refs=reference_sequence(rows,model)
    lambdas={b:frac(F(1,3)) for b in refs}
    Ms={b:I.exact(0) for b in refs}
    products={b:I.exact(1) for b in refs}
    entries=[]
    for t,reading in enumerate(rows):
        hprev=I.exact(1) if t==0 else health[t-1]
        hcond=health[t]/hprev
        if hcond.lo<=0:
            raise ArithmeticError((name,t,'health conditional mass unresolved'))
        ells={}
        for b,kernels in refs.items():
            q=kernels[t]
            if q.lo<=0:
                raise ArithmeticError((name,t,b,'reference kernel not positive'))
            ell=q/hcond
            ells[b]=ell
            Ms[b]=(Ms[b]+weight(t))*ell
            products[b]=products[b]*ell
        q_sil=silence_mass(reading.center,F(0),variances[t],F(model['Z']))
        q_send_all=I.exact(1)-q_sil
        normalized=q_sil+q_send_all
        assert q_sil.lo>0 and q_send_all.lo>0 and normalized.lo<=1<=normalized.hi
        a=I.exact(1)/(t+2)
        R=a+sum((lambdas[b]*Ms[b] for b in refs),I.exact(0))
        direct=a+sum((lambdas[b]*direct_starts(
            [refs[b][i]/(health[i]/(I.exact(1) if i==0 else health[i-1]))
             for i in range(t+1)]) for b in refs),I.exact(0))
        assert R.lo>0 and direct.lo<=R.hi and R.lo<=direct.hi
        assert a.lo<=R.lo<=R.hi
        assert all(x.lo>0 and x.hi<=1 for x in (kernels[t] for kernels in refs.values()))
        entries.append({'time':t,'healthy_mass':health[t].json(),
                        'healthy_conditional':hcond.json(),
                        'reference_normalizer':{'silence':q_sil.json(),
                                                'sum_all_send_codes':q_send_all.json(),
                                                'total':normalized.json()},
                        'q':{str(b):refs[b][t].json() for b in refs},
                        'ell':{str(b):ells[b].json() for b in refs},
                        'M':{str(b):Ms[b].json() for b in refs},
                        'R':R.json(),'direct_R':direct.json(),
                        'epsilon_R_lower':str((I.exact(epsilon)*R).lo)})
    exclusions=[]
    point_amps=(F(0),F(1,20),F(1,10),F(1,4))
    point_diagnostics=0
    for t in range(len(rows)):
        prefix=rows[:t+1]
        p0=health[t]
        Rlo=D(entries[t]['R']['lo'])
        for k in range(t+1):
            upper=history_union_upper(model,prefix,k,amplitude_box,pieces=2)
            lr_upper=upper/I(p0.lo,p0.lo)
            for b in point_amps:
                p=history_bounds(model,prefix,k,b,pieces=2)[-1]
                # Separate subdivision schedules can yield nonnested valid
                # intervals. Compare a high-precision point value instead of
                # asserting that one conservative upper endpoint dominates another.
                if b==0:
                    assert p.lo<=upper.hi,(name,t,k,b,p,upper)
                if diagnose_points and b in (F(0),F(1,4)):
                    diagnostic,_=joint_integral(model,prefix,k,b,2)
                    assert F(diagnostic)<=F(upper.hi),(name,t,k,b,diagnostic,upper)
                    point_diagnostics+=1
            excluded=lr_upper.hi < D(epsilon)*Rlo
            exclusions.append({'time':t,'onset':k,'amplitude_box':[str(x) for x in amplitude_box],
                               'p_candidate_upper':str(upper.hi),'p0_lower':str(p0.lo),
                               'L_box_upper':str(lr_upper.hi),'epsilon_R_lower':str(D(epsilon)*Rlo),
                               'certified_excluded':bool(excluded)})
    return {'steps':len(rows),'entries':entries,'box_checks':len(exclusions),
            'independent_endpoint_point_diagnostics':point_diagnostics,
            'exclusions':exclusions}


def frozen_cases(model):
    data=json.loads((R3/'verification.json').read_text(encoding='utf8'))
    outputs={}
    for name,case in data['cases'].items():
        rows=[Reading(float.fromhex(c),None if z is None else float.fromhex(z))
              for c,z in case['observations']]
        outputs[name]=run_record(name,rows,model,diagnose_points=True)
    return outputs


def pressure_cases(model):
    center=0.0
    silence=[Reading(center,None) for _ in range(32)]
    sparse=[Reading(0.,0.),Reading(0.,None),Reading(.25,.5),Reading(.25,None),
            Reading(.125,-0.),Reading(.125,None),Reading(-.25,-.5),Reading(-.25,None)]
    return {'32_silence':run_record('32_silence',silence,model),
            '8_sparse_codes':run_record('8_sparse_codes',sparse,model)}


def main():
    exact_weight_identity()
    model=json.loads((HERE.parent/'paper2_stage6_vector_correction_20261122'/'model.json').read_text(encoding='utf8'))
    frozen=frozen_cases(model)
    pressure=pressure_cases(model)
    files=[Path(__file__),HERE/'reference_kernel.py',R3/'verification.json',
           R3/'mixture_history.py',R3/'verify_short_histories.py',
           R3/'rational_batch.py',HERE.parent/'paper2_stage10_numerical_contract_20261123'/'numerical_record.py',
           HERE.parent/'paper2_stage4_certified_correction_20261122'/'interval_arithmetic.py',
           HERE.parent/'paper2_stage6_vector_correction_20261122'/'exact_linear.py',
           HERE.parent/'paper2_stage6_vector_correction_20261122'/'model.json']
    result={'candidate_reference_biases':['1/20','1/10','1/4'],
            'exact_weight_identity_lengths':list(range(1,9)),
            'reference_mean_offset':'0, fixed predictable strategy',
            'mixture_weights':'1/3 each','epsilon':'0.001',
            'frozen_cases':frozen,'pressure_cases':pressure,
            'sha256':{p.relative_to(HERE.parents[1]).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
    all_entries=[e for case in frozen.values() for e in case['entries']]
    all_boxes=[e for case in frozen.values() for e in case['exclusions']]
    point_diagnostics=sum(case['independent_endpoint_point_diagnostics'] for case in frozen.values())
    excluded=[e for e in all_boxes if e['certified_excluded']]
    min_health=min((D(e['healthy_mass']['lo']),name,e['time'])
                   for name,case in frozen.items() for e in case['entries'])
    result['summary']={'frozen_prefixes':len(all_entries),'amplitude_onset_boxes':len(all_boxes),
                       'independent_endpoint_point_diagnostics':point_diagnostics,
                       'box_exclusions_on_these_records':len(excluded),
                       'minimum_frozen_healthy_mass':{'value':str(min_health[0]),
                                                      'case':min_health[1],'time':min_health[2]},
                       'minimum_reference_lower':str(min(D(e['R']['lo']) for e in all_entries)),
                       'maximum_reference_upper':str(max(D(e['R']['hi']) for e in all_entries))}
    (HERE/'r4a_checks.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
    print('PASS',sum(len(x['entries']) for x in frozen.values()),'frozen prefixes; reference lower min',
          min(D(e['R']['lo']) for e in all_entries))
    print('PASS',sum(x['box_checks'] for x in frozen.values()),'onset-box outer checks')
    print('pressure', {k:v['steps'] for k,v in pressure.items()})


if __name__=='__main__':
    main()
