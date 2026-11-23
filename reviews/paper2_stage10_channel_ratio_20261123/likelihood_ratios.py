"""Candidate/healthy interval ratios on exactly the frozen R3 histories."""
from decimal import Decimal, localcontext
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
R3 = HERE.parent / "paper2_stage10_n03r_20261123"
sys.path.insert(0, str(R3))
from mixture_history import I, Reading, history_bounds
from verify_short_histories import MODEL, joint_integral


def ratio(candidate, healthy):
    if healthy.lo <= 0 or not all(v.is_finite() for v in
                                   (healthy.lo, healthy.hi, candidate.lo, candidate.hi)):
        return None
    return candidate / healthy


def display(bounds):
    with localcontext() as ctx:
        ctx.prec = 66
        lo, hi = bounds
        return [str((Decimal(lo.numerator)/Decimal(lo.denominator)).next_minus()),
                str((Decimal(hi.numerator)/Decimal(hi.denominator)).next_plus())]


def main():
    source = R3 / 'verification.json'
    frozen = json.loads(source.read_text(encoding='utf8'))
    model = json.loads(MODEL.read_text(encoding='utf8'))
    k, b = frozen['candidate']['onset'], F(frozen['candidate']['bias'])
    records = []
    assert ratio(I.exact(1), I(Decimal(0),Decimal(1))) is None
    for case, data in frozen['cases'].items():
        rows = [Reading(float.fromhex(c), None if z is None else float.fromhex(z))
                for c,z in data['observations']]
        candidate = history_bounds(model,rows,k,b)
        healthy = history_bounds(model,rows,k,F(0))
        for t,(num,den,archived) in enumerate(zip(candidate,healthy,data['prefixes'])):
            assert (num.lo,num.hi) == (Decimal(archived['lo']),Decimal(archived['hi']))
            result = ratio(num,den)
            if result is None:
                raise ArithmeticError((case,t,'unresolved healthy denominator'))
            cuts = archived['batch_pieces_per_send']
            pc, bc = joint_integral(model,rows[:t+1],k,b,cuts)
            ph, bh = joint_integral(model,rows[:t+1],k,F(0),cuts)
            assert bh[0] > 0
            independent = bc[0]/bh[1], bc[1]/bh[0]
            with localcontext() as ctx:
                ctx.prec = 110
                point = pc/ph
                width = (result.hi-result.lo)/point
            assert result.lo <= point <= result.hi and independent[0] <= F(point) <= independent[1]
            nested = F(result.lo) <= independent[0] <= independent[1] <= F(result.hi)
            if cuts > 1:
                assert nested, (case,t)
            if not any(r.word is not None for r in rows[k:t+1]):
                assert point == 1 and result.lo <= 1 <= result.hi
            records.append({'case':case,'t':t,'candidate':num.json(),'healthy':den.json(),
                            'ratio':result.json(),'batch_ratio':str(point),
                            'rational_ratio':display(independent),'rational_inside_recursive':nested,
                            'relative_width':str(width)})
    assert len(records) == 36
    max_width = max(records,key=lambda r: Decimal(r['relative_width']))
    min_healthy = min(records,key=lambda r: Decimal(r['healthy']['lo']))
    summary = {'prefixes':len(records),'nested_ratios':sum(r['rational_inside_recursive'] for r in records),
               'nested_archived_masses':sum(p['batch_inside_recursive'] for c in frozen['cases'].values()
                                             for p in c['prefixes']),
               'maximum_relative_width':{k:max_width[k] for k in ('case','t','relative_width')},
               'smallest_healthy':{k:min_healthy[k] for k in ('case','t','healthy','ratio','relative_width')}}
    report = {'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'candidate':frozen['candidate'],'summary':summary,'records':records}
    (HERE/'ratios.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps(summary,indent=2))


if __name__ == '__main__':
    main()
