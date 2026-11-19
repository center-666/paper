"""Deterministic scalar mutual-information proof audit; no random draws."""
from pathlib import Path
import json
import math

HERE = Path(__file__).resolve().parent
OUT = HERE / "results" / "g1_scalar.json"


def tail(x):
    return 0.5 * math.erfc(x / math.sqrt(2.0))


def h2(p):
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -p * math.log2(p) - (1 - p) * math.log2(1 - p)


def event_probs(sigma, tau, b):
    if sigma <= 0 or tau <= 0:
        raise ValueError("sigma and tau must be positive")
    if not (0 <= b < tau):
        raise ValueError("closed-form branch requires 0 <= b < tau")
    p_plus = 2 * tail((tau - b) / sigma)
    p_minus = 2 * tail((tau + b) / sigma)
    return p_plus, p_minus


def mutual_information(sigma, tau, b):
    p_plus, p_minus = event_probs(sigma, tau, b)
    p = 0.5 * (p_plus + p_minus)
    return h2(p) - 0.5 * (h2(p_plus) + h2(p_minus))


def main():
    sigma, tau, b = 1.0, 1.0, 0.3
    pp0, pm0 = event_probs(sigma, tau, 0.0)
    pp, pm = event_probs(sigma, tau, b)
    i0 = mutual_information(sigma, tau, 0.0)
    ib = mutual_information(sigma, tau, b)
    assert abs(pp0 - pm0) < 1e-15
    assert abs(i0) < 1e-14
    assert pp > pm and ib > 0
    assert abs(ib - 0.06953195327124773) < 1e-14
    result = {
        "model": "Z~N(0,sigma^2), S=1{Z>0}, Gamma_b=1{|Z+b|>tau}",
        "sigma": sigma,
        "tau": tau,
        "b": b,
        "p_plus_no_attack": pp0,
        "p_minus_no_attack": pm0,
        "p_plus_attack": pp,
        "p_minus_attack": pm,
        "I_S_Gamma_no_attack_bits": i0,
        "I_S_Gamma_attack_bits": ib,
        "incremental_sign_leakage_bits": ib - i0,
        "proof_scope": "private sign only; not amplitude or full-state mutual information",
        "random_samples": 0,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
