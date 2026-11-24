# ERCR task breakdown after P0

## P1: segmented pollution response

Implement the one-switch response using the trusted event sequence and compare it against a direct candidate filter. Acceptance requires a per-time numerical tolerance and explicit tests for unchanged, increased, decreased, and sign-changing amplitudes.

## P2: trusted-history audit

Define the observation contract, event and payload likelihoods, a common reference process, and conservative continuous amplitude-box bounds. A finite amplitude grid may diagnose behavior but cannot be the formal result.

## P3: pollution set and robust recovery

Map surviving parameter boxes to pollution-set segments or polygons, compute a conservative damage bound, and use the weighted closest-point projection. Invalid or unresolved certificates must return no action.

## P4: same-information comparisons

Compare Monitor, rejection baselines, a point-estimate compensator, TRSR, and ERCR on the same trusted log. Oracle remains a separate upper-bound diagnostic.

## P5: independent experiments

Freeze seeds and protocol before confirmation runs. Report all trajectories, failures, no-action cases, false actions on healthy records, recovery delay, risk-bound slack, and query cost.

## P6: manuscript assembly

Write the paper around the narrow claim that can be supported by the completed theorem and experiments. The current evidence supports the pollution-response and conditional-risk foundation. It does not yet support a claim of online ERCR gain, continuous-parameter coverage, or finite-bit communication certification.

## Stop conditions

- If segmented response does not match direct filtering, stop before audit development.
- If only a finite amplitude grid can be implemented, restrict the result to exploratory evidence.
- If the certified pollution set generally contains the origin or the Oracle opportunity is too small, do not add more algorithmic modules without revisiting the research claim.
