"""Run development or a registered confirmation, with per-ID atomic checkpoints."""
from __future__ import annotations
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import traceback
import uuid

from engine import TASK, MODEL, simulate, evaluate

CASES = {"strong_early": (.25,50), "strong_late": (.25,96),
         "weak_early": (.10,50), "weak_late": (.10,96), "health": (0.,50)}
DEV_SEED = 202611251703

def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix("." + uuid.uuid4().hex + ".tmp")
    tmp.write_text(json.dumps(data,allow_nan=False,ensure_ascii=False)+"\n",encoding="utf8",newline="\n")
    os.replace(tmp,path)

def read(p):
    return json.loads(p.read_text(encoding="utf8"))

def digest(p):
    # Frozen inputs are UTF-8 text. Match Git LF blobs on Windows checkouts.
    return hashlib.sha256(p.read_bytes().replace(b"\r\n",b"\n")).hexdigest()

def trial(group, index, seed, thresholds, phase, identity):
    outdir = TASK/"results"/phase
    ident = f"{group}-{index:04d}"
    path = outdir/(ident+".json")
    if path.exists():
        row = read(path)
        if (row["id"],row["seed"],row["identity"]) != (ident,seed,identity):
            raise ValueError("Checkpoint identity mismatch")
        return ident
    lock = path.with_suffix(".lock")
    # OS file lock is released automatically if the process exits.
    import msvcrt
    with lock.open("a+b") as stream:
        stream.seek(0)
        msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
        if path.exists():
            return ident
        try:
            b,k = CASES[group]
            wall, cpu = time.perf_counter(), time.process_time()
            pub,priv = simulate(seed,list(CASES).index(group),index,b,k)
            data = evaluate(pub,priv,b,k,thresholds)
            data.update(id=ident,group=group,episode=index,phase=phase,seed=seed,identity=identity,
                        seconds=time.perf_counter()-wall, cpu=time.process_time()-cpu)
            save(path,data)
            print(phase,ident,round(data["seconds"],1),"s",flush=True)
        except Exception:
            save(outdir/"errors"/(ident+"-"+str(time.time_ns())+".json"),
                 dict(id=ident,identity=identity,seed=seed,trace=traceback.format_exc()))
            raise
    return ident

def warmup():
    pub,priv = simulate(202611251700,0,0,0.,50,8)
    evaluate(pub,priv,0.,50,{"h0":"0"})

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase",choices=["development","confirmation"])
    phase = parser.parse_args().phase
    if phase == "development":
        counts = {"strong_early":6}
        seed = DEV_SEED
        thresholds = {"h0":"0"}
        identity = "design-dev-v1"
        workers = 4
    else:
        reg = read(TASK/"registration.json")
        for file, value in reg["inputs"].items():
            if digest(TASK.parent/file) != value:
                raise ValueError(f"Registration hash mismatch: {file}")
        import numpy,scipy
        if [sys.version,numpy.__version__,scipy.__version__] != reg["versions"]:
            raise ValueError("Registered runtime mismatch")
        counts,seed,thresholds,workers = (reg[k] for k in ("counts","seed","thresholds","workers"))
        identity = digest(TASK/"registration.json")
    outdir = TASK/"results"/phase
    outdir.mkdir(parents=True,exist_ok=True)
    jobs = [(group,i) for group,count in counts.items() for i in range(count)]
    with ProcessPoolExecutor(max_workers=workers,initializer=warmup) as pool:
        futures = [pool.submit(trial,g,i,seed,thresholds,phase,identity) for g,i in jobs]
        for f in as_completed(futures):
            f.result()
    print(phase,"completed",len(jobs),flush=True)

if __name__ == "__main__":
    main()
