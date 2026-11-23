"""Verify the historical theory baseline using raw Git objects."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BASE = "d92c39cb1152f335d5b347ca9a2cc8f11924a64e"


def main():
    manifest = json.loads((HERE / "baseline_manifest.json").read_text(encoding="utf8"))
    if manifest["base_commit"] != BASE:
        raise ValueError("Unexpected theory baseline")
    files = manifest["files"]
    requests = "".join(BASE + ":" + path + "\n" for path in files).encode("utf8")
    result = subprocess.run(["git", "cat-file", "--batch"], cwd=REPO,
                            input=requests, capture_output=True, check=True)
    stream = io.BytesIO(result.stdout)
    matching_worktree = 0
    for path, expected in files.items():
        header = stream.readline().decode("utf8").strip().split()
        if len(header) != 3 or header[1] != "blob":
            raise ValueError("Missing baseline blob for " + path)
        object_id, _, size = header
        data = stream.read(int(size))
        if stream.read(1) != b"\n":
            raise ValueError("Malformed Git object response")
        digest = hashlib.sha256(data).hexdigest()
        if (object_id != expected["git_blob"] or digest != expected["sha256"] or
                len(data) != expected["size_bytes"]):
            raise ValueError("Historical baseline differs for " + path)
        current_path = REPO / path
        if current_path.is_file() and hashlib.sha256(current_path.read_bytes()).hexdigest() == digest:
            matching_worktree += 1
    if stream.read():
        raise ValueError("Unexpected data after baseline objects")
    print(json.dumps({"historical_baseline": "PASS", "base_commit": BASE,
                      "verified_files": len(files), "matching_worktree_files": matching_worktree},
                     indent=2))


if __name__ == "__main__":
    main()
