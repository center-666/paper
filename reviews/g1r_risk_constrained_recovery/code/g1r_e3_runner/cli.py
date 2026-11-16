from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

from .config_loader import load_config, ROOT
from .authorization_guard import authorize, bindings


def main(argv=None):
    p=argparse.ArgumentParser(description='Independent guarded E3 runner; default read-only readiness')
    mode=p.add_mutually_exclusive_group()
    mode.add_argument('--formal-e3',action='store_true')
    mode.add_argument('--show-authorization-bindings',action='store_true')
    p.add_argument('--authorization',type=Path); p.add_argument('--out',type=Path)
    p.add_argument('--resume',action='store_true')
    args=p.parse_args(argv)
    try:
        config=load_config()
        if not args.formal_e3:
            print(json.dumps({'scope':'E3','authorized':False,'bindings':bindings(config),
                'E2_dependencies':dict(config.dependencies),'note':'read-only; no trajectories or bootstrap executed'},indent=2))
            return 0
        receipt=authorize(config,args.authorization)
        if args.out is None: raise ValueError('--out required for E3')
        from .batch_runner import BatchRunner
        out=args.out if args.out.is_absolute() else ROOT/args.out
        print(json.dumps(BatchRunner(config,receipt,out,resume=args.resume).run(),indent=2))
        return 0
    except (OSError,ValueError,RuntimeError) as exc:
        print(f'E3 stopped: {type(exc).__name__}: {exc}',file=sys.stderr)
        return 2


if __name__=='__main__': raise SystemExit(main())
