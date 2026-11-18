"""Exact finite witnesses under the original ACK rule and per-edge greedy DoS.

Not a Monte Carlo runner. No random numbers, experiment seeds, or old imports.
"""
from fractions import Fraction as F
from pathlib import Path
import argparse
import json

ROOT = Path(__file__).resolve().parents[1]
A = (F(51, 50), F(101, 100))
K = F(3, 5)
C = tuple(F(51, 5000)*a for a in A)
THETA = F(1, 5)
OBS = (0, 1, 0, 1, 0)
EDGES = [(j, i) for j in range(5) for i in range(5) if j != i]
CASES = [(2, 6), (2, 7), (3, 7), (3, 8), (5, 9), (5, 10)]


def encode(x):
    if isinstance(x, F):
        return str(x)
    if isinstance(x, (tuple, list)):
        return [encode(v) for v in x]
    if isinstance(x, dict):
        return {k: encode(v) for k, v in x.items()}
    return x


def pack(x):
    return (json.dumps(encode(x), ensure_ascii=False, indent=2)+"\n").encode()


def high_target(k, B, L):
    return k == 1 or k >= L-B-1


def execute(B, L, measurements=None):
    """Constructor can solve y_1,k; replay consumes supplied rational y exactly."""
    hat = [[F(0), F(0)] for _ in range(5)]
    caches = [[F(0), F(0)] for _ in EDGES]
    anchors = [0]*20
    failed = [[] for _ in EDGES]
    Y, rows = [], []
    for t in range(L):
        # The communication at t has already finished; current measurement
        # forms estimates at t+1. At t=0 caches/estimates are initialized to 0.
        before = [v[:] for v in hat]
        if measurements is None:
            y = [F(0), F(0), F(t+1, 100), F(0), -F(t+1, 125)]
            q = F(2, 5) if high_target(t+1, B, L) else F(1, 40)
            desired = A[0]*caches[0][0]+q
            deterministic = A[0]*hat[0][0]+sum(
                C[0]*(caches[e][0]-hat[0][0])
                for e, (_, i) in enumerate(EDGES) if i == 0)
            y[0] = hat[0][0]+(desired-deterministic)/K
        else:
            y = list(measurements[t])
        Y.append(y)
        # Complete simultaneous five-node update.
        hat = [[A[r]*before[i][r]
                + (K*(y[i]-before[i][r]) if OBS[i] == r else 0)
                + sum(C[r]*(caches[e][r]-before[i][r])
                      for e, (_, dest) in enumerate(EDGES) if dest == i)
                for r in range(2)] for i in range(5)]
        k = t+1
        predicted = [[A[r]*cache[r] for r in range(2)] for cache in caches]
        residuals = [[hat[j][r]-predicted[e][r] for r in range(2)]
                     for e, (j, _) in enumerate(EDGES)]
        margins = [sum(x*x for x in d)-THETA**2 for d in residuals]
        highs = [g > 0 for g in margins]
        assert highs[0] == high_target(k, B, L)
        assert all(v[1] == 0 for v in hat+caches+predicted+residuals)
        frame = dict(k=k, estimates=hat, predicted_caches=predicted,
                     residuals=residuals, squared_trigger_margins=margins,
                     high=highs, anchors_before=anchors[:],
                     failures_before=[v[:] for v in failed],
                     communication_executed=k < L)
        if k < L:
            attempts, blocks, successes, decisions = [], [], [], []
            for e, (j, i) in enumerate(EDGES):
                D = anchors[e]+B+1
                used_D = sum(max(1, D-L+1) <= f < k for f in failed[e])
                attempt = highs[e] and D-k+1 <= B-used_D+1
                used_now = sum(max(1, k-L+1) <= f < k for f in failed[e])
                block = bool(attempt and used_now < B)
                success = bool(attempt and not block)
                attempts.append(bool(attempt)); blocks.append(block); successes.append(success)
                decisions.append(dict(deadline=D, used_deadline=used_D,
                                      used_current=used_now))
                if block:
                    failed[e].append(k)
                caches[e] = hat[j][:] if success else predicted[e][:]
                if success or not highs[e]:
                    anchors[e] = k
                assert k-anchors[e] <= B
                assert sum(max(1, k-L+1) <= f <= k for f in failed[e]) <= B
            frame.update(attempts=attempts, blocks=blocks, successes=successes,
                         decisions=decisions, post_caches=[x[:] for x in caches],
                         anchors_after=anchors[:])
        rows.append(frame)
    return Y, rows


def raw_measurement_rows(L):
    """y_i,t = row * zeta, zeta=(x0,w0..wL-2,v(time,node))."""
    dim = 7*L
    state = [[F(0)]*dim for _ in range(2)]
    state[0][0] = state[1][1] = F(1)
    answer = []
    for t in range(L):
        ys = []
        for i in range(5):
            row = state[OBS[i]][:]
            row[2*L+5*t+i] += 1
            ys.append(row)
        answer.append(ys)
        if t < L-1:
            state = [[a*x for x in row] for a, row in zip(A, state)]
            for r in range(2):
                state[r][2+2*t+r] += 1
    return answer


def coefficient_certificate(L, Y, rows):
    """Propagate full raw-noise linear maps on the saved discrete branch."""
    dim = 7*L
    hat = [[[F(0)]*dim for _ in range(2)] for _ in range(5)]
    cache = [[[F(0)]*dim for _ in range(2)] for _ in EDGES]
    yrows = raw_measurement_rows(L)
    center = [F(0)]*(2*L)+[x for y in Y for x in y]
    certificates = []
    radius = F(1)
    for t, frame in enumerate(rows):
        next_hat = []
        for i in range(5):
            node = []
            for r in range(2):
                self_factor = A[r]-4*C[r]-(K if OBS[i] == r else 0)
                row = [self_factor*x for x in hat[i][r]]
                for e, (_, dest) in enumerate(EDGES):
                    if dest == i:
                        row = [x+C[r]*y for x, y in zip(row, cache[e][r])]
                if OBS[i] == r:
                    row = [x+K*y for x, y in zip(row, yrows[t][i])]
                node.append(row)
            next_hat.append(node)
        hat = next_hat
        pred = [[[A[r]*v for v in edge[r]] for r in range(2)] for edge in cache]
        for e, (j, _) in enumerate(EDGES):
            linear = [[x-y for x, y in zip(hat[j][r], pred[e][r])] for r in range(2)]
            d = frame["residuals"][e]
            assert all(sum(x*y for x, y in zip(row, center)) == d[r]
                       for r, row in enumerate(linear))
            lip = [sum(abs(x) for x in row) for row in linear]
            b = 2*sum(abs(x)*c for x, c in zip(d, lip))+sum(c*c for c in lip)
            gap = abs(frame["squared_trigger_margins"][e])
            assert gap > 0
            bound = gap/(2*(1+b))
            radius = min(radius, bound)
            certificates.append(dict(k=t+1, edge=e, row_l1=lip,
                                     margin_abs=gap, quadratic_variation_bound=b,
                                     allowed_radius=bound))
        if t+1 < L:
            cache = [hat[j] if frame["successes"][e] else pred[e]
                     for e, (j, _) in enumerate(EDGES)]
    return dict(raw_dimension=dim, norm="Euclidean (also valid for coordinate infinity norm)",
                radius=radius, radius_decimal=float(radius), positive=radius > 0,
                gaussian_diagonal=[F(1)]*2+[F(1, 50)]*(2*(L-1))+[F(1, 5)]*(5*L),
                raw_center=center, residual_certificates=certificates)


def construct(B, L):
    assert B >= 2 and L >= B+4
    centerY, center_rows = execute(B, L)
    high_norms = [g+THETA**2 for row in center_rows
                  for g in row["squared_trigger_margins"] if g > 0]
    delta = min([F(1, 32)] + [(m-THETA**2)/(4*m) for m in high_norms])
    scale = 1-delta
    Y = [[scale*x for x in row] for row in centerY]
    _, rows = execute(B, L, Y)
    for pre, post in zip(center_rows, rows):
        assert pre["high"] == post["high"]
        for key in ("estimates", "predicted_caches", "residuals"):
            assert post[key] == [[scale*x for x in v] for v in pre[key]]
        assert all(g != 0 for g in post["squared_trigger_margins"])
    last = rows[-1]
    H = last["failures_before"][0]
    assert H == [1]+list(range(L-B, L-1))
    assert last["anchors_before"][0] == L-1
    assert rows[-2]["successes"][0]
    ss = min(B-1, L-B-2)
    return dict(B=B, L=L, edges_one_based=[[j+1, i+1] for j, i in EDGES],
                policy="original manuscript eq:policy", adversary="all-edge causal greedy",
                state_at_L=dict(anchor=L-1, failure_times=H, age=1,
                    failure_ages=sorted(L-h for h in H), high=True,
                    m_star=1, s_cost=0, s_safe=ss),
                construction=dict(low_q_center=F(1, 40), high_q_center=F(2, 5),
                    scale=scale, delta=delta, unscaled_measurements=centerY,
                    unscaled_threshold_equalities=sum(g == 0 for row in center_rows
                                                      for g in row["squared_trigger_margins"])),
                measurements=Y, frames=rows,
                neighborhood=coefficient_certificate(L, Y, rows))


def outputs():
    all_cases = [construct(B, L) for B, L in CASES]
    margins, balls = [], []
    for w in all_cases:
        gaps = [abs(g) for frame in w["frames"] for g in frame["squared_trigger_margins"]]
        margins.append(dict(B=w["B"], L=w["L"], trigger_decisions=len(gaps),
                            min_squared_margin=min(gaps),
                            min_squared_margin_decimal=float(min(gaps)),
                            threshold_equalities=0, scale=w["construction"]["scale"]))
        n = w["neighborhood"]
        balls.append({key: n[key] for key in
                      ("raw_dimension", "radius", "radius_decimal", "norm", "positive")}
                     | dict(B=w["B"], L=w["L"]))
    return {
        "B2_L6_witness.json": pack(all_cases[0]),
        "parameterized_witnesses.json": pack(dict(cases=all_cases[1:])),
        "trigger_margin_summary.json": pack(dict(cases=margins, total=sum(x["trigger_decisions"] for x in margins))),
        "open_neighborhood_summary.json": pack(dict(cases=balls, exact_formula="rho=min(1,min |g|/[2(1+B_g)])")),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    data = ROOT/"data"
    data.mkdir(parents=True, exist_ok=True)
    for name, raw in outputs().items():
        if args.verify:
            assert (data/name).read_bytes() == raw, name
        else:
            (data/name).write_bytes(raw)
    print("PASS: six full-network rational witnesses; all 20 edges; original policy; no RNG")


if __name__ == "__main__":
    main()
