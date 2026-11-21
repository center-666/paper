"""Freeze the reviewed protocol before any stage-three performance draws."""
from pathlib import Path
import json
import subprocess
import sys
import numpy as np
import scipy
from run_experiment import HERE,sha,write

REPO=HERE.parents[1]
if (HERE/"freeze.json").exists() or (HERE/"results").exists():
    raise SystemExit("Already frozen or data exist; do not overwrite preregistration")
cmd=["git","-c",f"safe.directory={REPO.as_posix()}"]
base=subprocess.check_output(cmd+["rev-parse","HEAD"],cwd=REPO,text=True).strip()
if not base.startswith("8c02c07b"):
    raise SystemExit("Unexpected baseline")
inputs=("core.py","run_experiment.py","protocol.json","launch.py")
evidence=("joint_reference_checks.json","joint_kernel_checks.json")
for name in evidence:
    result=json.loads((HERE/name).read_text(encoding="utf8"))
    if result["status"]!="PASS":
        raise SystemExit("Preflight failed: "+name)
    if name=="joint_kernel_checks.json" and result["core_sha256"]!=sha(HERE/"core.py"):
        raise SystemExit("Validated core has changed")
paths=subprocess.check_output(cmd+["ls-files","-co","--exclude-standard","-z"],
                              cwd=REPO).decode("utf8").split("\0")
scope=HERE.relative_to(REPO).as_posix()+"/"
protected={p:sha(REPO/p) for p in paths if p and not p.startswith(scope) and (REPO/p).is_file()}
write(HERE/"protected_before.json",protected)
write(HERE/"freeze.json",{
    "base_commit":base,"stage":"BEFORE_ANY_STAGE3_PERFORMANCE_SAMPLE",
    "input_hashes":{name:sha(HERE/name) for name in inputs},
    "evidence_hashes":{name:sha(HERE/name) for name in evidence},
    "runtime":{"python":sys.version,"numpy":np.__version__,"scipy":scipy.__version__},
    "protected_file_count":len(protected),"random_performance_samples_generated":False,
    "screen_does_not_select_or_tune_confirmation":True})
print("FROZEN",len(inputs),"performance inputs;",len(protected),"protected files")
