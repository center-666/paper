# Fixed-amplitude outer-set theorem

## Model and certificate

Let (\theta_t\in\mathbb R^n) be the conditional estimation bias under one persistent attack. For a fixed onset (k) and constant amplitude (b\in[0,b_{\max}]), the unit-amplitude response is

\[
H_{k,t}=F_tH_{k,t-1}+\gamma_tK_{1,t},\qquad
F_t=(I-K_{\gamma_t,t}C)A,
\]

with (H_{k,t}=0) before onset and the send injection beginning at (k). Thus (\theta_t=bH_{k,t}).

At a successful, possibly data-dependent time (\tau), suppose the full-time parameter confidence sequence certifies

\[
d_\tau^\top W\theta_\tau\ge z_\tau>0,\qquad W\succ0.
\]

For each onset define (a_{k,\tau}=d_\tau^\top WH_{k,\tau}). Since (b\ge0), any parameter pair satisfying the certificate must obey

\[
a_{k,\tau}>0,\qquad b\ge z_\tau/a_{k,\tau}.
\]

An onset with (a_{k,\tau}\le0), or with (z_\tau/a_{k,\tau}>b_{\max}), is impossible under this certificate. For several successful certificates from the same confidence sequence, the exact retained interval is

\[
\underline b_{k,t}=\max_j\frac{z_{\tau_j}}{d_{\tau_j}^\top WH_{k,\tau_j}},\qquad
\mathcal K_t=\{k: a_{k,\tau_j}>0\ \forall j,\ \underline b_{k,t}\le b_{\max}\}.
\]

Each response (H_{k,t}) is propagated with the same trusted event history. The resulting pollution set is

\[
\Theta_t=\bigcup_{k\in\mathcal K_t}\{bH_{k,t}:b\in[\underline b_{k,t},b_{\max}]\}.
\]

## Coverage and adaptive certificate times

Assume a single confidence sequence has the uniform coverage event

\[
\Pr_{\vartheta^\star}\{\forall t,\ (k^\star,b^\star)\in C_t\}\ge1-\varepsilon.
\]

Every successful directional certificate is a valid restriction of (C_{\tau_j}). On this one event, the true pair satisfies every retained amplitude constraint. Because (k^\star,b^\star) are fixed and (H_{k,t}) follows the same response recursion, (\theta_t^\star=b^\star H_{k^\star,t}\in\Theta_t\) for every (t\ge\tau_1). The stopping times may be chosen from the observed history; no new failure budget is spent for each later certificate. This argument would fail for only fixed-time coverage, time-varying attack amplitudes, attack shutdown, negative amplitudes, or a changed injection model.

## Risk-improving correction

Let (K_t=\overline{\operatorname{conv}}(\Theta_t)) and let

\[
c_t^\star=\arg\min_{c\in K_t}c^\top Wc.
\]

The projection variational inequality gives (\theta^\top Wc_t^\star\ge\|c_t^\star\|_W^2) for every (\theta\in K_t\). For output (m_t^r=m_t^a-c_t^\star),

\[
R_t^a-R_t^r=2\theta_t^\top Wc_t^\star-\|c_t^\star\|_W^2
\ge\|c_t^\star\|_W^2
\]

on the same coverage event. A directional lower support (s_t(d)=\inf_{\theta\in\Theta_t}d^\top W\theta>0) yields the implementable action (c_t=s_t(d)d/(d^\top Wd)); inward scaling to meet an output cap preserves the lower bound (R_t^a-R_t^r\ge\|c_t\|_W^2).

The exact fixed-amplitude set is contained in the legacy set reachable from one half-space while allowing an independent (b_t\in[0,b_{\max}]) at every future send. Therefore its **unconstrained optimal convex-projection guarantee** cannot be lower. With an output cap, monotonicity is safest stated for the same-direction support action or the capped minimax objective; comparing only the squared norms of two differently directed capped actions is not a valid proof.

## Outward interval implementation

The computational version encloses (a_{k,\tau}\) in (q_k=[q_k^-,q_k^+]\). If (q_k^+\le0), the onset is excluded; otherwise it stores the outward-rounded lower bound (b_{k,\mathrm{lo}}\le z/q_k^+). This outer interval includes every true admissible amplitude. The interval image may contain extra, certificate-incompatible points, so every proposed correction uses a lower support bound over that entire outer image. If that bound is weaker than the legacy certificate because of interval width, the implementation keeps the legacy action. It does not claim exact set inclusion for the rounded box itself.

## Incremental projection identity

For a current direction (d_t), propagate the covector by

\[
d_{t+1}=W^{-1}F_{t+1}^{-\top}Wd_t.
\]

For each onset, (q_{k,t}=d_t^\top WH_{k,t}) satisfies

\[
q_{k,t+1}=q_{k,t}+\gamma_{t+1}d_{t+1}^\top WK_{1,t+1}.
\]

The second term is common to all onsets. The cached implementation stores only a one-sided Decimal lower bound for each (q_{k,t}) and adds an outward-rounded lower injection once per onset and active direction. This avoids repeating all vector inner products during support queries.
