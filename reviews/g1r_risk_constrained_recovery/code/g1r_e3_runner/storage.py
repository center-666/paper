from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import os
import tempfile


def encoded(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':'), allow_nan=False)+'\n').encode()


def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path: Path, value, *, replace=False):
    payload = encoded(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not replace:
        if path.read_bytes()!=payload: raise ValueError('immutable E3 file differs: '+str(path))
        return digest(path)
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix='.tmp')
    try:
        with os.fdopen(fd,'wb') as f:
            f.write(payload); f.flush(); os.fsync(f.fileno())
        if replace: os.replace(temp,path)
        else: os.link(temp,path)
    finally:
        if os.path.exists(temp): os.unlink(temp)
    return digest(path)


@dataclass(frozen=True)
class PersistedProposal:
    path: Path
    sha256: str

    def read(self):
        if digest(self.path)!=self.sha256: raise ValueError('persisted proposal damaged')
        from .config_loader import canonical_sha256
        data=json.loads(self.path.read_text())
        if canonical_sha256(data['proposal'])!=data['record_sha256']:
            raise ValueError('proposal content digest differs')
        return data['proposal']


def persist_proposal(path, record):
    payload=record.payload()
    sha=write(path,{'record_sha256':record.record_sha256,'proposal':payload})
    return PersistedProposal(path,sha)


def verify_manifest(directory):
    manifest=json.loads((directory/'artifact_manifest.json').read_text())
    actual={p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file() and p.name!='artifact_manifest.json'}
    if actual!=set(manifest['files_sha256']): raise ValueError('artifact inventory mismatch')
    for name,sha in manifest['files_sha256'].items():
        if digest(directory/name)!=sha: raise ValueError('artifact damaged: '+name)
    return manifest


def manifest(directory, metadata):
    files={p.relative_to(directory).as_posix():digest(p) for p in sorted(directory.rglob('*')) if p.is_file() and p.name!='artifact_manifest.json'}
    write(directory/'artifact_manifest.json',{**metadata,'files_sha256':files})
