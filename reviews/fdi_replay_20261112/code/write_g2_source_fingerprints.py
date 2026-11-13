"""Verify run-time source bytes and record CRLF-normalized checkout hashes."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "simulation/g2_runs/2026-11-13_g2_replay_effectiveness_v3"
REVIEW = ROOT / "reviews/fdi_replay_20261112"
OUT = REVIEW / "g2_source_fingerprints.json"


def hashes(path):
    raw = Path(path).read_bytes()
    normalized = raw.replace(b"\r\n", b"\n")
    return {
        "sha256_worktree_bytes": hashlib.sha256(raw).hexdigest(),
        "sha256_crlf_to_lf": hashlib.sha256(normalized).hexdigest(),
    }


def main():
    run_sources = json.loads((RUN / "code_hashes.json").read_text(encoding="utf-8"))
    entries = {}
    for display, expected in run_sources.items():
        path = (REVIEW / display if display == "g2_screen_plan.json"
                else ROOT / "simulation" / display)
        actual = hashes(path)
        assert actual["sha256_worktree_bytes"] == expected, display
        entries[path.relative_to(ROOT).as_posix()] = {
            **actual, "run_recorded_sha256": expected}
    analysis = REVIEW / "code/analyze_g2_final.py"
    entries[analysis.relative_to(ROOT).as_posix()] = hashes(analysis)
    doc = {
        "run_id": RUN.name,
        "normalization": "The second hash replaces CRLF byte pairs with LF; it does not alter text content.",
        "runtime_sources": entries,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUT), "source_count": len(entries)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
