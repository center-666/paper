from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
import json

from ..g1r_e2_runner.config_loader import (ROOT, BASE, canonical_sha256, sha256_file,
                                         load_frozen_config, load_public_model)

E2_RUN = BASE / 'results/g1r_e2_run_20261116_001'
COVERAGE = BASE / 'results/g1r_e2_independent_coverage_20261116_r01'
SCAN = BASE / 'results/g1r_e3_seed_audit_20261116_r02/summary.json'
PREP = BASE / 'e3_preparation_config.json'


@dataclass(frozen=True)
class E3Config:
    shared: object
    normal_seeds: tuple
    attack_seeds: tuple
    bootstrap_seed: int
    bootstrap_resamples: int
    dependencies: object
    config_sha256: str
    seed_scan_sha256: str
    plan_sha256: str

    @property
    def base(self): return self.shared.base

    @property
    def root(self): return self.shared.root

    @property
    def methods(self): return self.shared.methods

    @property
    def events(self): return self.shared.events

    @property
    def ages(self): return self.shared.ages


def verify_e2_assets():
    manifest = json.loads((E2_RUN/'artifact_manifest.json').read_text(encoding='utf-8'))
    if sha256_file(E2_RUN/'artifact_manifest.json') != '40980383b61a63bc32d026f1db76c2066af7958d27e42792ab1eca27f9b3fd50':
        raise ValueError('E2 dependency manifest changed')
    for rel, digest in manifest['files_sha256'].items():
        if sha256_file(E2_RUN/rel) != digest:
            raise ValueError('E2 dependency corrupted: ' + rel)
    if json.loads((E2_RUN/'run_status.json').read_text())['status'] != 'COMPLETED':
        raise ValueError('E2 is not completed')
    return manifest


def load_config():
    shared = load_frozen_config(ROOT)
    plan = json.loads(PREP.read_text(encoding='utf-8'))
    verify_e2_assets()
    coverage = json.loads((COVERAGE/'summary.json').read_text())
    if (coverage['status'] != 'PASS' or coverage['unique_cases'] != 4800
            or coverage['mismatches'] or coverage['main_coverage'] != {'n': 200, 'covered': 200}):
        raise ValueError('independent E2 coverage not passed')
    scan = json.loads(SCAN.read_text())
    if (scan['status'] != 'PASS_NO_CONSUMPTION_IN_SCANNED_SCOPE'
            or scan['collision_count'] or scan['unresolved_count'] or scan['scan_errors']
            or len(scan['per_seed']) != 401):
        raise ValueError('E3 seed collision audit incomplete')
    dependencies = plan['dependency_sha256']
    for rel, digest in dependencies.items():
        if sha256_file(ROOT/rel) != digest:
            raise ValueError('E3 frozen dependency changed: ' + rel)
    def seeds(key):
        r = shared.protocol['seed_reservations'][key]
        return tuple(range(int(r['start']), int(r['start'])+int(r['count'])))
    normal, attack = seeds('e3_normal'), seeds('e3_attack')
    boot = seeds('e3_statistics')
    if normal != tuple(range(141440000,141440200)) or attack != tuple(range(141450000,141450200)) or boot != (141460000,):
        raise ValueError('E3 seed plan changed')
    if int(shared.protocol['e3_bootstrap_resamples']) != 1999:
        raise ValueError('E3 bootstrap plan changed')
    contract = {'plan_sha256': sha256_file(PREP), 'seed_scan_sha256': sha256_file(SCAN),
                'e2_config_sha256': shared.runner_config_sha256,
                'normal_seeds': normal, 'attack_seeds': attack, 'bootstrap_seed': boot[0],
                'bootstrap_resamples': 1999, 'environment_fingerprint': dict(shared.environment_fingerprint),
                'dependencies': dependencies}
    return E3Config(shared, normal, attack, boot[0], 1999,
                    MappingProxyType(dependencies), canonical_sha256(contract), sha256_file(SCAN), sha256_file(PREP))


def public_model(config):
    return load_public_model(config.shared)
