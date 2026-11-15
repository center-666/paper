"""Read-only collision scan for the frozen 400 E2 seeds."""
from __future__ import annotations
import argparse
import io
import json
import re
import subprocess
from pathlib import Path
import zipfile
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
NORMAL = list(range(141420000, 141420200))
ATTACK = list(range(141430000, 141430200))
E2_SEEDS = set(NORMAL + ATTACK)
PATTERN = re.compile(r"(?<!\d)(141420\d{3}|141430\d{3})(?!\d)")
SKIP_PARTS = {".git", ".venv", "__pycache__"}
MAX_MEMBER_BYTES = 100_000_000
SEED_DECLARATIONS = {
    "reviews/g1r_risk_constrained_recovery/code/audit_v2_seed_collisions.py",
    "reviews/g1r_risk_constrained_recovery/sources/task5_completion_20261114/pre_completion_source/audit_v2_seed_collisions.py",
}

def _record(hits, seed, where, source_type):
    item = hits.setdefault(seed, {"historical_text": [], "archive_members": [],
                                  "numeric_arrays": [], "filenames": []})
    item[source_type].append(where)

def _scan_np_array(array, location, hits):
    a = np.asarray(array)
    if a.dtype.kind in "iu":
        values = set(map(int, np.unique(a))) & E2_SEEDS
    elif a.dtype.kind == "f":
        finite = a[np.isfinite(a)]
        rounded = np.rint(finite) if finite.size else finite
        values = set(map(int, rounded[np.abs(finite-rounded) <= 1e-9])) & E2_SEEDS
    else:
        values = set()
    for seed in values:
        _record(hits, seed, location, "numeric_arrays")

def inspect(root: Path):
    expr = PATTERN.pattern
    args = ["rg", "-l", "--hidden", "--no-ignore", "--no-messages", "--text",
            "--pcre2", "--glob", "!.git/**", "--glob", "!.venv/**",
            "--glob", "!reviews/g1r_risk_constrained_recovery/protocol_v2.json",
            "--glob", "!reviews/g1r_risk_constrained_recovery/10_protocol_v2.md",
            "--glob", "!reviews/g1r_risk_constrained_recovery/code/audit_e2_seed_collisions.py",
            "--glob", "!reviews/g1r_risk_constrained_recovery/code/audit_v2_seed_collisions.py",
            "--glob", "!reviews/g1r_risk_constrained_recovery/sources/task5_completion_20261114/pre_completion_source/audit_v2_seed_collisions.py",
            "--glob", "!reviews/g1r_risk_constrained_recovery/results/g1r_e2_seed_audit_20261115_*/**",
            "--glob", "!reviews/g1r_risk_constrained_recovery/results/g1r_pre_e2_readonly_audit_20261115_r*/**",
            "-e", expr, "."]
    proc = subprocess.run(args, cwd=root, capture_output=True, text=True,
                          timeout=180, check=False)
    if proc.returncode not in (0, 1):
        raise RuntimeError(proc.stderr)
    candidates = [Path(x) for x in proc.stdout.splitlines() if x]
    hits, text_errors = {}, []
    for rel in candidates:
        try:
            txt = (root/rel).read_bytes().decode("utf-8", "ignore")
            for raw in set(PATTERN.findall(txt)):
                seed = int(raw)
                if seed in E2_SEEDS:
                    _record(hits, seed, str(rel).replace("\\", "/"), "historical_text")
        except OSError as exc:
            text_errors.append({"path": str(rel), "error": str(exc)})

    listing = subprocess.run(["rg", "--files", "--hidden", "--no-ignore",
                              "--glob", "!.git/**", "--glob", "!.venv/**", "."],
                             cwd=root, capture_output=True, text=True,
                             timeout=180, check=True).stdout.splitlines()
    arrays = [root/str(rel).replace("\\", "/").removeprefix("./") for rel in listing
              if rel.lower().endswith((".npz", ".npy"))]
    array_count, array_errors = 0, []
    for path in arrays:
        rel = path.relative_to(root).as_posix()
        try:
            loaded = np.load(path, allow_pickle=False)
            if isinstance(loaded, np.lib.npyio.NpzFile):
                with loaded as archive:
                    for key in archive.files:
                        try:
                            _scan_np_array(archive[key], f"{rel}::{key}", hits)
                        except (ValueError, OSError) as exc:
                            array_errors.append({"path": f"{rel}::{key}", "error": str(exc)})
            else:
                _scan_np_array(loaded, rel, hits)
            array_count += 1
        except (ValueError, OSError, EOFError) as exc:
            array_errors.append({"path": rel, "error": str(exc)})

    archives, zip_errors = [], []
    for path in root.rglob("*.zip"):
        if SKIP_PARTS.intersection(path.parts):
            continue
        rel = path.relative_to(root).as_posix()
        try:
            with zipfile.ZipFile(path) as archive:
                skipped = []
                for info in archive.infolist():
                    if info.is_dir():
                        continue
                    filename_matches = {int(s) for s in PATTERN.findall(info.filename)}
                    for seed in filename_matches & E2_SEEDS:
                        _record(hits, seed, f"{rel}!/{info.filename}", "filenames")
                    if info.file_size > MAX_MEMBER_BYTES:
                        skipped.append({"member": info.filename, "reason": "over_100MB",
                                        "bytes": info.file_size})
                        continue
                    try:
                        raw = archive.read(info)
                    except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
                        skipped.append({"member": info.filename, "reason": str(exc)})
                        continue
                    txt = raw.decode("utf-8", "ignore")
                    for seed in {int(s) for s in PATTERN.findall(txt)} & E2_SEEDS:
                        _record(hits, seed, f"{rel}!/{info.filename}", "archive_members")
                    if info.filename.lower().endswith((".npz", ".npy")):
                        try:
                            arr = np.load(io.BytesIO(raw), allow_pickle=False)
                            if isinstance(arr, np.lib.npyio.NpzFile):
                                with arr as nested:
                                    for key in nested.files:
                                        _scan_np_array(nested[key], f"{rel}!/{info.filename}::{key}", hits)
                            else:
                                _scan_np_array(arr, f"{rel}!/{info.filename}", hits)
                        except (ValueError, OSError, EOFError) as exc:
                            skipped.append({"member": info.filename,
                                            "reason": f"numeric_parse:{exc}"})
                archives.append({"path": rel, "member_count": len(archive.infolist()),
                                 "skipped_members": skipped})
        except (OSError, zipfile.BadZipFile) as exc:
            zip_errors.append({"path": rel, "error": str(exc)})

    seeds = []
    for seed in sorted(E2_SEEDS):
        match = hits.get(seed, {"historical_text": [], "archive_members": [],
                                "numeric_arrays": [], "filenames": []})
        count = sum(len(v) for v in match.values())
        seeds.append({"seed": seed, "group": "normal" if seed in NORMAL else "attack",
                      "status": "NO_COLLISION_IN_SCANNED_SCOPE" if count == 0 else "COLLISION",
                      "matches": match})
    return {"normal_range": [NORMAL[0], NORMAL[-1]],
            "attack_range": [ATTACK[0], ATTACK[-1]], "per_seed": seeds,
            "collision_count": sum(x["status"] == "COLLISION" for x in seeds),
            "workspace_file_count": len(listing), "text_candidate_count": len(candidates),
            "npz_npy_count": len(arrays), "npz_npy_scanned": array_count,
            "text_errors": text_errors, "numeric_array_errors": array_errors,
            "zip_archives": archives, "zip_errors": zip_errors,
            "excluded_plan_declarations": ["protocol_v2.json", "10_protocol_v2.md"],
            "excluded_seed_audit_utility_declarations": sorted(SEED_DECLARATIONS),
            "scope_note": "Tracked/untracked and ignored workspace files, integer/float NPZ/NPY arrays and readable ZIP contents; external drives/backups are outside scope."}

def main(out: Path):
    if out.exists():
        raise FileExistsError(f"Preserve prior E2 seed scan: {out}")
    result = inspect(ROOT)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n",
                   encoding="utf-8", newline="\n")
    print(json.dumps({"seeds": len(result["per_seed"]),
                      "collisions": result["collision_count"],
                      "workspace_files": result["workspace_file_count"],
                      "npz_npy": [result["npz_npy_scanned"], result["npz_npy_count"]],
                      "archives": len(result["zip_archives"]),
                      "errors": [len(result["text_errors"]), len(result["numeric_array_errors"]), len(result["zip_errors"])]},
                     ensure_ascii=False, indent=2))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    main(args.out if args.out.is_absolute() else ROOT/args.out)
