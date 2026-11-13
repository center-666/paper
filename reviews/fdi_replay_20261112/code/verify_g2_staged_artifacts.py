"""Verify the G2 v3 artifacts as staged Git blobs, including line-ending policy."""
from __future__ import annotations
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "simulation/g2_runs/2026-11-13_g2_replay_effectiveness_v3"
REVIEW = ROOT / "reviews/fdi_replay_20261112"


def staged(path):
    return subprocess.check_output(["git", "show", f":{path}"], cwd=ROOT)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    completion = json.loads((RUN / "completion.json").read_text(encoding="utf-8"))
    for relative, expected in completion["output_hashes"].items():
        path = f"simulation/g2_runs/{RUN.name}/{relative}"
        staged_data = staged(path)
        actual = digest(staged_data)
        if actual != expected:
            worktree_data = (RUN / relative).read_bytes()
            detail = {"path": path, "expected": expected, "worktree_sha256": digest(worktree_data),
                      "staged_sha256": actual, "worktree_bytes": len(worktree_data),
                      "staged_bytes": len(staged_data), "worktree_crlf": worktree_data.count(b"\r\n"),
                      "staged_crlf": staged_data.count(b"\r\n"),
                      "worktree_bom": worktree_data.startswith(b"\xef\xbb\xbf"),
                      "staged_bom": staged_data.startswith(b"\xef\xbb\xbf")}
            raise AssertionError(json.dumps(detail))

    fingerprints = json.loads((REVIEW / "g2_source_fingerprints.json").read_text(encoding="utf-8"))
    for relative in ("reviews/fdi_replay_20261112/g2_screen_plan.json",
                     "simulation/g2_replay_runner.py",
                     "simulation/engine.py",
                     "reviews/fdi_replay_20261112/code/analyze_g2_final.py"):
        data = staged(relative)
        entry = fingerprints["runtime_sources"].get(relative)
        if entry is None:
            entry = fingerprints["runtime_sources"]["reviews/fdi_replay_20261112/code/analyze_g2_final.py"]
        normalized = data.replace(b"\r\n", b"\n")
        assert digest(normalized) == entry["sha256_crlf_to_lf"], f"Staged source mismatch: {relative}"
        if relative in {"reviews/fdi_replay_20261112/g2_screen_plan.json",
                        "simulation/g2_replay_runner.py",
                        "reviews/fdi_replay_20261112/code/analyze_g2_final.py"}:
            assert digest(data) == entry["sha256_worktree_bytes"], f"Staged byte hash mismatch: {relative}"
    print(json.dumps({"status": "PASS", "v3_output_hashes": len(completion["output_hashes"]),
                      "source_fingerprints": len(fingerprints["runtime_sources"])}))


if __name__ == "__main__":
    main()
