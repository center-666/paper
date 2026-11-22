from pathlib import Path
import subprocess,json,hashlib
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
path=HERE/"protected_before.json"
if path.exists():raise SystemExit("Snapshot already exists")
cmd=["git","-c",f"safe.directory={REPO.as_posix()}"]
head=subprocess.check_output(cmd+["rev-parse","HEAD"],cwd=REPO,text=True).strip()
assert head.startswith("ccc18e09")
names=subprocess.check_output(cmd+["ls-files","-co","--exclude-standard","-z"],cwd=REPO).decode("utf8").split("\0")
scope=HERE.relative_to(REPO).as_posix()+"/"
files={name:hashlib.sha256((REPO/name).read_bytes()).hexdigest() for name in names
       if name and not name.startswith(scope) and (REPO/name).is_file()}
path.write_text(json.dumps({"base_commit":head,"files":files,
                "snapshot_phase":"after_stage5_only_files_created_before_final_validation"},indent=2)+"\n",
                encoding="utf8",newline="\n")
print("PROTECTED",len(files))
