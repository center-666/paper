"""Deterministic parallel scheduling of frozen cases; no data-based tuning."""
import os
for key in ("OPENBLAS_NUM_THREADS","OMP_NUM_THREADS","MKL_NUM_THREADS"):
    os.environ[key]="1"
import argparse
from concurrent.futures import ProcessPoolExecutor,as_completed
from pathlib import Path
import json
from run_experiment import HERE,run_job,write,sha,check_frozen


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("stage",choices=["screen","final","health_screen","health_final","offgrid"])
    args=parser.parse_args()
    check_frozen()
    p=json.loads((HERE/"protocol.json").read_text(encoding="utf8"))
    if args.stage in ("final","health_final","offgrid") and not (HERE/"results/screen/completion.json").exists():
        raise SystemExit("Complete screen before independent confirmation")
    if args.stage.startswith("health"):
        jobs=[(args.stage,mi,0,0) for mi in range(2)]
    else:
        offgrid=args.stage=="offgrid"
        jobs=[(args.stage,mi,bi,oi) for mi in range(2)
              for bi in range(2 if offgrid else 3) for oi in range(1 if offgrid else 4)]
    startpath=HERE/"results"/args.stage/"start.json"
    if startpath.exists():
        raise SystemExit("Stage already started; output overwrite prohibited")
    write(startpath,{"stage":args.stage,"jobs":jobs,"workers":6,"freeze_sha256":sha(HERE/"freeze.json"),
                     "source_sha256":sha(Path(__file__)),"parameters_retuned":False})
    with ProcessPoolExecutor(max_workers=6) as pool:
        for f in as_completed([pool.submit(run_job,job) for job in jobs]):
            name,seconds=f.result()
            print(name,"done",round(seconds,2),"s",flush=True)
    write(HERE/"results"/args.stage/"completion.json",{"stage":args.stage,"cases":len(jobs),"status":"COMPLETE"})


if __name__=="__main__":
    main()
