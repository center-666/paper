"""Verify all baseline files and package SHA256 without executing old programs."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[2]
BASE = "320744ea77e3f8637980d083e3365d255ac3bb79"
PREFIX = ROOT.relative_to(REPO).as_posix()
TASK_SOURCE = Path("C:/Users/zhongxin/.codex/attachments/21a5cc3f-15af-4d8d-b2db-be8b72a482ed/Pasted text.txt")


def git(*args):
    return subprocess.check_output(["git", "-C", str(REPO), *args])


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def packed(obj):
    return (json.dumps(obj, ensure_ascii=False, indent=2)+"\n").encode()


def baseline():
    changes = git("diff", "--name-only", BASE, "--", ".", f":(exclude){PREFIX}/**").strip()
    assert not changes, changes
    entries = []
    for item in git("ls-tree", "-r", "-z", BASE).split(b"\0"):
        if not item:
            continue
        info, name = item.split(b"\t", 1)
        mode, kind, oid = info.decode().split()
        assert kind == "blob", (kind, name)
        entries.append((mode, kind, oid, name.decode("utf-8")))
    process = subprocess.run(
        ["git", "-C", str(REPO), "cat-file", "--batch"],
        input=("".join(oid+"\n" for _, _, oid, _ in entries)).encode(),
        stdout=subprocess.PIPE, check=True)
    stream = memoryview(process.stdout)
    offset = 0
    records = []
    for mode, kind, oid, path in entries:
        end = process.stdout.index(b"\n", offset)
        header = process.stdout[offset:end].decode().split()
        assert header[:2] == [oid, kind]
        size = int(header[2])
        offset = end+1
        raw = bytes(stream[offset:offset+size])
        assert len(raw) == size and stream[offset+size] == 10
        offset += size+1
        # core.autocrlf may render different working-tree newlines; the
        # attribute-normalized git diff above checks content while this records
        # the exact baseline blob.
        records.append(dict(path=path, mode=mode, git_blob=oid, bytes=len(raw), sha256=sha(raw)))
    assert offset == len(process.stdout)
    return dict(baseline_commit=BASE, files=records, count=len(records))


def package():
    return {p.relative_to(ROOT).as_posix(): dict(bytes=p.stat().st_size, sha256=sha(p.read_bytes()))
            for p in sorted(ROOT.rglob("*")) if p.is_file() and p.name != "integrity_manifest.json"}


def task_source():
    raw = TASK_SOURCE.read_bytes()
    return dict(task_id="ACK-V1-P5.3", source_attachment=str(TASK_SOURCE),
                bytes=len(raw), sha256=sha(raw))


def report_links():
    count = 0
    for path in ROOT.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        assert "\ufffd" not in text
        for target in re.findall(r"\]\(([^)]+)\)", text):
            if target.startswith("http"):
                continue
            assert (path.parent/target.split("#")[0]).exists(), (path.name, target)
            count += 1
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seal", action="store_true")
    args = parser.parse_args()
    info = baseline()
    baseline_path = ROOT/"data"/"baseline_file_manifest.json.gz"
    task_manifest = ROOT/"data"/"task_source_manifest.json"
    if args.seal:
        baseline_path.write_bytes(gzip.compress(packed(info), mtime=0))
        task_manifest.write_bytes(packed(task_source()))
    else:
        assert json.loads(gzip.decompress(baseline_path.read_bytes())) == info
        assert json.loads(task_manifest.read_text(encoding="utf-8")) == task_source()
    count = report_links()
    manifest = ROOT/"integrity_manifest.json"
    if args.seal:
        manifest.write_bytes(packed(dict(baseline_commit=BASE, algorithm="SHA256",
            excludes=["integrity_manifest.json"], files=package())))
    else:
        assert json.loads(manifest.read_text(encoding="utf-8"))["files"] == package()
    print(json.dumps(dict(status="PASS", baseline_files_git_normalized_unchanged=info["count"],
        package_files=len(package()), report_links=count, baseline=BASE)))


if __name__ == "__main__":
    main()
