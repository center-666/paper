"""Index immutable runs without editing them; failed runs are not deleted."""
from pathlib import Path
import hashlib
import json
import platform
import numpy as np
import scipy

BRANCH = Path(__file__).resolve().parents[1]
ROOT = BRANCH.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha_lf(path):
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def status(name):
    if name == "g1r_p0_verified_20261113_v1":
        return "FINAL_VALID", "Full-horizon/cache/response/permission audit; MSE exploratory only."
    if name == "g1r_p1_structure_20261113_v1":
        return "FINAL_VALID_STRUCTURE_ONLY", "Error/output equations verified; no designed Deghat tracker."
    if "format_repair" in name:
        return "FORMAT_ONLY", "New JSON/CSV copies; does not rehabilitate historical scientific claims."
    if "mapping_audit" in name:
        num = int(name.rsplit("_", 1)[1])
        return {
            1: ("INSUFFICIENT", "Circular arithmetic check, not independent full-horizon evidence."),
            2: ("INSUFFICIENT", "Circular arithmetic check, not independent full-horizon evidence."),
            3: ("INVALID_INDEPENDENCE", "Reference future sender difference fed back to recurrence."),
            4: ("PRE_REPLACEMENT_ONLY", "Independent range(R,q); no independent post-q verification."),
            5: ("FAILED_EXPORT", "Partial run; write_csv NameError, no complete audit claim."),
            6: ("SUPERSEDED_FORMAT_ERROR", "Full-horizon intermediate; per-seed JSON with CSV suffix."),
            7: ("SUPERSEDED", "Intermediate full-horizon result; final entry is 20261113_v1."),
            8: ("SUPERSEDED", "Intermediate full-horizon result; final entry is 20261113_v1."),
        }[num]
    if "output_channels" in name:
        num = int(name.rsplit("_", 1)[1])
        if num == 1:
            return "INVALID_COMPARISON", "Disagreement feature branch was not enabled."
        if num == 2:
            return "EXTRA_INFORMATION_CONTROL", "Augmented branch used unsent sender estimates; not a same-permission baseline."
        return "WITHDRAWN_MSE", "Legal cache input but response used S A.T instead of A S; do not cite correction MSE."
    if "p0_final_audit" in name:
        if name.endswith("_01"):
            return "FAILED_NO_RESULT", "Missing summary key; empty directory. Failure stage recorded from execution history, no saved traceback."
        return "PASS_WITHDRAWN", "Validator missed response-matrix multiplication error. Historical PASS is not current acceptance."
    if "attack_input_tracker" in name:
        return "LEGACY_LIMITED", "Batch/recursive GLS algebra only; not a faithful Deghat tracker or new mechanism."
    return "LEGACY_NOT_REENDORSED", "Preserved original screen; current claims must use final P0 evidence and stated scope."


def main():
    entries = []
    for folder in sorted((BRANCH / "results").iterdir()):
        if not folder.is_dir():
            continue
        label, reason = status(folder.name)
        files = [{"path": p.relative_to(BRANCH).as_posix(), "bytes": p.stat().st_size,
                  "sha256": sha(p), "sha256_lf": sha_lf(p) if p.suffix in {".csv", ".json"} else None}
                 for p in sorted(folder.rglob("*")) if p.is_file()]
        entries.append({"run_id": folder.name, "status": label, "reason": reason, "files": files})
    sources = []
    for suffix in ("pdf", "txt"):
        p = BRANCH / "sources" / ("deghat2019." + suffix)
        if p.exists():
            sources.append({"local_only": p.relative_to(BRANCH).as_posix(), "sha256": sha(p),
                            "DOI": "10.1016/j.automatica.2018.10.052",
                            "public_author_url": "https://arxiv.org/pdf/1810.04301"})
    source_paths=set()
    for run in ("g1r_p0_verified_20261113_v1", "g1r_p1_structure_20261113_v1"):
        source_paths.update(json.loads((BRANCH/"results"/run/"source_hashes.json").read_text(encoding="utf-8")))
    source_fingerprints={p:{"sha256":sha(ROOT/p),"sha256_lf":sha_lf(ROOT/p)} for p in sorted(source_paths)}
    doc = {"date": "2026-11-13", "baseline_commit": "db7dabd8cbb9b425482bc9693b065fd25865d720",
           "final_source_fingerprints":source_fingerprints,
           "runtime": {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__},
           "important": ["Historical PASS fields may be withdrawn; use status here and reports 07-10.",
                         "Same seeds across reruns are not additional independent trials.",
                         "Intermediate code was not snapshotted at every failure; raw results are audit records, not all reproducible from current code.",
                         "The empty failed audit_01 directory is recorded here because Git cannot store empty directories.",
                         "Ignored legacy NPZ files remain local; final fitted NPZ is explicitly included in the delivery.",
                         "sha256_lf only normalizes CRLF to LF for pre-existing text checkout compatibility; original byte hashes are retained.",
                         "No papers downloaded during this task."],
           "literature_source_fingerprints": sources, "runs": entries}
    (BRANCH / "run_status_index.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"runs_indexed": len(entries), "files_indexed": sum(len(e["files"]) for e in entries)}))


if __name__ == "__main__":
    main()
