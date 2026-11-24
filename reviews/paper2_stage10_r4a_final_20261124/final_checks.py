"""R4a-Final signed-zero, overflow, and independent normalization checks."""
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import sys

from scipy.integrate import quad

HERE=Path(__file__).resolve().parent
R4A=HERE.parent/'paper2_stage10_r4a_20261124'
R3=HERE.parent/'paper2_stage10_n03r_20261123'
STAGE6=HERE.parent/'paper2_stage6_vector_correction_20261122'
sys.path[:0]=[str(R4A),str(R3),str(STAGE6)]

from alphabet_audit import (AlphabetReading,OVERFLOW_THRESHOLD,code_cell,
                            finite_alphabet_send_integral,finite_word_mass,overflow_mass)
from mixture_history import Reading
from numerical_record import interval_fraction as frac
from reference_kernel import silence_mass,reference_sequence,reference_step


def cell_contiguity_checks():
    tiny=math.ulp(0.0)
    max_float=float.fromhex('0x1.fffffffffffffp+1023')
    groups=[
        [-max_float,-math.nextafter(max_float,-math.inf)],
        [-2*tiny,-tiny,-0.0,+0.0,tiny,2*tiny],
        [math.nextafter(.5,-math.inf),.5,math.nextafter(.5,math.inf)],
        [math.nextafter(1.0,-math.inf),1.0,math.nextafter(1.0,math.inf)],
        [math.nextafter(max_float,-math.inf),max_float],
    ]
    pairs=0
    for values in groups:
        cells=[code_cell(x) for x in values]
        for i in range(len(cells)-1):
            assert cells[i][1]==cells[i+1][0],(values[i].hex(),values[i+1].hex())
            pairs+=1
    assert code_cell(-max_float)[0]==-OVERFLOW_THRESHOLD
    assert code_cell(max_float)[1]==OVERFLOW_THRESHOLD
    assert code_cell(-0.0)==(-F(1,2**1075),F(0))
    assert code_cell(+0.0)==(F(0),F(1,2**1075))
    assert code_cell(-math.inf)==(None,-OVERFLOW_THRESHOLD)
    assert code_cell(+math.inf)==(OVERFLOW_THRESHOLD,None)
    return {"sampled_local_groups":[len(x) for x in groups],"adjacent_boundaries":pairs,
            "negative_zero": [str(x) for x in code_cell(-0.)],
            "positive_zero": [str(x) for x in code_cell(+0.)],
            "overflow_threshold":str(OVERFLOW_THRESHOLD)}


def scipy_send_mass(mean,variance,center,Z):
    mu,S,c,z=map(float,(mean,variance,center,Z))
    sigma=math.sqrt(S)
    norm=1/math.sqrt(2*math.pi*S)
    f=lambda y:norm*math.exp(-(y-mu)**2/(2*S))*(-math.expm1(-z*(y-c)**2/2))
    point,error=quad(f,mu-12*sigma,mu+12*sigma,epsabs=1e-14,epsrel=1e-13,limit=300)
    tail=2*0.5*math.erfc(12/math.sqrt(2))
    return point, error, tail


def normalizer_cases():
    Z=F(2)
    scenarios=[
        {"name":"initial","mean":F(0),"S":F(1,5),"center":F(0)},
        {"name":"offset_center","mean":F(1,10),"S":F(3,10),"center":F(-1,20)},
        {"name":"later_covariance","mean":F(-1,8),"S":F(2,5),"center":F(3,20)},
    ]
    output=[]
    for scenario in scenarios:
        for b in (F(0),F(1,20),F(1,4)):
            finite,quadrature=finite_alphabet_send_integral(
                scenario["mean"],scenario["S"],scenario["center"],Z,bias=b,panels=4096)
            positive=overflow_mass(math.inf,b,scenario["mean"],scenario["S"],scenario["center"],Z)
            negative=overflow_mass(-math.inf,b,scenario["mean"],scenario["S"],scenario["center"],Z)
            qsil=silence_mass(float(scenario["center"]),F(scenario["mean"]),F(scenario["S"]),Z)
            # The two overflow cells are bounded from above by the corresponding
            # untriggered Gaussian tails. Their lower mass is unresolved at Decimal scale.
            total=qsil+finite+positive+negative
            assert total.lo<=1<=total.hi,(scenario,b,total)
            expected=1-qsil
            assert finite.lo<=expected.hi
            assert expected.lo<=finite.hi+positive.hi+negative.hi
            point,quad_error,tail=scipy_send_mass(
                scenario["mean"],scenario["S"],scenario["center"],Z)
            assert float(finite.lo) <= point <= float(finite.hi)
            output.append({
                "name":scenario["name"],"mean":str(scenario["mean"]),
                "variance":str(scenario["S"]),"center":str(scenario["center"]),
                "reference_bias":str(b),"finite_words_mass":finite.json(),
                "overflow_positive_upper":positive.json(),
                "overflow_negative_upper":negative.json(),
                "silence_mass":qsil.json(),"sum_contains_one":True,
                "direct_scipy_integral":point,"quad_error_estimate":quad_error,
                "scipy_tails_outside_12sigma_upper":tail,
                "riemann":quadrature
            })
    return output


def overflow_symbol_checks():
    rows=[]
    center=0.0
    for word in (-math.inf,math.inf):
        q=reference_step(AlphabetReading(center,word),F(1,4),F(1,5),F(2))
        assert q.lo==0 and q.hi.is_finite() and q.hi>0
        rows.append({"word":"-inf" if word<0 else "+inf","mass_upper":q.json(),
                     "numerical_lower_resolved":False})
    return rows


def selected_word_checks():
    tiny=math.ulp(0.0)
    words=[-tiny,-0.0,+0.0,tiny,
           math.nextafter(.5,-math.inf),.5,math.nextafter(.5,math.inf)]
    rows=[]
    for word in words:
        for bias in (F(0),F(1,4)):
            mass=finite_word_mass(word,bias,F(0),F(1,5),F(0),F(2))
            assert mass.lo>0 and mass.hi>=mass.lo
            rows.append({"word_hex":word.hex(),"bias":str(bias),"mass":mass.json(),
                         "positive_lower_resolved":True})
    return rows


def main():
    src=HERE/'center_provenance.json'
    if not src.exists():
        raise FileNotFoundError("Run center_source_audit.py first")
    provenance=json.loads(src.read_text(encoding='utf8'))
    assert all(row['generated_before_current_event'] and
               row['source_filter']==['prior_mean','phase'] for row in provenance['rows'])
    assert provenance['stage9_comparison']['absolute_center_variable_constructed'] is False
    model=json.loads((STAGE6/'model.json').read_text(encoding='utf8'))
    causal_readings=[Reading(float.fromhex(row['center_hex']),
                             None if row['word_hex'] is None else float.fromhex(row['word_hex']))
                     for row in provenance['rows']]
    _,causal_kernels=reference_sequence(causal_readings,model)
    assert all(kernel.lo>0 and kernel.hi<=1
               for kernels in causal_kernels.values() for kernel in kernels)
    result={
        "model":"Model A, continuous Gaussian measurement, shared pre-event center, nearest-even RN64 payload",
        "channel_input":"Y+b in exact real arithmetic, rounded once to binary64",
        "checks":{"cell_geometry":cell_contiguity_checks(),"normalization":normalizer_cases(),
                  "overflow_symbols":overflow_symbol_checks(),
                  "selected_finite_words":selected_word_checks()},
        "causal_history_kernel_checks":{"steps":len(causal_readings),
             "candidate_reference_biases":len(causal_kernels),
             "all_observed_conditional_masses_resolved":True},
        "provenance_sha256":hashlib.sha256(src.read_bytes()).hexdigest(),
        "stage9_source_audit":provenance['stage9_comparison'],
        "scope":"deterministic conditional-kernel arithmetic, no random performance samples"
    }
    files=[Path(__file__),HERE/'alphabet_audit.py',HERE/'center_source_audit.py',
           HERE/'center_provenance.json',
           R4A/'reference_kernel.py',R4A/'r4a_checks.py',
           R3/'mixture_history.py',
           HERE.parent/'paper2_stage10_numerical_contract_20261123'/'numerical_record.py',
           HERE.parent/'paper2_stage4_certified_correction_20261122'/'interval_arithmetic.py',
           STAGE6/'exact_linear.py',STAGE6/'model.json',
           HERE.parent/'paper2_stage9_cumulative_evidence_20261123'/'paired_recovery.py']
    result['sha256']={p.relative_to(HERE.parents[1]).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in files}
    (HERE/'final_checks.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
    print('PASS',len(result['checks']['normalization']),'normalization scenarios; signed-zero and overflow boundaries verified')
    print('stage9 absolute center logged:',provenance['stage9_comparison']['absolute_center_variable_constructed'])


if __name__=='__main__':
    main()
