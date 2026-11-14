"""Exact arithmetic audit of Si TIFS 2025 printed (49); not a filter.

Standard library only. No Zotero, simulation, randomness or cryptography.
The example concerns the printed universal bound, not its empirical figures.
An existing result is never overwritten. Run:
python checks/si_tifs_bound_check.py --output results/NEW_RUN/claims.json
"""
from __future__ import annotations

import argparse
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path


def matmul(a, b):
    return [[sum((a[i][k] * b[k][j] for k in range(len(b))), F(0))
             for j in range(len(b[0]))] for i in range(len(a))]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    ident = [[F(1), F(0)], [F(0), F(1)]]
    lap = [[F(1, 4), F(-1, 4)], [F(-1, 4), F(1, 4)]]
    phi = F(1, 10)
    g = [[ident[i][j] - (1 + phi) * lap[i][j] for j in range(2)]
         for i in range(2)]
    pred = [[F(1, 4) * ident[i][j] + F(1, 10) for j in range(2)]
            for i in range(2)]
    actual = matmul(matmul(g, pred), g)  # G is symmetric.
    a = [F(1)] * 10
    b1 = 1 + a[0] - a[1] - a[2] - a[6]
    printed = [[b1 * value for value in row] for row in actual]
    common = [[F(1)], [F(1)]]
    actual_q = matmul(matmul([[F(1), F(1)]], actual), common)[0][0]
    bound_q = matmul(matmul([[F(1), F(1)]], printed), common)[0][0]
    assert b1 == -1 and actual_q == F(9, 10) and bound_q == F(-9, 10)
    assert actual[0][0] - actual[0][1] == F(81, 1600)
    result = {
        'run_id': '20261114_si_tifs_r01',
        'source': {'doi': '10.1109/TIFS.2025.3588670',
                   'printed_page': 7445, 'formulas': ['49', '50', '52', '53']},
        'scope': 'Exact counterexample to printed universal second-moment bound; not Monte Carlo or new defense',
        'parameters': {'nodes': 2, 'A': F(1, 2), 'H': [0, 0],
                       'Q_common': F(1, 10), 'R': [1, 1],
                       'initial_error_second_moment': ident, 'L': lap,
                       'mask_identical': {'phi': phi, 'gamma': 1, 'sigma': 1, 'delta': 1},
                       'gain': 0, 'mask_additive_response': 0,
                       'consensus_updates': 1, 'all_a': a},
        'G': g, 'prediction_second_moment': pred,
        'actual_second_moment': actual, 'printed_b1': b1,
        'printed_upper_bound': printed,
        'test_vector': [1, 1], 'actual_quadratic_form': actual_q,
        'printed_bound_quadratic_form': bound_q,
        'bound_valid': False,
        'assumptions_checked_analytically': [
            'A stable and H=0 imply detectability',
            'L connected, undirected, with positive edge weight',
            'Initial error second moment positive definite',
            'Q and R positive; common process noise modeled jointly',
            'Identical nonzero gamma and positive phi/sigma/delta allowed',
            'L times the all-ones mask is zero, so B_n=0',
            'H=0 implies K=Theta=0 regardless of saturation',
            'All a_m=1 meet the printed positivity requirement'],
        'does_not_claim': ['All paper simulations invalid',
                           'No corrected upper bound exists',
                           'Any new fusion mechanism or empirical advantage'],
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'seed': None,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2,
                  default=lambda value: str(value) if isinstance(value, F) else value)
        stream.write('\n')
    print(f'PASS: exact printed-bound counterexample saved to {args.output}')


if __name__ == '__main__':
    main()
