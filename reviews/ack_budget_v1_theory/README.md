# ACK V1.0 P0–P4 theory audit

This package freezes the existing ACK manuscript model and independently checks
the first three integer-budget results. It does not modify the manuscript,
Yang-type estimator, simulation code, or historical results.

Run the exhaustive checker from the repository root:

```powershell
python -B reviews/ack_budget_v1_theory/ack_theory/theorem_checks.py
python -B reviews/ack_budget_v1_theory/ack_theory/test_boundaries.py -v
```

The checker uses separate implementations for the theoretical window criterion
and the brute-force blocking oracle. It is a finite validation of the proofs,
not a replacement for proof and not a Monte Carlo experiment.

T1–T3 proof drafts and finite checks are provided under these exact scopes:

- T1: fixed future opportunity set, persistent request, one attempt per slot;
- T2: deterministic causal policies and attempts counted before first success;
- T3: continuous suffix attempts after an initial wait, with `B < L`.

P0 full historical experiment-source provenance remains open; P1–P3 require
independent mathematical acceptance. P5 literature review, P6 estimator-interface
work, P7 experiments, and P8 submission review remain incomplete.
