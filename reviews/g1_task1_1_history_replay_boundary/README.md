# G1 Task 1.1 review package

Start with [the final decision](07_task1_1_final_decision.md).

This package contains seven research reports, a SHA256 manifest, deterministic
analysis scripts, derived tables, and byte-identical copies of two **existing**
historical files (clean estimates/events and nominal gains). It contains no new
simulation or Seed trajectories. The archived gains are read, never regenerated.

From the repository root with the existing NumPy-enabled environment:

~~~powershell
python -B reviews/g1_task1_1_history_replay_boundary/code/analyze_historical_candidate_sets.py --verify
python -B reviews/g1_task1_1_history_replay_boundary/code/static_formula_checks.py --verify
~~~

Both commands are read-only verification. Omitting --verify rewrites only their
derived outputs under this package's data/ directory. The candidate script also
checks the preceding Task 0.5 artifact hashes. Source provenance is recorded in
[01](01_scope_and_source_audit.md) and data/source_integrity.json.

The 1,543 packet candidates are **not independent samples**. Their one-step scores
are offline algebra on saved data, not online detector performance or generated
single-Replay counterfactual trajectories.

The manifest 08_manifest.sha256 covers every file in this package except itself.
All frozen Task 0/0.5/1 assets remain unchanged.
