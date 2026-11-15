"""High-precision deterministic cross-check of the frozen v2 risk cap.

Uses Decimal arithmetic and independently generated Gauss-Legendre rules.
This is a high-precision numerical check, not directed-rounding interval proof.
No RNG or trajectories are used.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "reviews/g1r_risk_constrained_recovery"
D = Decimal


def pi_decimal():
    """Machin formula with alternating arctangent series."""
    def atan_inv(n):
        inv = D(1) / D(n)
        inv2 = inv * inv
        term = inv
        total = term
        k = 1
        while True:
            term *= -inv2
            add = term / D(2*k + 1)
            total += add
            if abs(add) < D(10) ** -75:
                # Alternating-series remainder is no larger than next term.
                return total, abs(add)
            k += 1
    a, ea = atan_inv(5)
    b, eb = atan_inv(239)
    return D(16)*a - D(4)*b, D(16)*ea + D(4)*eb


def legendre_rule(n, pi):
    """Gauss-Legendre nodes/weights on [-1,1], Newton in Decimal."""
    roots, weights = [], []
    half = (n + 1) // 2
    for i in range(1, half + 1):
        # Double cosine is only an initial guess; Newton refinement is Decimal.
        import math
        x = D(str(math.cos(math.pi * (i - .25) / (n + .5))))
        for _ in range(80):
            p0, p1 = D(1), x
            if n == 0:
                pn, pnm1 = p0, D(0)
            elif n == 1:
                pn, pnm1 = p1, p0
            else:
                for k in range(2, n + 1):
                    pk = (D(2*k-1)*x*p1 - D(k-1)*p0) / D(k)
                    p0, p1 = p1, pk
                pn, pnm1 = p1, p0
            deriv = D(n) * (x*pn - pnm1) / (x*x-D(1))
            dx = pn / deriv
            x -= dx
            if abs(dx) < D(10) ** -72:
                break
        else:
            raise ArithmeticError(f"Legendre root {i}/{n} failed")
        p0, p1 = D(1), x
        if n == 1:
            pn, pnm1 = p1, p0
        else:
            for k in range(2, n + 1):
                pk = (D(2*k-1)*x*p1 - D(k-1)*p0) / D(k)
                p0, p1 = p1, pk
            pn, pnm1 = p1, p0
        deriv = D(n) * (x*pn-pnm1)/(x*x-D(1))
        weight = D(2) / ((D(1)-x*x) * deriv*deriv)
        roots.append(x)
        weights.append(weight)
        if n % 2 == 0 or i <= n // 2:
            roots.append(-x)
            weights.append(weight)
    paired = sorted(zip(roots, weights), key=lambda z: z[0])
    assert len(paired) == n
    return [x for x, _ in paired], [w for _, w in paired]


def sin_cos(x, pi):
    """Taylor sin/cos; inputs lie in [0,pi/2]."""
    x2 = x*x
    st, ct = x, D(1)
    s, c = st, ct
    n = 1
    while max(abs(st), abs(ct)) > D(10) ** -72:
        st *= -x2 / D((2*n)*(2*n+1))
        ct *= -x2 / D((2*n-1)*(2*n))
        s += st
        c += ct
        n += 1
        if n > 200:
            raise ArithmeticError("Taylor series failed to converge")
    return s, c


def erfc_decimal(x, pi):
    """Power-series erf, adequate here with 75-digit cancellation margin."""
    if x < 0:
        return D(2) - erfc_decimal(-x, pi)
    term = x
    total = term
    n = 0
    x2 = x*x
    while True:
        n += 1
        term *= -x2 * D(2*n-1) / D(n*(2*n+1))
        total += term
        if abs(term) < D(10) ** -72:
            break
        if n > 500:
            raise ArithmeticError("erf series failed to converge")
    return D(1) - D(2)*total/pi.sqrt()


def calc_order(order, alpha, q, eig_low, eig_high, pi):
    roots, weights = legendre_rule(order, pi)
    acc = D(0)
    for x, w in zip(roots, weights):
        phi = (x + D(1))*pi/D(4)
        _, co = sin_cos(phi, pi)
        si, _ = sin_cos(phi, pi)
        v = eig_high*co*co + eig_low*si*si
        sv = v.sqrt()
        xx = q/(D(2).sqrt()*sv)
        # E[(sqrt(v) R - q)+] for Rayleigh R: sqrt(pi*v/2) erfc(q/sqrt(2v))
        g = (pi/D(2)).sqrt()*sv*erfc_decimal(xx, pi)
        acc += w*g
    tail_moment = alpha*q + acc/D(2)
    return tail_moment


def main(out: Path):
    with localcontext() as ctx:
        ctx.prec = 80
        task3 = json.loads((BASE/"results/g1r_task3_normalrisk_20261114_r01/summary.json").read_text(encoding="utf-8"))
        proto = json.loads((BASE/"protocol_v2.json").read_text(encoding="utf-8"))
        moments = json.loads((BASE/"results/g1r_task3_normalrisk_20261114_r01/normal_risk_moments.json").read_text(encoding="utf-8"))
        sig = moments.get("Sigma_m") or task3["Sigma_m"]
        a, b, c = D(str(sig[0][0])), D(str(sig[0][1])), D(str(sig[1][1]))
        tr = a+c
        disc = ((a-c)*(a-c)+D(4)*b*b).sqrt()
        eig_high, eig_low = (tr+disc)/D(2), (tr-disc)/D(2)
        q = D(str(task3["tail_integration"]["quantile"]))
        alpha = D(str(proto["alpha"]))
        pi, pi_error = pi_decimal()
        estimates = {str(n): calc_order(n,alpha,q,eig_low,eig_high,pi) for n in (48,64,80)}
        cguard = D(str(proto["c_guard_engineering"]))
        U = D(str(proto["U_common"]))
        R = D(str(proto["normal_risk_budget_R"]))
        risk = alpha*U*U + D(2)*U*cguard
        for left,right in zip((48,64),(64,80)):
            if abs(estimates[str(left)]-estimates[str(right)]) > D("1e-25"):
                raise ArithmeticError(f"Gauss order convergence failed: {left}, {right}")
        if not (estimates["64"] < cguard and risk < R):
            raise ArithmeticError("High precision check does not support frozen guard/cap")
        record = {
            "scope":"Deterministic high precision risk integral cross-check; no trajectories/RNG",
            "decimal_precision_digits":ctx.prec,
            "pi_machin_series_remainder_bound":str(pi_error),
            "Sigma_m_source":"Task 3 archived normal moments; decimal serialization of stored binary64 values",
            "Sigma_m_eigenvalues_decimal": {"high":str(eig_high),"low":str(eig_low)},
            "q_reused_from_Task3_not_refit":str(q),
            "c_alpha_upper_identity":"alpha*q + E[(||m0||-q)_+]; valid for any fixed q>=0, no exact quantile assumption needed for upper bound",
            "gauss_legendre_decimal_estimates":{k:str(v) for k,v in estimates.items()},
            "orders_48_64_abs_difference":str(abs(estimates["48"]-estimates["64"])),
            "orders_64_80_abs_difference":str(abs(estimates["64"]-estimates["80"])),
            "c_guard":str(cguard),
            "guard_minus_64_order_estimate":str(cguard-estimates["64"]),
            "U_common":str(U),
            "risk_bound_using_c_guard":str(risk),
            "risk_budget_R":str(R),
            "remaining_risk_margin":str(R-risk),
            "status":"PASS_HIGH_PRECISION_NUMERICAL_CROSSCHECK_NOT_FORMAL_INTERVAL_PROOF",
            "quadrature_error_claim":"Convergence across independent Gauss orders is evidence only; no formal quadrature remainder enclosure is claimed",
            "new_trajectories":0,"seeds_used":[]}
        out.parent.mkdir(parents=True,exist_ok=True)
        with out.open("x",encoding="utf-8",newline="\n") as f:
            json.dump(record,f,ensure_ascii=False,indent=2)
            f.write("\n")
        print(json.dumps(record,ensure_ascii=False,indent=2))


if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    main(a.out if a.out.is_absolute() else ROOT/a.out)
