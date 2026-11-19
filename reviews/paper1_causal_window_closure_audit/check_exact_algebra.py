"""Exact finite algebra only; no stochastic trajectories or Monte Carlo.

Rebuild the counterexample from its rational model, compare gains/covariances
with the report, and verify its rank/cancellation/constant arithmetic.
"""

from fractions import Fraction as F
from pathlib import Path
import hashlib
import json


def mat(rows):
    return [[F(x) for x in row] for row in rows]


def add(a, b):
    return [[x + y for x, y in zip(ar, br)] for ar, br in zip(a, b)]


def mul(a, b):
    return [[sum(x * y for x, y in zip(row, col)) for col in zip(*b)] for row in a]


def transpose(a):
    return [list(row) for row in zip(*a)]


def neg(a):
    return [[-x for x in row] for row in a]


def scalar(s, a):
    return [[s * x for x in row] for row in a]


def norm2(a):
    return sum(row[0] ** 2 for row in a)


def det2(a):
    return a[0][0] * a[1][1] - a[0][1] * a[1][0]


def trace(a):
    return sum(a[i][i] for i in range(len(a)))


I = mat([[1, 0], [0, 1]])
C = mat([[1, 0]])
P0 = mat([[1, "1/2"], ["1/2", 1]])
Q = scalar(F(1, 2), I)
R = F(1)
Z = F(1)
checks = []


def check(name, actual, expected):
    assert actual == expected, (name, actual, expected)
    checks.append({"name": name, "status": "PASS", "exact": actual})


def gain(p, g):
    den = mul(mul(C, p), transpose(C))[0][0] + R + (1 - g) / Z
    return scalar(1 / den, mul(p, transpose(C)))


def post(p, g):
    return add(p, neg(mul(mul(gain(p, g), C), p)))


K = gain(P0, 1)
priors = {g: add(post(P0, g), Q) for g in (0, 1)}
Ks = {g: gain(priors[g], 1) for g in (0, 1)}
u = {g: mul(add(I, neg(mul(gain(priors[1], g), C))), K) for g in (0, 1)}
check("initial gain", K, mat([["1/2"], ["1/4"]]))
check("prior given initial send", priors[1], mat([[1, "1/4"], ["1/4", "11/8"]]))
check("target silent gain given send", gain(priors[1], 0), mat([["1/3"], ["1/12"]]))
check("target send gain given send", Ks[1], mat([["1/2"], ["1/8"]]))
check("target send gain given silence", Ks[0], mat([["7/13"], ["2/13"]]))
check("u0", u[0], mat([["1/3"], ["5/24"]]))
check("u1", u[1], mat([["1/4"], ["3/16"]]))
B11 = [[-u[1][i][0], -Ks[1][i][0]] for i in range(2)]
check("determinant B11", det2(B11), F(-1, 16))
check("legal cancellation on 11 per unit t", add(neg(u[1]), scalar(F(1, 2), Ks[1])), mat([[0], ["-1/8"]]))
check("silent branch visible response per unit t", mul(C, neg(u[0]))[0][0], F(-1, 3))

expected = {
    "11": mat([["1/2", "1/8"], ["1/8", "43/32"]]),
    "10": mat([["2/3", "1/6"], ["1/6", "65/48"]]),
    "01": mat([["7/13", "2/13"], ["2/13", "71/52"]]),
    "00": mat([["14/19", "4/19"], ["4/19", "105/76"]]),
}
labels = {}
for g0 in (0, 1):
    for g1 in (0, 1):
        h = f"{g0}{g1}"
        labels[h] = post(priors[g0], g1)
        check(f"covariance {h}", labels[h], expected[h])
        assert labels[h][0][0] > 0 and det2(labels[h]) > 0

check("covariance trace span", max(map(trace, labels.values())) - min(map(trace, labels.values())), F(167, 608))
umax = max(map(norm2, u.values()))
kmax = max(map(norm2, Ks.values()))
check("umax squared", umax, F(89, 576))
check("Kmax squared", kmax, F(53, 169))
check("causal constant coefficient independent of pstar", 16 * kmax, F(848, 169))
check("causal constant coefficient of inverse pstar", 9 * (2 * umax + kmax), F(89, 32) + F(477, 169))
next_variances = {h: p[0][0] + F(1, 2) + R for h, p in labels.items()}
check("Mstar squared", max(1 + v * Z for v in next_variances.values()), F(123, 38))
check("beta minimum", min(1 / (2 * (v + 1 / Z)) for v in next_variances.values()), F(19, 123))
v1 = priors[1][0][0] + R
check("silent prefactor inverse squared", 1 + v1 * Z, F(3))
check("silent exponent coefficient on a0 squared", K[0][0] ** 2 / (2 * (v1 + 1 / Z)), F(1, 24))

visible_radius = max(
    abs(u[1][0][0]) + abs(Ks[1][0][0]),
    abs(u[0][0][0]),
    abs(Ks[0][0][0]),
)
check("exact visible radius per b", visible_radius, F(3, 4))
assert visible_radius <= 1

swap = mat([[0, 1], [1, 0]])
swapK = mat([["1/2"], [0]])
check("swap one step invisible", mul(mul(C, swap), swapK), mat([[0]]))
check("swap two step visible", mul(mul(C, mul(swap, swap)), swapK), mat([["1/2"]]))

base = Path(__file__).resolve().parent
output = {
    "status": "PASS",
    "evidence_type": "exact rational finite algebra; not simulation or all-policy proof",
    "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "checks": checks,
}
(base / "exact_algebra_checks.json").write_text(
    json.dumps(output, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8"
)
print(f"PASS: {len(checks)} exact algebra assertions; no simulations.")
