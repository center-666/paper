# P0 repository audit and P1 theory unification

This directory records the P0 repository audit and the subsequent P1 theory unification for the second paper.

The audit is based on commit `1090bff83a76590e5bf7920dda414de5c66ff6cd` and branch `paper2-ercr-final-20261124`.

## Current research scope

- The frozen physical model is a centralized two-state estimator with one scalar sensor.
- The main attack is now fixed to an unknown onset and constant nonnegative bounded amplitude that persists after onset.
- The main contribution is vector pollution sets and conditional-risk-safe recovery under trusted histories.
- Stage 6 and Stage 9 assets remain read-only sources.
- The existing Oracle archive remains a separate finite-window potential diagnostic.

The original P0 audit analyzed the then-proposed one-switch ERCR attack. Its complexity counts are retained as an audit trail. The user subsequently replaced that attack scope with the fixed-amplitude Stage 6/9 model, so one-switch implementation is no longer a P1/P2 task.

## Deliverables

- [asset_audit.md](asset_audit.md) records code locations, transferable results, limitations, and the seven P0 questions.
- [source_manifest.json](source_manifest.json) records source hashes and file roles.
- [complexity_audit.json](complexity_audit.json) freezes the one-switch enumeration and memory estimates.
- [task_breakdown.md](task_breakdown.md) separates the next implementation stages from results that can already support a manuscript.
- [p1_theory_unification.md](p1_theory_unification.md) gives the unified model, lemmas, theorem proofs, implementation boundaries, and draft chapter organization.
- [p1_proof_audit.json](p1_proof_audit.json) records theorem-by-theorem validity and remaining claim limits.
- [p1_experiment_evidence.md](p1_experiment_evidence.md) classifies reusable historical experiments and identifies required new evidence.

P0 and P1 do not modify the Stage 6, Stage 9, or Oracle source files.
