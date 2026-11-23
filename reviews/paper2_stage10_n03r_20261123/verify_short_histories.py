"""Independent short-history integration using the joint open-loop observation law."""
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
from itertools import product
import hashlib
import json
import math
from pathlib import Path
import sys

from mixture_history import Reading, history_bounds, CONTRACT
from rational_batch import batch_bounds
from exact_linear import add, matrix, matmul, transpose, update

HERE = Path(__file__).resolve().parent
MODEL = HERE.parent / 'paper2_stage6_vector_correction_20261122' / 'model.json'


def dec(x):
    return D(x.numerator)/D(x.denominator)


def joint_covariance(model, rows):
    # Compute the unconditional loading of each independent noise on Y_t.
    # Each V2 covariance here is diagonal; loadings avoid the filter Riccati path.
    A = [[F(a) for a in row] for row in model['A']]
    C = [F(c) for c in model['C'][0]]
    P, Q = model['P0_prior'], model['Q']
    assert F(P[0][1]) == F(P[1][0]) == F(Q[0][1]) == F(Q[1][0]) == 0
    n = len(rows)
    noise = [F(P[j][j]) for j in range(2)] + [F(Q[j][j]) for _ in range(n-1) for j in range(2)]
    state = [[F(i == j) for j in range(2*n)] for i in range(2)]
    loads = []
    for t in range(n):
        loads.append([sum(C[i]*state[i][j] for i in range(2)) for j in range(2*n)])
        if t+1 < n:
            state = [[sum(A[i][k]*state[k][j] for k in range(2)) for j in range(2*n)] for i in range(2)]
            for i in range(2):
                state[i][2*(t+1)+i] = F(1)
    R, Z = F(model['R']), F(model['Z'])
    return [[sum(a*b*q for a,b,q in zip(loads[i],loads[j],noise)) +
             ((R + (1/Z if rows[i].word is None else 0)) if i == j else 0)
             for j in range(n)] for i in range(n)]


def joint_integral(model, rows, onset, bias, partitions=1):
    # No interval filter, posterior mean, gain or Riccati implementation here.
    # Factor the batch covariance into L D L^T over exact rationals.
    sigma = joint_covariance(model, rows)
    n = len(rows)
    lower = [[F(i == j) for j in range(n)] for i in range(n)]
    diag = []
    for j in range(n):
        pivot = sigma[j][j] - sum(lower[j][k]**2*diag[k] for k in range(j))
        assert pivot > 0
        diag.append(pivot)
        for i in range(j+1,n):
            lower[i][j] = (sigma[i][j] - sum(lower[i][k]*diag[k]*lower[j][k] for k in range(j))) / pivot
    with localcontext() as ctx:
        ctx.prec = 125
        # A separate rounded constant for the high precision diagnostic only.
        pi = D('3.1415926535897932384626433832795028841971693993751058209749445923078164062862089986280348253421170679821480865132823')
        Z = D(model['Z'])
        constant = ((2*pi/Z)**sum(r.word is None for r in rows) /
                    ((2*pi)**n * dec(math.prod(diag)))).sqrt()
        nodes = [(D(3)/5).sqrt()*s for s in (-1,0,1)]
        weights = [D(5)/18, D(4)/9, D(5)/18]
        axes = []
        cells = []
        for t,row in enumerate(rows):
            c = F.from_float(row.center)
            if row.word is None:
                axes.append([(dec(c),D(1))])
                cells.append((c,c))
                continue
            # Independently decode midpoints, including signed zero for the fixtures.
            z = F.from_float(row.word)
            left = (F.from_float(math.nextafter(row.word,-math.inf))+z)/2
            right = (F.from_float(math.nextafter(row.word,math.inf))+z)/2
            if row.word == 0:
                if math.copysign(1,row.word) > 0: left = F(0)
                else: right = F(0)
            shift = bias if t >= onset else F(0)
            cells.append((left-shift, right-shift))
            mid, width = (left+right)/2-shift, right-left
            axis = []
            for node,w in zip(nodes,weights):
                # Subtract the center in rational coordinates before conversion.
                u = dec(mid) + dec(width/2)*node
                d = dec(mid-c) + dec(width/2)*node
                e = Z*d*d/2
                if e < D('1e-45'):
                    h = e*(1-e/2+e*e/6)
                else:
                    h = 1-(-e).exp()
                axis.append((u,dec(width)*w*h))
            axes.append(axis)
        dld = [[dec(x) for x in row] for row in lower]
        total = D(0)
        for sample in product(*axes):
            projected = []
            for i,(v,_) in enumerate(sample):
                projected.append(v-sum(dld[i][j]*projected[j] for j in range(i)))
            exponent = sum(x*x/dec(p) for x,p in zip(projected,diag))
            total += math.prod(w for _,w in sample)*(-exponent/2).exp()
        ranges = []
        for a,b in cells:
            if a == b:
                ranges.append([(a,b)])
            else:
                step = (b-a)/partitions
                ranges.append([(a+i*step,a+(i+1)*step) for i in range(partitions)])
        lower_mass = upper_mass = F(0)
        for subbox in product(*ranges):
            lo,hi = batch_bounds(rows,subbox,lower,diag,F(model['Z']))
            lower_mass += lo
            upper_mass += hi
        return constant*total, (lower_mass, upper_mass)


def feedback_fixture(model):
    """Generate a conditional Model A center path using public history only."""
    A, C, Q, P = (matrix(model[key]) for key in ('A','C','Q','P0_prior'))
    delta, R, Z = (F(model[key]) for key in ('quantization_half_width','R','Z'))
    mean = [[F(0)],[F(0)]]
    readings, log = [], []
    # External phase realizations for a deterministic conditional-law check.
    phases = [F(0),delta/4,-delta/2,delta/8,-delta/8]
    words = [.375,None,-.25,None,.5]
    for phase, word in zip(phases, words):
        prediction = matmul(C, mean)[0][0]
        index = (prediction-phase+delta)//(2*delta)
        grid_center = phase + 2*delta*index
        shared_center = float(grid_center)
        center = F.from_float(shared_center)
        assert abs(center-prediction) <= delta
        readings.append(Reading(shared_center,word))
        log.append({'prediction':str(prediction),'phase':str(phase),'index':index,
                    'grid_center':str(grid_center),'shared_center_hex':shared_center.hex()})
        observation = center if word is None else F.from_float(word)
        post_P, gain, transition = update(P,C,R + (1/Z if word is None else 0))
        mean = matmul(A,add(matmul(transition,mean),matmul(gain,[[observation]])))
        P = add(matmul(matmul(A,post_P),transpose(A)),Q)
    return readings,log


def main():
    model = json.loads(MODEL.read_text(encoding='utf8'))
    onset, bias = 1, F(1,4)
    tie = bias + F(1,2**54)
    continuous = tie + F(1,2**57)
    once = float(continuous+bias)
    twice = float(continuous)+float(bias)
    assert once == math.nextafter(.5,math.inf) and twice == .5
    # Conditional kernel fixtures; the centers are fixed external inputs.
    ordinary = [Reading(c,z) for c,z in [(0.,.375),(.25,-.25),(.125,.5),(.25,.75),(.125,-.5)]]
    silent = lambda i: Reading(ordinary[i].center,None)
    fixtures = {
        'two_send_silent': [ordinary[0],silent(1)],
        'two_silent_send_zero': [silent(0), Reading(.25,.5)],
        'two_sends': ordinary[:2],
        'three_silent_send_silent': [silent(0),ordinary[1],silent(2)],
        'three_all_silent': [silent(i) for i in range(3)],
        'three_all_send': ordinary[:3],
        'four_signed_zero': [Reading(0.,-0.),silent(1),ordinary[2],silent(3)],
        'five_mixed': [ordinary[0],silent(1),ordinary[2],silent(3),ordinary[4]],
        'five_all_send': ordinary,
        'two_positive_zero': [Reading(0.,0.),silent(1)],
    }
    fixtures['five_feedback'], feedback_log = feedback_fixture(model)
    results = {}
    for name,rows in fixtures.items():
        masses = history_bounds(model,rows,onset,bias)
        detail = []
        for n,m in enumerate(masses,1):
            # A tighter independent enclosure on the two designated full histories.
            refine = n == len(rows) and name in ('two_sends','three_silent_send_silent')
            subdivisions = 16 if refine else 1
            reference, (batch_lo,batch_hi) = joint_integral(model,rows[:n],onset,bias,subdivisions)
            if not (0 < m.lo <= reference <= m.hi <= 1 and
                    0 < batch_lo <= F(reference) <= batch_hi <= 1):
                raise AssertionError((name,n,m,reference,batch_lo,batch_hi))
            nested = F(m.lo) <= batch_lo <= batch_hi <= F(m.hi)
            if refine and not nested:
                raise AssertionError(('independent enclosure not nested',name))
            # Compact, outward decimal display of the independent rational bounds.
            with localcontext() as ctx:
                ctx.prec = 56
                batch_display = [str(dec(batch_lo).next_minus()),str(dec(batch_hi).next_plus())]
            detail.append({'lo':str(m.lo),'hi':str(m.hi),'batch':str(reference),
                           'rational_batch_bounds':batch_display,
                           'batch_pieces_per_send':subdivisions,'batch_inside_recursive':nested,
                           'relative_width':str((m.hi-m.lo)/reference)})
        results[name] = {'observations':[[r.center.hex(),r.word.hex() if r.word is not None else None] for r in rows],
                         'prefixes':detail}
    files = [Path(__file__),HERE/'mixture_history.py',HERE/'rational_batch.py',MODEL,CONTRACT/'numerical_record.py',
             HERE.parent/'paper2_stage4_certified_correction_20261122'/'interval_arithmetic.py',
             HERE.parent/'paper2_stage6_vector_correction_20261122'/'exact_linear.py',
             HERE.parent/'paper2_stage6_vector_correction_20261122'/'vector_record.py']
    report = {'model':'V2 / A; conditional on common centers','candidate':{'onset':onset,'bias':str(bias)},
              'five_feedback_audit_only': feedback_log,
              'channel_witness': {'real_y':str(continuous),'b':str(bias),
                                  'one_round_hex':once.hex(),'two_round_hex':twice.hex()},
              'pieces_per_send':2,'deterministic':True,'python':sys.version.split()[0],
              'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files},'cases':results}
    (HERE/'verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8',newline='\n')
    print('PASS', len(results), 'histories,',sum(len(v['prefixes']) for v in results.values()), 'prefix comparisons')
    print('maximum relative width',max(D(p['relative_width']) for v in results.values() for p in v['prefixes']))
    print('five_mixed final',results['five_mixed']['prefixes'][-1])


if __name__ == '__main__':
    main()
