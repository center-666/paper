"""Audit Fast versus exact actions on frozen tracks with different bitwise hashes."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
STAGE = HERE.parents[1]
FAST = STAGE / "submission_evidence" / "fast"
AUDIT = FAST / "audit.json"
OUTPUT = HERE / "action_differences_41.json"

sys.path.insert(0, str(FAST))
spec = importlib.util.spec_from_file_location("fast_replay", FAST / "run.py")
if spec is None or spec.loader is None:
    raise RuntimeError("Could not load the frozen paired replay utility")
fast_replay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fast_replay)

audit = json.loads(AUDIT.read_text(encoding="utf8"))
unmatched = [row["id"] for row in audit["records"] if not row["hash_matches"][1]]
paths = {
    path.stem: path
    for folder in (STAGE / "results" / "confirmation",
                   STAGE / "supplement" / "results" / "transition")
    for path in folder.glob("*.json")
}
if len(unmatched) != 41 or any(identifier not in paths for identifier in unmatched):
    raise RuntimeError("Expected the 41 frozen tracks with non-identical M3 action hashes")

results = []
for index, identifier in enumerate(unmatched, start=1):
    result = fast_replay.timed(paths[identifier])
    results.append(result)
    payload = {
        "protocol": "deterministic exact-versus-binary64 replay of the 41 frozen non-bitwise-identical tracks",
        "completed": index,
        "total": len(unmatched),
        "records": results,
    }
    temporary = OUTPUT.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    temporary.replace(OUTPUT)
    print(f"{index}/{len(unmatched)} {identifier} max_abs={result['max_abs_action_difference']:.17g}", flush=True)

all_differences = [row["max_abs_action_difference"] for row in results]
summary = {
    "completed": len(results),
    "max_abs_action_difference": max(all_differences),
    "tracks_above_1e-10": sum(row["count_action_difference_gt_1e_10"] > 0 for row in results),
}
payload = {
    "protocol": "deterministic exact-versus-binary64 replay of the 41 frozen non-bitwise-identical tracks",
    "completed": len(results),
    "total": len(unmatched),
    "summary": summary,
    "records": results,
}
temporary = OUTPUT.with_suffix(".tmp")
temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
temporary.replace(OUTPUT)
print(json.dumps(summary, indent=2))
