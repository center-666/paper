"""Binary interval replay of the two-tank M2/M3 estimators on public records."""
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy>=2", "python-flint==0.9.0"]
# ///
import argparse
from bisect import bisect_left
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from fractions import Fraction
import json
from pathlib import Path
import sys

import numpy as np
from flint import arb, ctx, fmpq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "paper2_stage6_vector_correction_20261122"))
from exact_linear import add, asfloat, inverse, matmul, matrix, transpose, update

CAP = Fraction(35, 100)
EPS = Fraction(1, 1000)
LEVELS = [Fraction(1, 40), Fraction(1, 20), Fraction(1, 10)]
REFERENCE = [CAP * j / 5 for j in (-1, -2, -5, 1, 2, 5)]


def ball(value):
    x = Fraction(value)
    return arb(fmpq(x.numerator, x.denominator))


def mv(rows, vec):
    return [sum(a*b for a, b in zip(row, vec)) for row in rows]


def trigger(distance, z):
    return -(-z * distance**2 / 2).expm1()


def rational_endpoint(endpoint):
    mantissa, exponent = endpoint.man_exp()
    return Fraction(int(mantissa)) * Fraction(2)**int(exponent)


def transport(direction, adjoint):
    vector = mv(adjoint, direction)
    scale = max(map(abs, vector))
    return tuple(v/scale for v in vector), scale


@dataclass
class Onset:
    first_send: int
    response: list = field(default_factory=lambda: [arb(0), arb(0)])
    linear: arb = field(default_factory=arb)
    quadratic: arb = field(default_factory=arb)


class TwoTank:
    def __init__(self):
        plant = json.loads((ROOT / "config/plants.json").read_text())["plants"]["industrial_two_tank"]
        self.A, self.C, self.Q, self.P = [matrix(plant[k]) for k in ("A", "C", "Q", "P0")]
        if self.C != [[1, 0]] or matrix(plant["W"]) != [[1, 0], [0, 1]]:
            raise ValueError("This two-tank replay requires C=[1,0] and W=I")
        self.R, self.Z = Fraction(plant["R"][0][0]), Fraction(plant["Z"])
        self.A_ball = [[ball(v) for v in row] for row in self.A]
        self.A_float = np.array(asfloat(self.A))
        self.B_float = np.array(plant["B"], float)
        self.B_ball = [[ball(v) for v in row] for row in plant["B"]]
        self.prior = np.zeros(2)
        self.nominal_prior = [arb(0), arb(0)]
        self.onsets, self.sends = [], []
        self.send_times = []
        self.intervals = None
        self.directions = []
        self.old = None
        self.mass = [arb(0) for _ in REFERENCE]
        self.ref = arb(1)

    def observe(self, frame):
        t, sent, center, payload = frame
        posterior, gain, transition = update(self.P, self.C, self.R + (0 if sent else 1/self.Z))
        variance = ball(self.P[0][0] + self.R)
        silent_variance = variance + ball(1/self.Z)
        self.P = add(matmul(matmul(self.A, posterior), transpose(self.A)), self.Q)
        # Interpret the publicly logged binary64 observations as exact real
        # inputs. Carry the mathematical nominal mean separately from the
        # frozen binary64 monitor that publishes the estimate.
        offset = arb(center) - self.nominal_prior[0]
        observation = payload if sent else center
        residual = observation - self.prior[0]
        self.monitor = self.prior + np.asarray(asfloat(gain)).ravel() * residual
        control = [.15 if t % 120 < 60 else .08, .05]
        self.prior = self.A_float @ self.monitor + self.B_float @ control
        K = [ball(row[0]) for row in gain]
        u = arb(observation) - self.nominal_prior[0]
        # (I-KC) times the prior avoids double-counting its interval radius.
        T = [[ball(v) for v in row] for row in transition]
        corrected = mv(T, self.nominal_prior)
        nominal = [x + k*arb(observation) for x, k in zip(corrected, K)]
        self.monitor_error = [arb(float(x))-y for x, y in zip(self.monitor, nominal)]
        inputs = mv(self.B_ball, [ball(str(x)) for x in control])
        self.nominal_prior = [x+y for x, y in zip(mv(self.A_ball, nominal), inputs)]
        z = ball(self.Z)
        if sent:
            mark = arb(payload) - arb(center)
            denominator = trigger(mark, z)
            if not denominator > 0:
                raise ArithmeticError("Unresolved nominal send density")
            self.onsets.append(Onset(len(self.sends)))
            self.send_times.append(t)
            self.sends.append((mark, denominator))
        # Prior response to a unit bias active since time zero (shared by
        # the six predictable reference kernels).
        eta = mv(self.A_ball, self.onsets[0].response)[0] if self.onsets else arb(0)
        weight = ball(Fraction(1, (t+1)*(t+2)))
        for j, amplitude in enumerate(REFERENCE):
            b = ball(amplitude)
            shift = -b*eta
            if sent:
                shift += b
                ratio = ((u*shift - shift**2/2)/variance).exp() * trigger(mark-b, z)/denominator
            else:
                ratio = ((offset*shift - shift**2/2)/silent_variance).exp()
            self.mass[j] = (self.mass[j]+weight)*ratio
        self.ref = ball(Fraction(1, t+2)) + sum(self.mass)/len(self.mass)
        for onset in self.onsets:
            prior = mv(self.A_ball, onset.response)
            eta = prior[0]
            if sent:
                onset.linear += (1-eta)*u/variance
                onset.quadratic += (1-eta)**2/variance
            else:
                onset.linear -= offset*eta/silent_variance
                onset.quadratic += eta**2/silent_variance
            onset.response = mv(T, prior)
            if sent:
                onset.response = [x+k for x, k in zip(onset.response, K)]
        if self.old or self.directions:
            adjoint = transpose(inverse(matmul(transition, self.A)))
            self.directions = [transport(d, adjoint)[0] for d in self.directions]
            if self.old:
                d, scale = transport(self.old[0], adjoint)
                support = self.old[1]/scale
                if sent:
                    support -= CAP*abs(sum(di*ki[0] for di, ki in zip(d, gain)))
                self.old = (d, support) if support > 0 else None

    def likelihood(self, onset, amplitude, upper=False):
        gaussian = onset.linear*amplitude - onset.quadratic*amplitude**2/2
        value = (gaussian.upper() if upper else gaussian).exp()
        for mark, denominator in self.sends[onset.first_send:]:
            distance = mark-amplitude
            # Send probability increases with the absolute distance.
            if upper:
                distance = distance.abs_upper()
            value *= trigger(distance, ball(self.Z))/denominator
        return value

    def certify(self, direction, target, witness_index, witness_b):
        cutoff = self.ref*ball(EPS)
        if not cutoff > 1:
            return False
        if witness_index is None or not (0 <= witness_index < len(self.onsets) and abs(witness_b) <= CAP):
            return False
        if not self.likelihood(self.onsets[witness_index], ball(witness_b)) > cutoff:
            return False
        for onset in self.onsets:
            coefficient = sum(x*ball(d) for x, d in zip(onset.response, direction))
            pending = [(-CAP, CAP, 0)]
            while pending:
                lo, hi, depth = pending.pop()
                interval = ball(lo).union(ball(hi))
                if coefficient*interval > ball(target):
                    continue
                if self.likelihood(onset, interval, upper=True) < cutoff:
                    continue
                # A compatible point with insufficient support suffices to
                # refuse this proposal. An unresolved box also yields no action.
                mid = (lo+hi)/2
                if (coefficient*ball(mid) <= ball(target)
                        and self.likelihood(onset, ball(mid)) >= cutoff):
                    return False
                if depth == 16:
                    return False
                pending.extend([(lo, mid, depth+1), (mid, hi, depth+1)])
        return True

    def propose(self):
        # Midpoints rank point proposals only. Certification covers the whole
        # continuous parameter range, independently of this ranking.
        best = 1.0
        selected = None
        for index in (-5, -4, -3, -2, -1, 1, 2, 3, 4, 5):
            amplitude = CAP*index/5
            for k, onset in enumerate(self.onsets):
                score = float(self.likelihood(onset, ball(amplitude)).mid())
                if score > best:
                    best = score
                    selected = (k, amplitude)
        if selected is None:
            return [], None, Fraction(0)
        k, amplitude = selected
        point = [float(amplitude)*float(x.mid()) for x in self.onsets[k].response]
        scale = max(map(abs, point))
        if scale < 1e-14:
            return [], k, amplitude
        return [Fraction(format(x/scale, ".6f")) for x in point], k, amplitude

    @staticmethod
    def ideal_action(direction, target):
        step = min(target/sum(d*d for d in direction), 1/sum(map(abs, direction)))
        return [step*d for d in direction]

    def accept(self, direction, target):
        direction = tuple(direction)
        if self.intervals is None:
            self.intervals = {k: (-CAP, CAP) for k in range(len(self.onsets))}
        kept = {}
        for k, (lo, hi) in self.intervals.items():
            q = sum(ball(d)*h for d, h in zip(direction, self.onsets[k].response))
            left, right = rational_endpoint(q.lower()), rational_endpoint(q.upper())
            pieces = []
            if right > 0 and target/right <= hi:
                pieces.append((max(lo, target/right), hi))
            if left < 0 and target/left >= lo:
                pieces.append((lo, min(hi, target/left)))
            if pieces:
                kept[k] = min(x for x, _ in pieces), max(y for _, y in pieces)
        self.intervals = kept
        if direction not in self.directions:
            self.directions.append(direction)
        candidate = (direction, target)
        if self.old is None or (sum(x*x for x in self.ideal_action(*candidate))
                                > sum(x*x for x in self.ideal_action(*self.old))):
            self.old = candidate

    def publish(self, direction, target, radius):
        ideal = self.ideal_action(direction, target)
        actual = [Fraction(float(m))-Fraction(float(m)-float(a)) for m, a in zip(self.monitor, ideal)]
        if sum(map(abs, actual)) > 1:
            return (Fraction(0), Fraction(0)), Fraction(0)
        loss = sum(r*ball(abs(a-i)) for r, a, i in zip(radius, actual, ideal))
        discrepancy = sum(e.abs_upper()*ball(abs(a)) for e, a in zip(self.monitor_error, actual))
        lower = ball(2*sum(a*a for a in ideal)-sum(a*a for a in actual))-2*(loss+discrepancy)
        if lower > 0:
            return actual, rational_endpoint(lower.lower())
        return (Fraction(0), Fraction(0)), Fraction(0)

    def outputs(self):
        zero = ((Fraction(0), Fraction(0)), Fraction(0))
        if not self.old and not self.intervals:
            return zero, zero
        radius = [ball(CAP)*max(h.response[j].abs_upper() for h in self.onsets) for j in range(2)]
        legacy = self.publish(*self.old, radius) if self.old else zero
        best = legacy if self.intervals else zero
        for d in self.directions if self.intervals else ():
            projections = []
            for k, (lo, hi) in self.intervals.items():
                q = sum(ball(di)*h for di, h in zip(d, self.onsets[k].response))
                projections.extend(((q*ball(lo)).lower(), (q*ball(hi)).lower()))
            support = rational_endpoint(min(projections))
            if support > 0:
                candidate = self.publish(d, support, radius)
                if candidate[1] > best[1]:
                    best = candidate
        return legacy, best


def replay(path):
    ctx.prec = 64
    record = json.loads(path.read_text())
    model = TwoTank()
    archived = {q["time"]: q for q in record["queries"]}
    results = []
    useful_counts = [0, 0]
    different_useful = [0, 0]
    checked = violations = uncertain = 0
    for frame in record["public"]:
        model.observe(frame)
        t = frame[0]
        query = t in (127, 255, 383, 511)
        if query:
            direction, onset_index, amplitude = model.propose()
            decisions = []
            if direction:
                for level in LEVELS:
                    target = level*sum(map(abs, direction))
                    passed = model.certify(direction, target, onset_index, amplitude)
                    decisions.append(passed)
                    if not passed:
                        break
                    model.accept(direction, target)
        outputs = model.outputs()
        # Known onset/amplitude enter only this offline audit.
        k = bisect_left(model.send_times, 50)
        delta = list(model.monitor_error)
        if k < len(model.onsets):
            delta = [e+ball(str(record["b"]))*h for e, h in zip(delta, model.onsets[k].response)]
        for m, (action, lower) in enumerate(outputs):
            if 50 <= t <= 561:
                useful = lower >= Fraction(1,1600)
                useful_counts[m] += useful
                different_useful[m] += useful != (record["bounds"][t][m] >= 1/1600)
            if lower > 0:
                checked += 1
                risk = 2*sum(e*ball(a) for e, a in zip(delta, action))-ball(sum(a*a for a in action))
                violations += int(risk < ball(lower))
                uncertain += int(not (risk >= ball(lower) or risk < ball(lower)))
        if not query:
            continue
        bound = outputs[1][1]
        q = archived[t]
        archived_direction = [Fraction(v) for v in q["direction"] or []]
        frozen = [r["certified"] for r in q["levels"]]
        decisions_match = decisions == frozen
        # Frozen likelihoods use rounded residuals, ours use the actual public
        # values. Report the numerical difference instead of imposing equality.
        cutoff_difference = None
        if q["levels"]:
            cutoff = q["levels"][0]["cutoff"]
            old = ball(cutoff["lo"]).union(ball(cutoff["hi"]))
            cutoff_difference = str(((model.ref*ball(EPS)).log()-old).abs_upper())
        results.append(dict(time=t, binary=decisions, frozen=frozen, match=decisions_match,
                            direction_match=direction == archived_direction,
                            log_cutoff_difference=cutoff_difference,
                            useful=bound >= Fraction(1,1600), risk_bound=float(bound)))
    return dict(id=record["id"], queries=results, useful_M2_M3=useful_counts,
                different_useful_M2_M3=different_useful, checked=checked,
                violations=violations, numerically_undecided=uncertain)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path, help="Archived two-tank JSON files or their directories")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    files = [f for p in args.files for f in (sorted(p.glob("*.json")) if p.is_dir() else [p])]
    if not files or args.workers < 1:
        parser.error("Supply two-tank records and a positive worker count")
    if args.workers > 1:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            results = list(pool.map(replay, files))
    else:
        results = [replay(p) for p in files]
    output = json.dumps(results, indent=2)
    if args.output:
        temporary = args.output.with_suffix(".tmp")
        temporary.write_text(output+"\n", encoding="utf8")
        temporary.replace(args.output)
    else:
        print(output)
