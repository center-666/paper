"""Replay each original isolated kernel from its exact SHA-256-registered source."""
from __future__ import annotations
import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import types

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
FILES = {1:"registration_v1.json",2:"registration_v2.json",3:"registration_v3.json",4:"registration.json"}
DIRS = {1:"data/quantization",2:"data_v2/drift",3:"data_v3/model_mismatch",4:"data_v4/model_mismatch"}
LAYOUT = json.loads((ROOT/"source_layout.json").read_bytes())


def source(version):
    reg = json.loads((ROOT/FILES[version]).read_bytes())
    layout = LAYOUT[str(version)]
    if layout["git_commit"] != reg["source_commit"]:
        raise ValueError("Unidentified source commit")
    path = ROOT.relative_to(REPO).as_posix()+"/run_exploration.py"
    blob = subprocess.check_output(["git","show",reg["source_commit"]+":"+path],cwd=REPO)
    lines = blob.splitlines(keepends=True)
    for lo,hi in layout["crlf_line_ranges_inclusive"]:
        for i in range(lo-1,hi):
            lines[i] = lines[i].removesuffix(b"\n")+b"\r\n"
    result=b"".join(lines)
    if hashlib.sha256(result).hexdigest()!=reg["implementation_sha256"]:
        raise ValueError("Simulation source SHA-256 mismatch")
    for file,expected in reg["source_hashes"].items():
        if hashlib.sha256((REPO/file).read_bytes().replace(b"\r\n",b"\n")).hexdigest()!=expected:
            raise ValueError(file)
    return result


def load_kernel(version):
    # A dedicated worker pool per version isolates the original module hooks.
    reg=json.loads((ROOT/FILES[version]).read_bytes())
    kernel=types.ModuleType("registered_simulator")
    kernel.__file__=str(ROOT/"run_exploration.py")
    exec(compile(source(version),kernel.__file__,"exec"),kernel.__dict__)
    if reg["runtime"] != {"python":sys.version, "numpy":kernel.np.__version__}:
        raise ValueError("Use the Python and NumPy versions in the registration")
    default_read=kernel.read
    def registered_read(path):
        if path==ROOT/"registration.json":
            return reg
        return default_read(path)
    kernel.read=registered_read
    global ENGINE
    ENGINE=kernel


def replay(path):
    row=json.loads(path.read_bytes())
    task={k:row[k] for k in ("experiment","scenario","bits","epsilon","group","index",
                              "bias_kind","bias","fraction","rho") if k in row}
    new=ENGINE.evaluate_task(task,row["registration_hash"])
    assert row["public_history_sha256"]==new["public_history_sha256"],path.name
    for method,metrics in row["metrics"].items():
        for key,old in metrics.items():
            now=new["metrics"][method][key]
            if now==old:
                continue
            if not isinstance(old,float) or not math.isclose(now,old,rel_tol=1e-12,abs_tol=1e-10):
                raise ArithmeticError((path.name,method,key,old,now))
    return {"id":path.name,"history_sha256":new["public_history_sha256"],"cpu_seconds":new["cpu_seconds"]}


def run(full=False,workers=4):
    samples={1:"12bit_strong_positive_00.json",2:"decay_05_strong_positive_00.json",
             3:"eps_m1.00pct_health_00.json",4:"eps_m5.00pct_health_00.json"}
    result={}
    for version in FILES:
        directory=ROOT/DIRS[version]
        paths=sorted(directory.glob("*.json")) if full else [directory/samples[version]]
        paths=[p for p in paths if not p.name.startswith("enhance_") and
               not (version==3 and p.name.startswith("eps_p5.00pct"))]
        with ProcessPoolExecutor(workers,initializer=load_kernel,initargs=(version,)) as pool:
            result[str(version)]=list(pool.map(replay,paths))
        print("verified version",version,len(paths),flush=True)
    label="all" if full else "samples"
    output = ROOT/"verification_runs"/f"replay_{label}.json" if full else ROOT/"replay_samples.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf8",newline="\n")


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--all",action="store_true")
    parser.add_argument("--workers",default=4,type=int)
    args=parser.parse_args()
    run(args.all,args.workers)
