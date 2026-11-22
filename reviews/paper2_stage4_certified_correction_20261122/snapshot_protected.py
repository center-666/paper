"""Record task-external byte hashes; only current research folder is writable."""
from pathlib import Path
import subprocess,json,hashlib
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
path=HERE/"protected_before.json"
if path.exists():
    raise SystemExit("Refusing to overwrite existing snapshot")
cmd=["git","-c",f"safe.directory={REPO.as_posix()}"]
base=subprocess.check_output(cmd+["rev-parse","HEAD"],cwd=REPO,text=True).strip()
assert base.startswith("e1c55269")
names=subprocess.check_output(cmd+["ls-files","-co","--exclude-standard","-z"],cwd=REPO).decode("utf8").split("\0")
scope=HERE.relative_to(REPO).as_posix()+"/"
hashes={name:hashlib.sha256((REPO/name).read_bytes()).hexdigest() for name in names
        if name and not name.startswith(scope) and (REPO/name).is_file()}
data={"base_commit":base,"scope":scope,"snapshot_phase":"after_new_task_only_files_created_before_final_validation",
      "files":hashes,"random_performance_samples_generated":False}
path.write_text(json.dumps(data,indent=2)+"\n",encoding="utf8",newline="\n")
print("PROTECTED",len(hashes),"task-external files")
