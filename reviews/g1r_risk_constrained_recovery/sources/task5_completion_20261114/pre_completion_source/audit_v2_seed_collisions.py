"""Read-only full workspace and ZIP-member scan for reserved v2 seeds."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import zipfile
from pathlib import Path


RANGES = [(141400000, 5), (141410000, 199), (141420000, 200),
          (141430000, 200), (141440000, 200), (141450000, 200),
          (141460000, 1)]
RESERVED = {s for start, count in RANGES for s in range(start, start + count)}
# Find the v2 seed namespace, then check exact interval membership below. This
# also catches ignored run trees with arbitrary CSV/JSON formatting.
PATTERN = re.compile(r"(?<!\d)1414\d{5}(?!\d)")
SKIP_PARTS = {".git", ".venv", "__pycache__"}
MAX_FILE_BYTES = 100_000_000


def inspect(root: Path):
    # ripgrep performs a much faster binary-safe file-level scan than loading
    # every generated CSV/NPZ into Python.  Exclude only this audit's known
    # reservation declarations and outputs; all old and untracked material is
    # part of the scan.
    expression = PATTERN.pattern
    command = ["rg", "-l", "--hidden", "--no-ignore", "--no-messages", "--text", "--pcre2",
               "--glob", "!.git/**", "--glob", "!.venv/**",
               "--glob", "!reviews/g1r_risk_constrained_recovery/protocol_v2.json",
               "--glob", "!reviews/g1r_risk_constrained_recovery/10_protocol_v2.md",
               "--glob", "!reviews/g1r_risk_constrained_recovery/code/audit_v2_seed_collisions.py",
               "--glob", "!reviews/g1r_risk_constrained_recovery/sources/task5_v2_20261114/**",
               "--glob", "!reviews/g1r_risk_constrained_recovery/sources/task5_v2_20261114_r*/**",
               "-e", expression, "."]
    process = subprocess.run(command, cwd=root, capture_output=True,
                             text=True, timeout=180, check=False)
    if process.returncode not in (0, 1):
        raise RuntimeError(f"ripgrep failed: {process.stderr.strip()}")
    candidates = [Path(line) for line in process.stdout.splitlines() if line]
    hits = []
    unreadable = []
    for path in candidates:
        try:
            text = path.read_bytes().decode("utf-8", "ignore")
            found = sorted({int(value) for value in PATTERN.findall(text)
                            if int(value) in RESERVED})
            if found:
                hits.append({"file": path.as_posix().replace("./", ""), "seeds": found})
        except OSError as exc:
            unreadable.append({"file": path.as_posix().replace("./", ""), "error": str(exc)})
    all_files = subprocess.run(["rg", "--files", "--hidden", "--no-ignore", "--glob", "!.git/**",
                                "--glob", "!.venv/**", "."], cwd=root,
                               capture_output=True, text=True, timeout=180,
                               check=True).stdout.splitlines()
    large = []
    for name in all_files:
        path = root / name.lstrip("./")
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                large.append({"file": name.replace("./", ""), "bytes": path.stat().st_size})
        except OSError:
            pass

    archives = []
    for path in root.rglob("*.zip"):
        if SKIP_PARTS.intersection(path.parts):
            continue
        try:
            with zipfile.ZipFile(path) as archive:
                members, archive_hits, skipped = len(archive.infolist()), [], []
                for info in archive.infolist():
                    if info.is_dir():
                        continue
                    if info.file_size > MAX_FILE_BYTES:
                        skipped.append({"member": info.filename, "bytes": info.file_size})
                        continue
                    try:
                        text = archive.read(info).decode("utf-8", "ignore")
                    except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
                        skipped.append({"member": info.filename, "error": str(exc)})
                        continue
                    found = sorted({int(value) for value in PATTERN.findall(text)
                                    if int(value) in RESERVED})
                    if found:
                        archive_hits.append({"member": info.filename, "seeds": found})
                archives.append({"file": path.relative_to(root).as_posix(),
                                 "member_count": members, "hits": archive_hits,
                                 "skipped_members": skipped})
        except (OSError, zipfile.BadZipFile) as exc:
            archives.append({"file": path.relative_to(root).as_posix(), "error": str(exc)})

    return {"reserved_seed_count": len(RESERVED), "scanned_workspace_files": len(all_files),
            "text_file_collisions": hits, "oversize_files_unscanned": large,
            "unreadable_files": unreadable, "zip_archives": archives,
            "scope_note": "Scans current workspace and ZIP members; cannot inspect external drives, backup media, or unreadable encrypted/compressed members."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    # Refuse overwrites, including a partial/failure output. Compute first so
    # a scan failure never leaves a misleading empty artifact.
    result = inspect(args.root.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    main()
