# Stage 8: re-certify over retained attack parameters

This package develops a lower-cost follow-up to the Stage 7 fixed-amplitude recovery method. Once a valid directional certificate has retained onset-specific amplitude intervals, later certificates search only the intersection of those intervals with the current continuous likelihood confidence set.

The exact confidence threshold, reference mixture, likelihood, and branch-and-bound arithmetic are unchanged. The same time-uniform confidence event covers the true fixed onset and amplitude at every adaptive re-certification time. See [01_theory.md](01_theory.md) for the coverage proof and interval search rule.

On nine previously certified Stage 7 strong-attack queries, using only certificates from strictly earlier times, restricted and full searches returned the same successful decisions, correction vectors, and guaranteed gains. Continuous likelihood calls fell from 19,063 to 7,578, and low-support segments from 9,544 to 3,789. Mean query time fell from 53.26 to 25.27 seconds; median per-query speedup was 2.48x. These are deterministic re-runs of saved records, not new random performance samples.

Singleton amplitude intervals are checked explicitly: a low-support point that may remain in the confidence set returns unresolved, while a point whose support lower bound clears the target can be safely retained.

The witness scan is optional. Removing it changed no decision or correction in the tested records and saved only 18 likelihood calls across the nine queries. Most savings came from dropping previously excluded onset/amplitude branches.

Run `check_restricted.py` for the deterministic checks, `replay_stage7_queries.py` to reproduce the saved-query comparison, and `validate_stage8.py` for output and source-trace integrity checks. The Stage 7 manuscript and estimator were not modified.
