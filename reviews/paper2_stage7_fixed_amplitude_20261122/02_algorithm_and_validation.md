# Algorithm and deterministic validation

## Update after a successful certificate

For every onset (k\) still represented, the original vector record provides an outward interval for

\[
q_{k,\tau}=d_\tau^\top WH_{k,\tau}.
\]

At a positive certificate (z_\tau\), the algorithm removes (k\) if the interval upper endpoint is nonpositive. Otherwise it updates

\[
\underline b_k\leftarrow\max\left(\underline b_k,\operatorname{down}\left(z_\tau/q_{k,\tau}^+\right)\right),
\]

and removes (k\) if this exceeds (b_{\max}\). The lower endpoint is rounded down, so the true fixed amplitude is retained. Every successful certificate contributes, whether or not it replaces the legacy action.

At each subsequent trusted event, the unit responses and all active adjoint directions are updated. The support over a candidate interval is bounded below using (q_k^-\underline b_k) when (q_k^-\ge0), and (q_k^-b_{\max}) otherwise. The algorithm proposes the best certified action among retained directions and preserves the old action whenever interval uncertainty would produce a weaker lower guarantee.

## Deterministic test results

`check_fixed_amplitude.py` exhaustively enumerates all 64 length-6 event words and all six onset indices. It checks exact Fraction response propagation against directed Decimal response boxes; true amplitude retention; removal of nonpositive support onsets; support at interval endpoints; multiple-certificate intersection without reviving excluded onsets; future event propagation; and projection gain against the directional lower bound. It records 10,395 passing assertions and observes signed state components.

`check_direction_cache.py` checks the direct interval projection cache on 128 length-7 event words and 256 direction/onset updates. `check_direction_cache_fast.py` and its corrected key-synchronized version check a one-sided lower cache on the same 128 words and 1,280 support/action comparisons against exact rational responses. The corrected cache keys are checked after every event so the queried direction always matches its stored response coefficients.

All tests are deterministic and require no Monte Carlo assumptions. These tests validate the stated V2 model only; they do not establish finite-precision guarantees for a different implementation, model mismatch, hidden measurement centers, or a multidimensional sensor.

After the independent full-search run, `audit_fresh_response.py` regenerated those same frozen streams without running likelihood search. Across all 36 episodes it checked 18,432 stepwise enclosures of the exact rational true-onset response and all 37 successful certificate inequalities against the realized true parameter. Every response remained inside its outward interval and every successful certificate had nonnegative exact margin (minimum margin approximately 0.04615). This is a deterministic audit of the observed traces, not a statistical confidence-rate validation.

## Computation

The exact proof implementation maintains Fraction-valued responses. That version is useful as a deterministic oracle but is too slow for long traces. The replay implementation instead uses Stage 4 outward Decimal boxes for (H_{k,t}), while the Riccati covariance and gains remain exact fractions.

The direct support implementation recomputes each direction/onset inner product on every step. Its average strong-attack support-search time was 81.97 seconds per 562-step episode. The corrected cache propagates one lower projection value using the shared injection identity; it reduced mean support-search time to 5.33 seconds and mean replay time from 92.05 to 17.07 seconds. On all 36 frozen episodes, its MSE, action, conditional-risk, and guarantee outputs were exactly equal to the direct implementation in the stored float metrics (maximum absolute difference 0).

This removes the repeated projection bottleneck. It does not include likelihood-search time, and it does not remove the original record's cost of maintaining all onset likelihoods. A full independent confirmation must report the complete run cost.
