"""Freeze only after mathematical/deterministic preflight and before sampling."""
import json,hashlib,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
if (HERE/"freeze.json").exists() or (HERE/"results").exists():raise SystemExit("Already frozen")
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
cmd=["git","-c",f"safe.directory={REPO.as_posix()}"]
base=subprocess.check_output(cmd+["rev-parse","HEAD"],cwd=REPO,text=True).strip()
assert base.startswith("5738b644")
inputs=("model.json","pilot_protocol.json","pilot.py","vector_record.py","projection.py","exact_linear.py")
checks=("covariance_certificate.json","projection_checks.json","dynamics_checks.json","vector_record_checks.json")
for name in checks:assert json.loads((HERE/name).read_text(encoding="utf8"))["status"]=="PASS"
dependencies=(
    "reviews/paper2_stage4_certified_correction_20261122/interval_arithmetic.py",
    "reviews/paper2_stage4_certified_correction_20261122/certificate.py",
    "reviews/paper2_stage5_certification_acceleration_20261122/strong_concavity.py")
names=subprocess.check_output(cmd+["ls-files","-co","--exclude-standard","-z"],cwd=REPO).decode("utf8").split("\0")
scope=HERE.relative_to(REPO).as_posix()+"/"
protected={name:sha(REPO/name) for name in names if name and not name.startswith(scope) and (REPO/name).is_file()}
(HERE/"protected_before.json").write_text(json.dumps(protected,indent=2)+"\n",encoding="utf8",newline="\n")
record={"base_commit":base,"stage":"BEFORE_ANY_V2_PERFORMANCE_RANDOM_SAMPLES",
        "inputs":{name:sha(HERE/name) for name in inputs},
        "dependency_hashes":{name:sha(REPO/name) for name in dependencies},
        "preflight":{name:sha(HERE/name) for name in checks},
        "random_samples_generated":False,"screen_does_not_tune_final":True}
(HERE/"freeze.json").write_text(json.dumps(record,indent=2)+"\n",encoding="utf8",newline="\n")
print(json.dumps(record,indent=2))
