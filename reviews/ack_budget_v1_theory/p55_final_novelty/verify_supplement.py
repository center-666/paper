"""Read-only integrity verification for the P5.5 full-text addendum."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
MANIFEST = HERE / "supplement_integrity.json"


def main() -> int:
    args = argparse.ArgumentParser()
    args.add_argument("--local-pdfs", action="store_true")
    local = args.parse_args().local_pdfs
    manifest = json.loads(MANIFEST.read_bytes())
    allowed = {entry["path"] for entry in manifest["files"]}
    allowed.add(MANIFEST.relative_to(ROOT).as_posix())
    problems = []
    for entry in manifest["files"]:
        path = ROOT / entry["path"]
        if not path.is_file():
            problems.append("missing: " + entry["path"])
            continue
        data = path.read_bytes()
        if len(data) != entry["bytes"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
            problems.append("changed: " + entry["path"])
    for line in subprocess.check_output(
        ["git", "diff", "--name-status", manifest["baseline_commit"], "--"],
        cwd=ROOT, text=True, encoding="utf-8"
    ).splitlines():
        kind, path = line.split("\t", 1)
        if kind != "A" or path not in allowed:
            problems.append("unexpected baseline difference: " + line)
    if local:
        sources = json.loads((HERE / "sources_fulltext_supplement.json").read_bytes())
        for entry in sources["sources"]:
            path = Path(entry["local_path"])
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
                problems.append("source unavailable or changed: " + entry["id"])
    if problems:
        print("\n".join(problems))
        return 1
    print(f"PASS: {len(manifest['files'])} addendum file hashes and protected Git baseline")
    if local:
        print("PASS: 3 local formal PDF hashes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
