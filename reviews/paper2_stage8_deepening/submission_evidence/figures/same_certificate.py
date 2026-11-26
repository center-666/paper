"""Trace the same frozen certificate in both propagation rules on two public histories."""
from fractions import Fraction as F
from pathlib import Path
import json
import sys

HERE = Path(__file__).resolve().parent
STAGE = HERE.parents[1]
sys.path.insert(0, str(STAGE / "code"))
from experiment import (CAP, D, Methods, USEFUL, W, capped_halfspace_action,
                        inverse, matmul, move, publish, restrict, transpose, update)


def replay(group):
    case = json.loads((STAGE / "results/confirmation" / f"{group}-00.json").read_text())
    threshold = D("5.4575843864474839580272229276002610049268878740485")
    method = Methods(D(".35"), threshold, mode="M3")
    # The first observed separation within the scored window, independent of sign.
    public = case["public"]
    bounds = case["bounds"]
    queries = {q["time"] for q in case["queries"]}
    split = next(t for t in range(51, 562) if public[t][1] and t not in queries
                 and bounds[t-1][0] >= USEFUL and bounds[t][0] == 0 and bounds[t][1] >= USEFUL)
    start = max(t for t in queries if t < split)
    stop = min((t-1 for t in queries if t > start), default=561)
    old = None
    points = []
    first_cert = min(q["time"] for q in case["queries"] if any(r["certified"] for r in q["levels"]))
    for frame in public[:stop+1]:
        t, sent, *_ = frame
        core = method.core
        if t > start:
            _, gain, transition = update(core.P, core.C, core.R+(0 if sent else 1/core.Z))
            direction, scale = move(direction, transpose(inverse(matmul(transition, core.A))))
            if old is not None:
                old /= scale
                if sent:
                    old -= method.cap * abs(sum(d*g[0] for d, g in zip(direction, gain)))
                if old <= 0:
                    old = None
        actions, query, *_ = method.step(frame)
        if t < start:
            continue
        if t == start:
            direction = tuple(F(x) for x in query["direction"])
            certified = [F(q["target"]) for q in query["levels"] if q["certified"]]
            target = max(certified)
            old = target
            view = core.view()
            boxes = {}
            for k in range(view.n):
                box = restrict((-method.cap, method.cap), view.support_coefficient(k, direction), target)
                if box is not None:
                    boxes[k] = box
            anchor_direction = [str(x) for x in direction]
        assert direction in method.directions
        if start <= t <= split:
            assert method.old == ((direction,old) if old is not None else None)
        values = []
        for k, box in boxes.items():
            q = core.support_coefficient(k, direction)
            values.extend(F(x)*b for x in (q.lo, q.hi) for b in box)
        support = min(values)
        supports = [old or F(0), support]
        certified_bounds = []
        for value in supports:
            action, _ = capped_halfspace_action((direction, value) if value > 0 else None, W, CAP)
            delivered, lower, _ = publish(method.monitor, action, method.radius)
            certified_bounds.append(float(lower))
        if t == split:
            assert (delivered, lower) == actions["M3"]
            # Identify all stored directions producing the selected displacement
            # and exact released lower bound. A sole match disambiguates ties.
            origin_matches = []
            for index, candidate in enumerate(method.directions):
                support_all = min(
                    F(endpoint)*b for k, box in method.intervals.items()
                    for q in [core.support_coefficient(k,candidate)]
                    for endpoint in (q.lo, q.hi) for b in box)
                if support_all > 0:
                    act, _ = capped_halfspace_action((candidate,support_all),W,CAP)
                    if publish(method.monitor,act,method.radius)[:2] == actions["M3"]:
                        origin_matches.append((index,candidate))
            assert [d for _, d in origin_matches] == [direction]
            source_index = origin_matches[0][0]
            normalized = [float(x) for x in direction]
        points.append(dict(t=t, sent=sent, M2_support=float(supports[0]), M3_support=float(support),
                           M2_bound=certified_bounds[0], M3_bound=certified_bounds[1],
                           same_M3_release=(delivered, lower) == actions["M3"]))
        assert [float(actions[k][1]) for k in ("M2", "M3")] == bounds[t]
    end = split
    by_time = {p["t"]: p for p in points}
    while end <= stop and by_time[end]["M2_bound"] == 0 and by_time[end]["M3_bound"] >= USEFUL:
        end += 1
    return dict(id=case["id"], first_certificate=first_cert, signed_at=start,
                target=str(target), direction=anchor_direction,
                winning_direction_index_at_split=source_index, normalized_direction_at_split=normalized,
                feasible_onsets=len(boxes), split=split, useful_until=end-1,
                useful_count=end-split, samples=points)


if __name__ == "__main__":
    results = [replay(g) for g in ("strong_positive", "strong_negative")]
    (HERE / "same_certificate.json").write_text(json.dumps(results, indent=2)+"\n", encoding="utf8")
