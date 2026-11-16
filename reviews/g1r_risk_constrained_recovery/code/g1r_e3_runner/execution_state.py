from __future__ import annotations
import json
import traceback
import sys
from datetime import datetime, timezone

from .storage import write, digest
from .config_loader import canonical_sha256


def mark(directory, status, **context):
    write(directory/'run_status.json',{'status':status,'E3_executed':status=='COMPLETED',
        'timestamp_utc':datetime.now(timezone.utc).isoformat(),'context':context},replace=True)


def require_resumable_or_complete(directory, config, *, allow_complete=False):
    state=json.loads((directory/'run_status.json').read_text())
    allowed={'RUNNING','INTERRUPTED_RESUMABLE'}
    if allow_complete: allowed.add('COMPLETED')
    if state['status'] not in allowed: raise RuntimeError('E3 run is inconclusive/aborted; owner inspection required')
    stored=json.loads((directory/'config.json').read_text())
    if stored['experiment_config_sha256']!=config.config_sha256:
        raise ValueError('E3 checkpoint/config binding changed')


class Checkpoint:
    def __init__(self, directory, identity):
        self.directory=directory; self.path=directory/'checkpoint.json'; self.identity=identity
        self.completed={}
        if self.path.exists():
            record=json.loads(self.path.read_text())
            if canonical_sha256(record['payload'])!=record['sha256'] or record['payload']['identity']!=identity:
                raise ValueError('E3 checkpoint corrupted or identity differs')
            self.completed=record['payload']['completed']
            self.verify()

    def verify(self):
        for entry in self.completed.values():
            for name,sha in entry['files'].items():
                if digest(self.directory/name)!=sha: raise ValueError('completed E3 shard damaged: '+name)

    def done(self,key): return key in self.completed

    def complete(self,key,files):
        if key in self.completed: raise ValueError('duplicate completed E3 seed')
        self.completed[key]={'files':{p.relative_to(self.directory).as_posix():digest(p) for p in files}}
        payload={'identity':self.identity,'completed':self.completed}
        write(self.path,{'payload':payload,'sha256':canonical_sha256(payload)},replace=True)


def fail(directory, exc, context):
    interrupted=isinstance(exc,(KeyboardInterrupt,SystemExit))
    status='INTERRUPTED_RESUMABLE' if interrupted else 'ABORTED_INCONCLUSIVE'
    trace=''.join(traceback.format_exception(type(exc),exc,exc.__traceback__))
    # A late failure must never leave a publishable gate/statistics document.
    for name in ('statistics.json',):
        path=directory/name
        if path.exists():
            quarantine=directory/'failures'/f'{name}.unreleased'
            quarantine.parent.mkdir(parents=True,exist_ok=True)
            if not quarantine.exists(): path.rename(quarantine)
    try:
        import uuid
        write(directory/'failures'/f'{uuid.uuid4().hex}.json',{'status':status,'type':type(exc).__name__,
            'traceback':trace,'context':context})
        mark(directory,status,**context)
    except BaseException:
        print('E3 logging failure; run ineligible; preserve terminal evidence\n'+trace,file=sys.stderr)
        print(traceback.format_exc(),file=sys.stderr)
    return status
