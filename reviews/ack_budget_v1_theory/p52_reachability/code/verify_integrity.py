"""Seal or check P5.2 artifacts, and verify frozen tracked assets against P5."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

PACKAGE = Path(__file__).resolve().parents[1]
REPO = PACKAGE.parents[2]
BASE = "80f235c9aed754deb47b53c4e010c2424279ea0d"
PREFIX = PACKAGE.relative_to(REPO).as_posix()
PROTECTED = [
    "reviews/ack_budget_v1_theory",
    "papers/paper2_ack_budget_deadline",
    "simulation/engine.py", "simulation/model.py", "simulation/config.json",
]


def git(*args):
    return subprocess.check_output(["git", "-C", str(REPO), *args])


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False)+"\n",
                    encoding="utf-8", newline="\n")


def frozen_assets():
    changes = git("diff", "--name-only", BASE, "--", ".",
                  f":(exclude){PREFIX}/**").decode("utf-8").strip()
    assert not changes, f"Changes outside authorized P5.2 directory: {changes}"
    records = []
    listing = git("ls-tree", "-r", "-z", BASE, "--", *PROTECTED)
    for entry in listing.split(b"\0"):
        if not entry:
            continue
        metadata, name = entry.split(b"\t", 1)
        mode, kind, oid = metadata.decode().split()
        assert kind == "blob"
        path = name.decode("utf-8")
        expected = git("cat-file", "blob", oid)
        actual = (REPO / path).read_bytes()
        assert actual == expected, path
        records.append(dict(path=path, baseline_git_blob=oid,
                            bytes=len(actual), sha256=sha(actual)))
    return dict(baseline=BASE, files=records, count=len(records),
                no_tracked_changes_outside_p52=True)


def package_files():
    return {p.relative_to(PACKAGE).as_posix(): dict(bytes=p.stat().st_size,
            sha256=sha(p.read_bytes()))
            for p in sorted(PACKAGE.rglob("*")) if p.is_file()
            and p.name != "integrity_manifest.json"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seal", action="store_true")
    args = parser.parse_args()
    protected = frozen_assets()
    protected_path = PACKAGE / "data" / "protected_assets.json"
    manifest_path = PACKAGE / "integrity_manifest.json"
    if args.seal:
        write_json(protected_path, protected)
        write_json(manifest_path, dict(baseline=BASE, algorithm="SHA256",
                                      excludes=["integrity_manifest.json"],
                                      files=package_files()))
    else:
        assert json.loads(protected_path.read_text(encoding="utf-8")) == protected
        assert json.loads(manifest_path.read_text(encoding="utf-8"))["files"] == package_files()
    print(json.dumps(dict(status="PASS", protected_files=protected["count"],
                          package_files=len(package_files()),
                          all_frozen_bytes_equal_baseline=True)))


if __name__ == "__main__":
    main()
