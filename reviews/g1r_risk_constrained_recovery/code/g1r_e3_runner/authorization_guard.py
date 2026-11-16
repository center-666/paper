from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json

from .config_loader import PREP, SCAN, canonical_sha256, sha256_file
from ..g1r_e2_runner.authorization_guard import runner_source_sha256
from ..g1r_e2_runner.environment_guard import verify_environment

_SEAL = object()


class AuthorizationError(PermissionError): pass


@dataclass(frozen=True)
class E3Authorization:
    scope: str
    owner: str
    authorization_id: str
    file_sha256: str
    bindings: tuple
    _seal: object = field(default=None, repr=False)


def bindings(config):
    verify_environment(config.shared)
    if sha256_file(PREP)!=config.plan_sha256 or sha256_file(SCAN)!=config.seed_scan_sha256:
        raise AuthorizationError('E3 configuration/seed scan changed after loading')
    for relative, expected in config.dependencies.items():
        if sha256_file(config.root/relative)!=expected:
            raise AuthorizationError('E3 frozen dependency damaged/changed: '+relative)
    paths = sorted(Path(__file__).parent.rglob('*.py')) + [Path(__file__).parent/'authorization_template.json',
        Path(__file__).parent.parent/'audit_e2_independent_coverage.py',
        Path(__file__).parent.parent/'audit_e3_seed_collisions.py',
        Path(__file__).parent.parent/'audit_e3_preparation.py']
    paths = [p for p in paths if '__pycache__' not in p.parts]
    files = [(p.relative_to(config.root).as_posix(), sha256_file(p)) for p in paths]
    files.append(('frozen_e2_algorithms_and_yang_dependencies', runner_source_sha256(config.shared)))
    return {'final_code_sha256': canonical_sha256(sorted(files)),
            'protocol_sha256': config.shared.protocol_sha256,
            'calibration_thresholds_sha256': config.shared.thresholds_sha256,
            'seed_list_sha256': canonical_sha256({'normal': config.normal_seeds,
                'attack': config.attack_seeds, 'bootstrap': config.bootstrap_seed}),
            'experiment_config_sha256': config.config_sha256}


def authorize(config, path: Path | None):
    verify_environment(config.shared)
    if path is None or not path.is_file():
        raise AuthorizationError('E3 blocked: separately owner-issued E3 authorization required')
    record = json.loads(path.read_text(encoding='utf-8'))
    if record.get('scope') != 'E3' or record.get('authorized') is not True:
        raise AuthorizationError('E3 blocked: E2 authorization or unauthorized template is invalid')
    if not str(record.get('owner','')).strip() or not str(record.get('authorization_id','')).strip():
        raise AuthorizationError('E3 owner/ID missing')
    expected = bindings(config)
    if record.get('bindings') != expected:
        raise AuthorizationError('E3 five bindings mismatch')
    return E3Authorization('E3', record['owner'], record['authorization_id'],
                           sha256_file(path), tuple(sorted(expected.items())), _SEAL)


def require(config, receipt):
    if (type(receipt) is not E3Authorization or receipt._seal is not _SEAL
            or receipt.scope != 'E3' or not receipt.file_sha256):
        raise AuthorizationError('invalid E3 receipt; no E2 receipts accepted')
    if receipt.bindings != tuple(sorted(bindings(config).items())):
        raise AuthorizationError('stale E3 authorization')
    for path in (PREP, SCAN):
        if not path.is_file(): raise AuthorizationError('missing E3 readiness asset')
