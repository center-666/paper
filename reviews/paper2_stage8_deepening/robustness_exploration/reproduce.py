"""One-command report regeneration or seed-to-score validation of the archived runs."""
from __future__ import annotations
import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
sys.dont_write_bytecode = True
ROOT=Path(__file__).resolve().parent


def run(*args):
    subprocess.run([sys.executable,"-B",*args],cwd=ROOT,check=True)


def set_replay_root(directory):
    import stable_sweep
    stable_sweep.ROOT=Path(directory)


def stable_replay(workers):
    import stable_sweep as sweep
    registration=json.loads((ROOT/"stable_registration.json").read_text(encoding="utf8"))
    assert registration==sweep.configuration()
    with tempfile.TemporaryDirectory(dir=ROOT,prefix="stable_replay_") as directory:
        scratch=Path(directory)
        shutil.copyfile(ROOT/"stable_registration.json",scratch/"stable_registration.json")
        comparison=scratch/"data/quantization"
        comparison.mkdir(parents=True)
        for g in sweep.GROUPS:
            name=f"continuous_{g}_00.json"
            shutil.copyfile(ROOT/"data/quantization"/name,comparison/name)
        with ProcessPoolExecutor(workers,initializer=set_replay_root,initargs=(directory,)) as pool:
            for percent in sweep.EPS:
                for g in sweep.GROUPS:
                    ids=range(1 if percent==0 else 12)
                    for first in range(0,len(ids),6):
                        jobs=[pool.submit(sweep.run_trial,percent,g,i) for i in ids[first:first+6]]
                        for result in jobs: result.result()
        for path in (ROOT/"stable_data").glob("*.json"):
            old=sweep.frozen.read(path)
            new=sweep.frozen.read(scratch/"stable_data"/path.name)
            assert new["public_history_sha256"]==old["public_history_sha256"],path.name
            for name,metrics in old["metrics"].items():
                for field,v in metrics.items():
                    got=new["metrics"][name][field]
                    assert got==v or isinstance(v,float) and math.isclose(got,v,rel_tol=1e-12,abs_tol=1e-10),(path.name,name,field)
    print("stable hydraulic full seed replay passed")


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--from-seeds",action="store_true",help="recompute trajectories using the registered seed schedule")
    p.add_argument("--workers",type=int,default=4)
    args=p.parse_args()
    if args.from_seeds:
        run("replay_registered.py","--all","--workers",str(args.workers))
        stable_replay(args.workers)
        run("fixed_prefix.py","--verify","--workers",str(args.workers))
        import ablate_direction
        import audit_drift
        import replay_registered
        with ProcessPoolExecutor(args.workers,initializer=replay_registered.load_kernel,initargs=(2,)) as pool:
            audits=list(pool.map(audit_drift.check,sorted((ROOT/"data_v2/drift").glob("decay_*.json"))))
        with ProcessPoolExecutor(args.workers) as pool:
            ablations=list(pool.map(ablate_direction.score,[(g,i) for g in ablate_direction.GROUPS for i in range(12)]))
        for new,old in [(audits,json.loads((ROOT/"drift_oracle_audit.json").read_bytes())),
                        (ablations,json.loads((ROOT/"direction_ablation.json").read_bytes())["rows"])]:
            assert [{k:v for k,v in row.items() if k!="cpu_seconds"} for row in new]==[
                {k:v for k,v in row.items() if k!="cpu_seconds"} for row in old]
    run("rebuild_report_bundle.py")


if __name__=="__main__":
    main()
