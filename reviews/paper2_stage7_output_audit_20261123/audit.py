"""Audit the supplied shadow replay and the binary64 action on frozen seeds."""

import argparse
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction as F
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile
import zlib

os.environ['OPENBLAS_NUM_THREADS'] = '1'
import numpy as np
from scipy.stats import t as student_t

from output_certificate import certify_output

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STAGE6 = HERE.parent / 'paper2_stage6_vector_correction_20261122'
STAGE7 = HERE.parent / 'paper2_stage7_fixed_amplitude_20261122'
sys.path.insert(0, str(STAGE7))
from fresh_confirmation import verify_frozen
from fixed_amplitude import capped_halfspace_action, interval_fraction, transport_halfspace
from direction_cache_corrected import CorrectedFastEnvelope
from exact_linear import asfloat
from interval_arithmetic import Interval


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def check_zip(zip_path):
    with ZipFile(zip_path) as archive:
        def get(name):
            return json.loads(archive.read(f'stage7_parameter_memory/{name}.json'))

        anchors = get('anchors_stage6_strong')
        replay = get('shadow_replay_results')['results']
        supplied = get('summary_statistics')
        exact_checks = get('exact_test_results')
    freeze = read(STAGE7 / 'stage7_freeze.json')
    assert anchors['source_commit'] == freeze['baseline_commit']
    fingerprint_rows = []
    gains = []
    baseline_error = 0.
    for index, row in enumerate(replay):
        path = STAGE6 / 'results_v2/final' / f'b0.25_episode{index:03d}.json'
        relative = path.relative_to(ROOT).as_posix()
        original = subprocess.check_output(['git', 'show', f"{anchors['source_commit']}:{relative}"], cwd=ROOT)
        assert hashlib.sha256(original).hexdigest() == freeze['stage6_final_trace_manifest'][path.name]
        frozen = json.loads(original)
        successful = [[q['time'], F(str(q['level'])), *map(F, q['direction']), F(q['target_support'])]
                      for q in frozen['certificate_queries'] if q['certified']]
        claimed = [[ti, *map(F, coordinates)] for ti, *coordinates in anchors['episodes'][str(index)]]
        assert successful == claimed and row['episode'] == index
        for ti, level, d0, d1, target in anchors['episodes'][str(index)]:
            fingerprint_rows.append('|'.join(map(str, (index, ti, f'{float(level):.3f}', d0, d1, target))))
        baseline_error = max(baseline_error, abs(row['old'] - frozen['snapshots']['512']['certified_gain']))
        gains.append(row['new'] - row['old'])
    assert len(replay) == 12 and len(fingerprint_rows) == 27 and baseline_error < 1e-8
    fingerprint = f'{zlib.crc32(chr(10).join(fingerprint_rows).encode()):08x}'
    assert fingerprint == supplied['anchor_checksum'] == '2a7a8967'
    mean = float(np.mean(gains))
    ci = list(student_t.interval(.95, len(gains) - 1, loc=mean, scale=np.std(gains, ddof=1) / np.sqrt(len(gains))))
    np.testing.assert_allclose([mean, *ci], [supplied['paired_new_minus_old']['mean'],
                                           *supplied['paired_new_minus_old']['descriptive_t95']], atol=1e-12)
    return {'zip_sha256': hashlib.sha256(zip_path.read_bytes()).hexdigest(), 'anchors': len(fingerprint_rows),
            'fingerprint': fingerprint, 'baseline_max_abs_error': baseline_error, 'paired_difference': mean,
            'descriptive_ci95': ci, 'supplied_exact_check_record': exact_checks}


def audit_episode(path):
    archived = read(path)
    cfg = read(STAGE7 / 'fresh_protocol.json')
    model = read(STAGE6 / 'model.json')
    b = archived['b']
    seed_case = cfg['attack_strengths'].index(b)
    assert archived['seed'] == cfg['seed'] and archived['full_certificate_search']
    freeze_bytes = (STAGE7 / 'fresh_confirmation_freeze.json').read_bytes()
    assert archived['freeze_sha256'] == hashlib.sha256(freeze_bytes).hexdigest()
    phys, events, phase = [np.random.default_rng(s) for s in np.random.SeedSequence(
        [cfg['seed'], seed_case, archived['episode']]).spawn(3)]
    A, C, Q = (np.asarray(model[key], float) for key in ('A', 'C', 'Q'))
    noise_factor = np.linalg.cholesky(Q)
    sigma = math.sqrt(float(model['R']))
    Z, delta = (float(model[key]) for key in ('Z', 'quantization_half_width'))
    cap = F(str(cfg['output_l1_cap']))
    start = cfg['attack_start']
    error = np.linalg.cholesky(np.array(model['P0_prior'], float)) @ phys.normal(size=2)
    envelope = CorrectedFastEnvelope(model, track_responses=bool(archived['successful_certificates']))
    certificates = {}
    for row in archived['successful_certificates']:
        certificates.setdefault(row['time'], []).append(row)
    assert [tuple([q['time'], tuple(map(F, q['direction'])), F(q['target_support'])])
            for q in archived['certificate_queries'] if q['certified']] == [
        (q['time'], tuple(map(F, q['direction'])), F(q['z'])) for q in archived['successful_certificates']]

    old = None
    exact_gain = 0.
    nominal_certified = 0.
    emitted_gain = 0.
    emitted_certified = 0.
    max_bound_gap = 0.
    corrected_ticks = 0
    fallbacks = 0
    state_bounds = [Interval.exact(0), Interval.exact(0)]
    for tick in range(archived['steps']):
        v = sigma * phys.normal()
        w = noise_factor @ phys.normal(size=2)
        center = 0. if tick == 0 else delta * (2 * phase.random() - 1)
        y = float((C @ error).item() + v)
        sent = bool(events.random() > math.exp(-.5 * Z * (y - center)**2))
        amplitude = b if sent and tick >= start else 0.
        Fmat, gain = envelope.advance(sent)
        K = np.array(asfloat(gain), float).ravel()
        post_error = error - K * (y + amplitude) if sent else error - K * center
        if envelope.track_responses:
            old = transport_halfspace(old, Fmat, gain, sent, envelope.bmax)
            amplitude_box = Interval(Interval.exact(0).lo, interval_fraction(envelope.bmax).hi) if sent else Interval.exact(0)
            state_bounds = [sum((interval_fraction(c) * bound for c, bound in zip(row, state_bounds)),
                                Interval.exact(0)) + interval_fraction(g[0]) * amplitude_box
                            for row, g in zip(Fmat, gain)]
            for row in certificates.get(tick, ()):
                direction = tuple(map(F, row['direction']))
                target = F(row['z'])
                envelope.add_certificate(direction, target)
                if capped_halfspace_action((direction, target), envelope.W, cap)[1] > capped_halfspace_action(old, envelope.W, cap)[1]:
                    old = (direction, target)
        baseline_action, baseline_bound = capped_halfspace_action(old, envelope.W, cap)
        action, bound = (F(0), F(0)), F(0)
        for direction in envelope.direction_cache:
            candidate = envelope.directional_action(direction, cap)
            if candidate['guaranteed_gain'] > bound:
                action, bound = candidate['action'], candidate['guaranteed_gain']
        if bound < baseline_bound:
            action, bound = baseline_action, baseline_bound
        if tick >= start and bound:
            magnitude = tuple(max(abs(F(x.lo)), abs(F(x.hi))) for x in state_bounds)
            output, output_bound, fallback = certify_output(action, bound, magnitude, envelope.W, cap)
            assert sum(abs(F.from_float(x)) for x in output) <= cap and output_bound >= 0
            fallbacks += fallback
            corrected_ticks += 1
            post_nominal = post_error + np.array(tuple(map(float, action)))
            post_emitted = post_error + np.array(output)
            exact_gain += float(post_error @ post_error - post_nominal @ post_nominal)
            emitted_gain += float(post_error @ post_error - post_emitted @ post_emitted)
            nominal_certified += float(bound)
            emitted_certified += float(output_bound)
            max_bound_gap = max(max_bound_gap, abs(float(bound - output_bound)))
        error = A @ post_error + w
    target = archived['snapshots']['512']
    np.testing.assert_allclose([exact_gain, nominal_certified], [target['new_gain'], target['new_gcert']], atol=1e-8, rtol=0)
    return {'amplitude': b, 'episode': archived['episode'], 'nonzero_nominal_actions': corrected_ticks,
            'zero_fallbacks': fallbacks, 'nominal_gain': exact_gain, 'emitted_gain': emitted_gain,
            'nominal_certified_sum': nominal_certified, 'emitted_certified_sum': emitted_certified,
            'max_absolute_step_bound_change': max_bound_gap}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('zip', type=Path, nargs='?', default=HERE / 'stage7_parameter_memory_research_20261122.zip')
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    verify_frozen()
    shadow = check_zip(args.zip)
    print('Verified shadow replay sources and paired summary.', flush=True)
    paths = sorted((STAGE7 / 'results/fresh_confirmation').glob('b*_episode*.json'))
    assert len(paths) == 36
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        episodes = list(pool.map(audit_episode, paths))
    assert all(sum(row['amplitude'] == b for row in episodes) == 12 for b in (0., .1, .25))
    result = {'status': 'PASS', 'shadow': shadow, 'archive_replay_episodes': episodes,
              'nonzero_nominal_actions': sum(row['nonzero_nominal_actions'] for row in episodes),
              'zero_fallbacks': sum(row['zero_fallbacks'] for row in episodes),
              'max_sample_gain_change': max(abs(row['nominal_gain'] - row['emitted_gain']) for row in episodes),
              'max_absolute_step_bound_change': max(row['max_absolute_step_bound_change'] for row in episodes),
              'scope': 'Stored certificates and seeded defender replay. No new likelihood search or random sample.'}
    (HERE / 'audit_results.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    print({key: value for key, value in result.items() if key not in ('shadow', 'archive_replay_episodes')})


if __name__ == '__main__':
    main()
