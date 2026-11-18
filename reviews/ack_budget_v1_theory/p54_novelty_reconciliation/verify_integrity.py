"""Verify the P5.4 report package without reading external PDFs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
MANIFEST = HERE / "04_integrity_manifest.json"


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    failures: list[str] = []
    for entry in manifest["files"]:
        path = REPO_ROOT / entry["path"]
        if not path.is_file():
            failures.append(f"missing: {entry['path']}")
            continue
        data = path.read_bytes()
        actual = hashlib.sha256(data).hexdigest()
        if len(data) != entry["bytes"] or actual != entry["sha256"]:
            failures.append(
                f"changed: {entry['path']} bytes={len(data)} sha256={actual}"
            )
    if failures:
        print("P5.4 integrity FAILED")
        print("\n".join(failures))
        return 1
    print(f"P5.4 integrity PASS ({len(manifest['files'])} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
