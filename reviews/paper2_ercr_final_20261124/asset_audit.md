# ERCR P0 asset audit

## Baseline and scope

The audit uses the repository baseline `1090bff83a76590e5bf7920dda414de5c66ff6cd` on branch `paper2-ercr-final-20261124`. The model is the V2 centralized remote estimator specified in `reviews/paper2_stage6_vector_correction_20261122/model.json`.

The frozen model has

\[
A=\begin{bmatrix}1.02&0.10\\0&0.97\end{bmatrix},\quad C=[1,0],\quad Q=0.05I_2,
\]

with \(R=0.20\), \(P_0=0.8I_2\), \(Z=2\), and \(W=I_2\). It is a centralized two-state, single-scalar-sensor model. It does not provide a distributed-estimation or multi-sensor-fusion result.

## 1. Model location

The authoritative model file is

`reviews/paper2_stage6_vector_correction_20261122/model.json`

The Stage 6 joint observation and pollution specification is in

`reviews/paper2_stage6_vector_correction_20261122/01_vector_kernel_and_pollution.md`

The Stage 9 protocol for the cumulative evidence experiments is in

`reviews/paper2_stage9_cumulative_evidence_20261123/stage9_protocol.json`

The TRSR/Oracle study keeps the same V2 receiver model in

`reviews/paper2_trsr_design_20261124/model.json`

## 2. Monitor, trigger, and attack injection

The Stage 9 production-style episode entry point is

`reviews/paper2_stage9_cumulative_evidence_20261123/paired_recovery.py`, function `run_episode`.

Within that function, the relevant order is:

1. generate the physical error and scalar measurement;
2. generate the trusted center and trigger event;
3. modify a sent payload when the attack is active;
4. update the Monitor with the sent payload or the trusted center on silence;
5. record the trusted event history and feed the recovery logic.

The current fixed-amplitude injection is implemented as

```python
injection = float(b) if sent and t >= t0 else 0.
residual = y + injection if sent else r
```

This is sufficient as a source for a finite-window response audit. It is not yet a one-switch online ERCR implementation.

The compact Stage 6 reference path is in

`reviews/paper2_stage6_vector_correction_20261122/pilot_v2.py`.

It records the event, center residual, payload, gain, and response update used by the Stage 6 certificates.

## 3. Stage 6 pollution response

The implementation is in

`reviews/paper2_stage6_vector_correction_20261122/vector_record.py`.

The mathematical source is

`reviews/paper2_stage6_vector_correction_20261122/01_vector_kernel_and_pollution.md`.

For a fixed trusted event history, the existing response bank has the form

\[
H_t(k)=F_tH_{t-1}(k)+\gamma_tK_{1,t}{\bf1}_{\{t\ge k\}}.
\]

For a constant finite-window amplitude,

\[
d_t=b\bigl[H_t(k_0)-H_t(k_1)\bigr].
\]

For the proposed one-switch attack, the corresponding algebraic extension is

\[
d_t=b_1[H_t(k_0)-H_t(\tau)] + b_2[H_t(\tau)-H_t(k_1)].
\]

The extension still requires a new implementation and a direct-filter equivalence test. It cannot be obtained by changing two scalar parameters in the existing constant-amplitude code without checking the event-conditioned likelihood and the attack timing.

## 4. Reusable receiver functions

The reusable interfaces are in `reviews/paper2_trsr_design_20261124/code/receiver.py`.

| Function | Reuse assessment |
|---|---|
| `V2Filter.initial` | Directly reusable for the frozen V2 state and covariance initialization. |
| `V2Filter.predict` | Directly reusable for Monitor and candidate replay. |
| `V2Filter.update` | Reusable after an independent check that its silent-center convention matches the ERCR log contract. |
| `V2Filter.response` | Reusable as the one-step building block for a segmented response bank. |
| `V2Filter.replay` | Useful as a comparison or offline candidate evaluator. It is not an ERCR audit implementation. |
| `decide` | Reference recovery decision only. ERCR needs a pollution-set projector and cannot treat this Oracle/TRSR decision as its online method. |

The Oracle runner is `reviews/paper2_trsr_design_20261124/code/run_oracle_pilot.py`. It uses true attack-window information for offline scoring and therefore cannot be called by the online ERCR interface.

## 5. Results and proofs that transfer

The following results can support the ERCR derivation after their assumptions are restated.

### Transferable foundations

- The scalar observation kernel and the silent-event equivalent update in Stage 6.
- The linear pollution-response identity for a fixed trusted event sequence.
- The exact conditional weighted-risk decomposition and the convex projection result in `03_projection_and_directional_certificate.md`.
- The Stage 9 source-binding, causal-history, and cumulative-envelope design as an audit discipline.
- The Stage 9 incremental likelihood implementation as an engineering starting point for fixed-amplitude candidates.

### Results requiring a new proof

- The one-switch pollution identity as an implemented, event-conditioned candidate model.
- Joint likelihood and time-consistent coverage for \((k_0,\tau,k_1,b_1,b_2)\) with continuous amplitude boxes.
- Mapping a continuous two-amplitude confidence box to a conservative two-dimensional pollution set.
- The stopping rule based only on the trusted history rather than the true stop time.
- Any claim of long-horizon online complexity or continuous-parameter coverage.

The convex projection theorem itself is standard and should not be presented as the sole novelty. The research content must be the construction of the trusted-history pollution set and the conditions under which the projection is safe.

## 6. Oracle data boundary

The Oracle archive is

`reviews/paper2_trsr_design_20261124/results/oracle_v1/episodes.csv.gz`

with protocol and provenance in

`reviews/paper2_trsr_design_20261124/results/oracle_v1/manifest.json`.

It contains 1,600 paired independent episodes, 3,200 attack or sham trajectories, and 48,000 window rows. The Oracle runner receives the true attack window and amplitude for offline potential scoring. The archive can be re-evaluated without leaking truth into an online algorithm only if the re-evaluation is an analysis process that masks `b`, `start`, and `stop` from the ERCR input interface.

Permitted uses are

- direct pollution-response equivalence checks;
- an Oracle potential or recovery-opportunity diagnostic;
- fixed-log comparisons where the candidate method sees only the trusted record;
- reproducibility and runtime audits.

It cannot support a claim that ERCR has an online detection rate, a confidence-set coverage rate, or a deployed recovery gain. The current Oracle report explicitly records that boundary. The existing untracked `oracle_archive` objects remain outside this P0 submission.

## 7. One internal amplitude switch complexity

For total length \(T=652\) and maximum attack duration \(D_{\max}=60\), the number of discrete templates is

\[
N_0=\sum_{D=1}^{60}(T-D+1)=37{,}350
\]

for a constant-amplitude window, and

\[
N_1=\sum_{D=1}^{60}(T-D+1)(D-1)=1{,}083{,}830
\]

for one internal switch. Two internal switches already give 20,780,095 templates. These figures exclude continuous amplitude values and likelihood subdivision.

If each one-switch template is updated for all 652 samples, the minimum direct template-time workload is

\[
1{,}083{,}830\times652=706{,}657{,}160
\]

template updates. A 21 by 21 amplitude grid would create about 477,969,030 template-grid combinations. Storing one binary64 log-likelihood per grid combination requires about 3.56 GiB before candidate states, interval endpoints, and history caches are included.

The direct enumeration is therefore unsuitable as the primary online algorithm. The next implementation must share response prefixes, retain amplitude boxes, prune by certified likelihood bounds, or use a dynamic-programming representation. A finite grid can be used for exploratory diagnostics only and cannot be reported as continuous-amplitude coverage.

## P0 decision

The repository contains a credible theory base for an ERCR paper, especially the link

\[
\text{trusted history}\;\longrightarrow\;\text{pollution set}\;\longrightarrow\;\text{worst-case risk certificate}.
\]

It does not yet contain an online ERCR implementation or an ERCR experiment. The most defensible manuscript at the current state would center the existing Stage 6 pollution-and-projection theorem and present Stage 9 as the evidence-audit foundation, while labeling the Oracle result as potential analysis. A submission claiming an online ERCR performance improvement would be premature until P1--P5 are completed.
