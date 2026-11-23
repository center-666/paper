# Re-certification inside the retained fixed-amplitude set

## Setup

Let the exact sequential confidence set at time (t) be

\[
C_t^\varepsilon=\{(k,b):p_{k,b,t}>\varepsilon q_t\},
\]

where the same predictable reference process (q_t) gives the full-time coverage guarantee

\[
\Pr_{k^\star,b^\star}\{(k^\star,b^\star)\in C_t^\varepsilon\text{ for every }t\}\ge1-\varepsilon.
\]

An earlier successful certificate at (	au) supplies an onset-indexed outer set

\[
S_\tau=\bigcup_k\{k\}\times[\underline b_{k,\tau},b_{\max}],
\]

derived from its directional inequality. On the same confidence event, the fixed true pair belongs to (S_\tau).

## Restricted certification rule

At a later time (t\ge\tau), the target certificate (d_t^\top W\theta_t\ge z_t>0) is valid if the likelihood search excludes every low-support pair in

\[
C_t^\varepsilon\cap S_\tau.
\]

For onset (k), write (a_{k,t}=d_t^\top WH_{k,t}). With an outward interval (a_{k,t}\in[a^-_{k,t},a^+_{k,t}]), amplitudes that might have low support are conservatively bounded by

\[
b\in[\underline b_{k,\tau},b_{k,\mathrm{hi}}],\qquad
b_{k,\mathrm{hi}}=\begin{cases}
\min\{b_{\max},z_t/a^-_{k,t}\},&a^-_{k,t}>0,\\
b_{\max},&a^-_{k,t}\le0.
\end{cases}
\]

The branch-and-bound calculation still uses the exact continuous likelihood over every retained onset and interval. If it proves that all candidates in (C_t^\varepsilon\cap S_\tau) have support at least (z_t), update

\[
S_{t}=S_\tau\cap\{(k,b):b a_{k,t}\ge z_t\}.
\]

If an outer amplitude interval collapses to one point, the implementation first checks its outward support lower bound. If that point can still have support below (z_t), it evaluates the point likelihood and leaves the query unresolved whenever the point may remain in the confidence set. It never discards a singleton merely because its interval width is zero.

Using outward interval endpoints can only enlarge the searched low-support region. Unresolved interval arithmetic, node limits, or an empty retained domain produce no new certificate.

## Why coverage is unchanged

On the single event where the true pair belongs to every (C_t^\varepsilon), induction gives

\[
(k^\star,b^\star)\in C_t^\varepsilon\cap S_{t-1}
\]

at every accepted re-certification. Since all low-support pairs in that intersection were excluded, the true pair satisfies the new directional inequality and remains in (S_t). The same initial confidence event supports every data-dependent re-certification time; no additional failure probabilities are spent.

The proof only covers the original model: fixed onset, fixed nonnegative amplitude, the specified send-time injection, and the same exact event/payload likelihood. A changing amplitude, shutdown, changed monitor, or a different sensor model requires a new outer-set propagation proof.

## The nonempty-witness check

The older implementation searched for one parameter satisfying (p_{k,b,t}>\varepsilon q_t) before it attempted to exclude low-support parameters. This is a useful diagnostic, but it is not required for coverage validity. On the confidence event, the true pair is already in (C_t^\varepsilon\cap S_\tau). Thus, if the low-support exclusion is valid and the intersection were empty, that can only occur off the confidence event already budgeted by (arepsilon). The restricted routine therefore makes the witness scan optional; by default it relies on the coverage argument and returns the same certificate condition.

This does not replace the confidence sequence or relax its threshold. It removes only a redundant search for a surviving point. The deterministic and frozen-record comparisons below verify that the optional check does not change decisions on the tested records.
