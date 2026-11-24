# ERCR P0 asset audit

This directory records the read-only audit for the proposed Event-Record-Constrained Robust Recovery (ERCR) study.

The audit is based on commit `1090bff83a76590e5bf7920dda414de5c66ff6cd` and branch `paper2-ercr-final-20261124`.

## Scope

- The frozen physical model is a centralized two-state estimator with one scalar sensor.
- The proposed attack extension is one internal amplitude switch during a finite attack window.
- Stage 6 and Stage 9 assets are treated as read-only sources.
- The existing Oracle archive is an offline potential diagnostic. It is not an online ERCR result.

## Deliverables

- [asset_audit.md](asset_audit.md) records code locations, transferable results, limitations, and the seven P0 questions.
- [source_manifest.json](source_manifest.json) records source hashes and file roles.
- [complexity_audit.json](complexity_audit.json) freezes the one-switch enumeration and memory estimates.
- [task_breakdown.md](task_breakdown.md) separates the next implementation stages from results that can already support a manuscript.

P0 does not modify the Stage 6, Stage 9, or Oracle source files.
