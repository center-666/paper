"""Independent QR/covariance-eigendecomposition audit; no simulator or set helpers."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.linalg import solve_triangular
from scipy.stats import chi2

from .g1r_e2_runner.config_loader import ROOT, load_frozen_config, load_public_model


def independent_cover(z, delta, model):
    sigma = np.asarray(model['Sigma_eta'], dtype=float)
    whiten = np.linalg.cholesky(sigma)
    zw = solve_triangular(whiten, np.asarray(z), lower=True)
    p = np.asarray(delta, dtype=float)
    if zw.shape != (12,) or p.shape != (2,) or not np.isfinite(zw).all() or not np.isfinite(p).all():
        raise ValueError('invalid independent coverage input')
    details = []
    for event in model['events']:
        O = np.asarray(event['O']); G = np.asarray(event['G'])
        X = solve_triangular(whiten, O, lower=True)
        Q, R = np.linalg.qr(X, mode='reduced')
        if np.linalg.matrix_rank(R, tol=1e-12 * np.linalg.norm(R, 2)) != 2:
            raise ValueError('rank-deficient parameter model')
        theta = solve_triangular(R, Q.T @ zw)
        residual = zw - X @ theta
        residual2 = float(residual @ residual)
        guard = 128 * np.finfo(float).eps * max(1., abs(residual2))
        compatible = residual2 - guard <= float(model['t_r'])
        # G R^-1 maps the parameter confidence ball directly to state space.
        GR = solve_triangular(R.T, G.T, lower=True).T
        covariance = float(model['t_Q']) * (GR @ GR.T)
        covariance = (covariance + covariance.T) / 2
        eigen, basis = np.linalg.eigh(covariance)
        if eigen[0] < -1e-12 * max(1., np.max(np.abs(eigen))):
            raise ValueError('indefinite impact covariance')
        radii = np.sqrt(np.maximum(eigen, 0.))
        scale = max(1., float(radii.max()))
        active = radii > 1e-12 * scale
        offset = basis.T @ (p - G @ theta)
        off_range = float(np.linalg.norm(offset[~active]))
        radius2 = float(np.sum(offset[active] ** 2 / eigen[active]))
        member = off_range <= 1e-9 * scale and radius2 <= 1. + 1e-9
        details.append({'event': [int(event['edge']), int(event['r'])],
                        'theta': theta.tolist(), 'residual_squared': residual2,
                        'compatible': bool(compatible), 'center': (G @ theta).tolist(),
                        'impact_covariance': covariance.tolist(),
                        'rank': int(active.sum()), 'radius_squared': radius2,
                        'off_range_norm': off_range, 'member': bool(member)})
    return any(d['compatible'] and d['member'] for d in details), details


def audit(output: Path):
    if output.exists():
        raise FileExistsError(output)
    cfg = load_frozen_config(ROOT); model = load_public_model(cfg)
    assert abs(model['t_Q'] - chi2.ppf(1-cfg.protocol['beta_parameter']/8, 2)) < 1e-12
    assert abs(model['t_r'] - chi2.ppf(1-cfg.protocol['beta_compatibility']/8, 10)) < 1e-12
    run = cfg.base / 'results/g1r_e2_run_20261116_001'
    manifest = json.loads((run/'artifact_manifest.json').read_text(encoding='utf-8'))
    for rel, digest in manifest['files_sha256'].items():
        if hashlib.sha256((run/rel).read_bytes()).hexdigest() != digest:
            raise ValueError('E2 asset damaged: ' + rel)
    truth = defaultdict(list)
    for batch in sorted(run.glob('attack_batch_*.csv')):
        with batch.open(encoding='utf-8', newline='') as f:
            for row in csv.DictReader(f):
                key = (int(row['seed']), tuple(json.loads(row['event'])), int(row['age']))
                truth[key].append(row)
    expected = {(s, e, a) for s in cfg.attack_seeds for e in cfg.events for a in cfg.ages}
    assert set(truth) == expected and len(truth) == 4800
    rows, mismatches, strata = [], [], defaultdict(lambda: {'n': 0, 'covered': 0})
    for (seed, event, age), group in sorted(truth.items()):
        assert len(group) == 3 and {r['method'] for r in group} == set(cfg.methods)
        proposals = [json.loads(line)['proposal'] for line in
                     (run/'seed_shards'/f'attack_batch_{(seed-141430000)//20:02d}_seed_{seed}_online.jsonl').read_text(encoding='utf-8').splitlines()]
        zs = [proposals[int(r['online_record_ordinal'])]['z'] for r in group]
        impacts = [[float(r['true_impact_x']), float(r['true_impact_y'])] for r in group]
        assert all(z == zs[0] for z in zs) and all(d == impacts[0] for d in impacts)
        original = [r['coverage_confirmed'].lower() == 'true' for r in group]
        assert len(set(original)) == 1
        cover, detail = independent_cover(zs[0], impacts[0], model)
        item = {'seed': seed, 'event': list(event), 'age': age,
                'independent_covered': cover, 'original_covered': original[0],
                'candidate_details': detail}
        rows.append(item)
        key = f'{event[0]}:{event[1]}@{age}'; strata[key]['n'] += 1; strata[key]['covered'] += cover
        if cover != original[0]: mismatches.append(item)
    output.mkdir(parents=True)
    detail_path = output/'coverage_cases.jsonl'
    detail_path.write_bytes(b''.join((json.dumps(r, sort_keys=True, allow_nan=False)+'\n').encode() for r in rows))
    summary = {'status': 'PASS' if not mismatches else 'FAIL_STOP_E3_PREPARATION',
               'unique_cases': len(rows), 'method_duplicate_rows': 14400,
               'mismatches': mismatches, 'strata': dict(strata),
               'main_coverage': strata['0:200@64'],
               'definition': 'one shared compatible candidate impact union; NOT three detection rates',
               'implementation': 'whitened QR GLS; G R^-1 covariance; spectral range/Mahalanobis membership',
               'original_coverage_helpers_called': False, 'new_trajectories': 0,
               'protocol_sha256': cfg.protocol_sha256, 'matrix_sha256': cfg.matrix_sha256,
               'e2_manifest_sha256': hashlib.sha256((run/'artifact_manifest.json').read_bytes()).hexdigest(),
               'details_sha256': hashlib.sha256(detail_path.read_bytes()).hexdigest()}
    (output/'summary.json').write_bytes((json.dumps(summary, indent=2, sort_keys=True)+'\n').encode())
    print(json.dumps({k: summary[k] for k in ('status','unique_cases','main_coverage','mismatches')}, indent=2))
    if mismatches: raise RuntimeError('independent coverage mismatch; stop E3 preparation')
    return summary


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--out', type=Path, required=True)
    audit(p.parse_args().out.resolve())
