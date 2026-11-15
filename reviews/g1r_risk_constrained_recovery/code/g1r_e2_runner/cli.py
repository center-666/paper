from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .authorization_guard import AuthorizationError, authorize
from .batch_runner import BatchRunner
from .config_loader import BASE, ROOT, load_frozen_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Guarded G1-R E2 runner")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true",
                      help="use existing Debug cache and fixture seed 0 only (default)")
    mode.add_argument("--formal-e2", action="store_true",
                      help="requires a valid separately supplied owner authorization file")
    parser.add_argument("--authorization", type=Path,
                        help="owner-provided E2 authorization JSON; never created by this runner")
    parser.add_argument("--out", type=Path,
                        help="new dry-run or formal Run directory; existing results are never replaced")
    return parser


def execution_mode(args) -> str:
    return "formal_e2" if args.formal_e2 else "dry_run"


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    mode = execution_mode(args)
    try:
        config = load_frozen_config(ROOT)
        receipt = authorize(mode, config, args.authorization)
        if mode == "dry_run":
            out = args.out or (BASE / "results/g1r_e2_runner_dryrun_20261115_r01")
        else:
            if args.out is None:
                raise AuthorizationError("formal E2 requires a new --out Run directory")
            out = args.out
        if not out.is_absolute():
            out = ROOT / out
        runner = BatchRunner(config, receipt, out)
        result = (runner.run_formal_e2() if mode == "formal_e2"
                  else runner.run_dry_run())
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (AuthorizationError, PermissionError, FileExistsError, ValueError,
            RuntimeError, OSError) as exc:
        print(f"E2 runner stopped: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
