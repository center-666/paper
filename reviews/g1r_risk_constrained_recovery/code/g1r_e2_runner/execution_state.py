"""Execution failures are run failures, never synthetic algorithm observations."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import traceback
import uuid

from .result_writer import canonical_json_bytes, write_exclusive, write_replace_atomic


class ExecutionAborted(RuntimeError):
    pass


def emergency_marker(run_dir: Path) -> Path:
    key = hashlib.sha256(str(run_dir.resolve()).encode()).hexdigest()
    return Path(tempfile.gettempdir()) / 'g1r_e2_abort_markers' / (key + '.json')


def require_not_aborted(run_dir: Path) -> None:
    marker = emergency_marker(run_dir)
    failures = run_dir / 'execution_failures'
    if marker.is_file() or (failures.exists() and any(failures.glob('*.json'))):
        raise ExecutionAborted('ABORTED_INCONCLUSIVE: owner review required; automatic retry is forbidden')
    state = run_dir / 'run_status.json'
    if state.is_file():
        record = json.loads(state.read_text('utf-8'))
        if record.get('status') == 'ABORTED_INCONCLUSIVE':
            raise ExecutionAborted('ABORTED_INCONCLUSIVE: owner review required')


def set_state(run_dir: Path, status: str, context: dict | None = None) -> None:
    write_replace_atomic(run_dir / 'run_status.json', canonical_json_bytes({
        'status': status, 'context': context or {},
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'e3_executed': False,
    }))


def record_failure(run_dir: Path, exc: BaseException, context: dict,
                   interrupted: bool = False) -> dict:
    status = 'INTERRUPTED_RESUMABLE' if interrupted else 'ABORTED_INCONCLUSIVE'
    record = {
        'status': status, 'exception_type': type(exc).__name__, 'message': str(exc),
        'traceback': ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
        'context': dict(context), 'run_dir': str(run_dir),
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'algorithm_outcome': False, 'seed_marked_complete': False,
        'automatic_retry': False,
    }
    folder = 'interruptions' if interrupted else 'execution_failures'
    target = run_dir / folder / (uuid.uuid4().hex + '.json')
    errors = []
    gate = run_dir / 'gate_counts.json'
    if gate.exists():
        try:
            quarantine = run_dir / folder / (uuid.uuid4().hex + '.gate_counts.unreleased.json')
            quarantine.parent.mkdir(parents=True, exist_ok=True)
            gate.rename(quarantine)
            record['quarantined_gate_counts'] = str(quarantine)
        except Exception as logging_exc:
            errors.append(repr(logging_exc))
    try:
        write_exclusive(target, canonical_json_bytes(record))
        record['record_path'] = str(target)
    except Exception as logging_exc:
        errors.append(repr(logging_exc))
    try:
        set_state(run_dir, status, context)
    except Exception as logging_exc:
        errors.append(repr(logging_exc))
    if errors:
        record['logging_failures'] = errors
        # A second writable volume may remain available after Run-disk failure.
        # A subsequent launch checks this deterministic emergency marker too.
        if not interrupted:
            try:
                write_replace_atomic(emergency_marker(run_dir), canonical_json_bytes(record))
            except Exception as fallback_exc:
                record['emergency_logging_failure'] = repr(fallback_exc)
        print(json.dumps(record, ensure_ascii=True), file=sys.stderr, flush=True)
    return record

