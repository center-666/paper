"""Exact arithmetic checks of printed identities; no estimator or Monte Carlo.

Run with Python 3 (standard library only). Output is JSON; --output refuses
to overwrite an existing result. The checks do not import simulation modules.
"""
from __future__ import annotations

import argparse
from fractions import Fraction as F
import hashlib
import itertools
import json
from pathlib import Path


def add(a, b):
    return [[x + y for x, y in zip(ar, br)] for ar, br in zip(a, b)]


def scale(c, a):
    return [[c * x for x in row] for row in a]


def transpose(a):
    return [list(row) for row in zip(*a)]


def multiply(a, b):
    bt = transpose(b)
    return [[sum((x * y for x, y in zip(row, col)), F(0)) for col in bt]
            for row in a]


def congruence(a, p):
    return multiply(multiply(a, p), transpose(a))


def moment_check(q):
    # Two mutually connected sensors. A=H=Q=R=P0=1, K=1/2,
    # epsilon=1/10; identical zero initial estimates give P0_network=11'.
    # K=1/2 agrees with printed (9)-(10) at this first step.
    eps, gain = F(1, 10), F(1, 2)
    p = [[F(1), F(1)], [F(1), F(1)]]
    zero = [[F(0), F(0)], [F(0), F(0)]]
    exact, mean_f, noise_mean = zero, zero, zero
    records = []
    for g1, g2 in itertools.product([0, 1], repeat=2):
        prob = (q if g1 else 1 - q) * (q if g2 else 1 - q)
        f = [[1 - eps * g2 - gain * g1, eps * g2],
             [eps * g1, 1 - eps * g1 - gain * g2]]
        noise = [[1 + g1 * gain**2, F(1)],
                 [F(1), 1 + g2 * gain**2]]
        exact = add(exact, scale(prob, add(congruence(f, p), noise)))
        mean_f = add(mean_f, scale(prob, f))
        noise_mean = add(noise_mean, scale(prob, noise))
        records.append({"gamma": [g1, g2], "probability": prob,
                        "transition": f, "noise_second_moment": noise})
    printed = add(congruence(mean_f, p), noise_mean)
    omitted = add(exact, scale(F(-1), printed))
    expected = [[q * (1 - q) * gain**2, F(0)],
                [F(0), q * (1 - q) * gain**2]]
    assert omitted == expected
    if q == F(1, 2):
        assert exact == [[F(7, 4), F(25, 16)], [F(25, 16), F(7, 4)]]
        assert printed == [[F(27, 16), F(25, 16)], [F(25, 16), F(27, 16)]]
    if q == 1:
        assert exact == printed
    return {"q": q, "exact_next_second_moment": exact,
            "printed_mean_transition_expression": printed,
            "omitted_switching_term": omitted,
            "printed_identity_holds": exact == printed,
            "enumerated_modes": records}


def lmi_check():
    # Printed Lemma 7: Phi=[[I,X],[X',I]], X=I-epsilon*q*L*A.
    eps, q = F(1, 10), F(1, 2)
    lap = [[F(1), F(-1)], [F(-1), F(1)]]
    ident = [[F(1), F(0)], [F(0), F(1)]]
    x = add(ident, scale(-eps * q, lap))
    xt = transpose(x)
    phi = [ident[i] + x[i] for i in range(2)]
    phi += [xt[i] + ident[i] for i in range(2)]
    v = [[F(1)], [F(1)], [F(-1)], [F(-1)]]
    value = multiply(multiply(transpose(v), phi), v)[0][0]
    assert value == 0
    return {"laplacian": lap, "A": F(1), "epsilon": eps, "q": q,
            "Phi": phi, "nonzero_test_vector": v,
            "quadratic_form": value, "strict_positive_definite": False}


def gaussian_rejection_check():
    # D~N(0,1), acceptance probability exp(-D^2/nu), nu=2/3.
    # Integral identity gives acceptance mass 1/sqrt(1+2/nu)=1/2
    # and accepted variance 1/(1+2/nu)=1/4.
    nu, z, va = F(2, 3), F(1, 2), F(1, 4)
    assert z**2 == 1 / (1 + 2 / nu)
    second = (1 - z * va) / (1 - z)
    fourth = (3 - z * 3 * va**2) / (1 - z)
    cumulant = fourth - 3 * second**2
    assert second == F(7, 4) and fourth == F(93, 16)
    assert cumulant == F(-27, 8)
    return {"difference_variance": F(1), "threshold_scale_nu": nu,
            "acceptance_probability": z, "rejected_second_moment": second,
            "rejected_fourth_moment": fourth,
            "gaussian_fourth_moment_at_same_variance": 3 * second**2,
            "rejected_fourth_cumulant": cumulant,
            "rejected_distribution_gaussian": False,
            "scope": "Gate likelihood and conditional Gaussian proof step, not a full network performance test."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    here = Path(__file__).resolve()
    repo = here.parents[3]
    sources = {}
    for name in ["yang2014", "yang2019", "zhou2022"]:
        relative = Path("literature_review/fdi_replay_reread_20261112") / (name + ".pdf")
        p = repo / relative
        sources[name] = {"path": relative.as_posix(), "available": p.exists(),
                         "sha256": hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None}
    result = {
        "audit_id": "20261114_r02_source_formula_checks",
        "reference_commit": "5cb72eeeac5bee00aa75527aa4a6558b97e74190",
        "type": "EXACT_ARITHMETIC_AND_ANALYTIC_MOMENT_CHECKS",
        "not_monte_carlo": True,
        "seeds": [],
        "source_code_sha256": hashlib.sha256(here.read_bytes()).hexdigest(),
        "sources": sources,
        "yang2014_random_activation": moment_check(F(1, 2)),
        "yang2014_all_active_control": moment_check(F(1)),
        "yang2014_printed_lmi": lmi_check(),
        "zhou2022_rejection_likelihood": gaussian_rejection_check(),
        "all_arithmetic_assertions_passed": True,
        "claim_scope": "Printed identities and missing assumptions; no claim that published simulations or archived project results are invalid."
    }
    payload = json.dumps(result, ensure_ascii=False, indent=2,
                         default=lambda value: str(value) if isinstance(value, F) else None) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as handle:
            handle.write(payload)
        print(args.output.as_posix())
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()
