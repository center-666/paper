"""Produce manuscript table values from both raw result files."""
import json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
timing = json.loads((HERE/"timing.json").read_text())["records"]
audit = json.loads((HERE/"audit.json").read_text())["records"]
assert len({r["id"] for r in audit}) == len(audit) == 116
assert len(timing) == 4
for method in ("M3-Exact", "M3-Fast"):
    samples = [r["methods"][method] for r in timing]
    times = np.array([s["wall"] for s in samples])
    queries = np.array([q for s in samples for q in s["query"]])
    assert len(queries) == 16
    print(method, "s/608 steps", times.mean(), "CPU s", np.mean([s["cpu"] for s in samples]),
          "query ms P50/P95", np.percentile(queries*1000, [50,95]))
print("Maximum coordinate difference on timed records, cm",
      max(r["max_abs_action_difference"] for r in timing))
for field in ("direction_mismatches", "decision_mismatches"):
    print(field, sum(len(r[field]) for r in audit), "/", 4*len(audit))
for field in ("useful_mismatches", "activity_mismatches", "hash_matches"):
    print(field, np.sum([r[field] for r in audit], axis=0))
for field in ("checked", "violations", "negative_gain_actions", "issued_queries"):
    print(field, sum(r[field] for r in audit))
for group in sorted({r["group"] for r in audit}):
    rows = np.array([r["useful"] for r in audit if r["group"]==group])
    print(group, len(rows), "M2/M3 useful steps", rows.mean(axis=0))
