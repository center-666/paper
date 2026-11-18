"""Independent exact verifier. Does not import the constructor or old engines."""
from fractions import Fraction as R
from collections import deque
from pathlib import Path
from copy import deepcopy
import json

DATA = Path(__file__).resolve().parents[1]/"data"
OBS = [0, 1, 0, 1, 0]
DIAG = [R("1.02"), R("1.01")]
GAIN = R(".6")
COUPLING = [R(".0102")*x for x in DIAG]
THRESHOLD2 = R(".04")


def linear(*terms):
    """Sparse homogeneous polynomial combination, independent of dense primary rows."""
    result = {}
    for scale, term in terms:
        for var, value in term.items():
            result[var] = result.get(var, R(0))+scale*value
    return {k: v for k, v in result.items() if v}


def measurement_form(time, node, L):
    r = OBS[node]
    form = {r: DIAG[r]**time, 2*L+5*time+node: R(1)}
    for t in range(time):
        form[2+2*t+r] = DIAG[r]**(time-1-t)
    return form


def replay(document):
    B, L = document["B"], document["L"]
    y = [[R(x) for x in row] for row in document["measurements"]]
    scale = R(document["construction"]["scale"])
    unscaled_y = [[R(x) for x in row] for row in document["construction"]["unscaled_measurements"]]
    assert y == [[scale*x for x in row] for row in unscaled_y]
    assert R(31, 32) <= scale < 1
    raw = [R(x) for x in document["neighborhood"]["raw_center"]]
    assert len(raw) == 7*L and raw[:2*L] == [0]*(2*L)
    assert raw[2*L:] == [x for row in y for x in row]
    covariance = [R(x) for x in document["neighborhood"]["gaussian_diagonal"]]
    assert covariance == [1, 1]+[R(".02")]*(2*(L-1))+[R(".2")]*(5*L)
    assert min(covariance) > 0
    dot = lambda form: sum((v*raw[i] for i, v in form.items()), R(0))
    estimates = {(i, r): {} for i in range(5) for r in range(2)}
    links = [(j, i) for j in range(5) for i in range(5) if j != i]
    assert document["edges_one_based"] == [[j+1, i+1] for j, i in links]
    caches = {(j, i, r): {} for j, i in links for r in range(2)}
    anchors = {link: 0 for link in links}
    failures = {link: [] for link in links}
    forms = []
    radius = R(1)
    target_trace = []
    original_high_norms = []
    for t, saved in enumerate(document["frames"]):
        k = t+1
        new = {}
        for i in range(5):
            Y = measurement_form(t, i, L)
            assert dot(Y) == y[t][i]
            for r in range(2):
                self_coef = DIAG[r]-4*COUPLING[r]-(GAIN if OBS[i] == r else 0)
                terms = [(self_coef, estimates[i, r])]
                terms += [(COUPLING[r], caches[j, i, r]) for j in range(5) if j != i]
                if OBS[i] == r:
                    terms.append((GAIN, Y))
                new[i, r] = linear(*terms)
        estimates = new
        assert [[str(dot(estimates[i, r])) for r in range(2)] for i in range(5)] == saved["estimates"]
        assert all(dot(estimates[i, 1]) == 0 for i in range(5))
        predictions = {key: linear((DIAG[key[2]], v)) for key, v in caches.items()}
        next_caches = {}
        target_info = None
        for index, (j, i) in enumerate(links):
            residual_forms = [linear((1, estimates[j, r]), (-1, predictions[j, i, r])) for r in range(2)]
            d = [dot(f) for f in residual_forms]
            assert list(map(str, d)) == saved["residuals"][index]
            assert [str(dot(predictions[j, i, r])) for r in range(2)] == saved["predicted_caches"][index]
            gap = sum(x*x for x in d)-THRESHOLD2
            assert gap != 0 and str(gap) == saved["squared_trigger_margins"][index]
            high = gap > 0
            original_norm = (gap+THRESHOLD2)/(scale*scale)
            assert high == (original_norm > THRESHOLD2)
            if high:
                original_high_norms.append(original_norm)
            assert high == saved["high"][index]
            assert anchors[j, i] == saved["anchors_before"][index]
            assert failures[j, i] == saved["failures_before"][index]
            lip = [sum(map(abs, f.values()), R(0)) for f in residual_forms]
            variation = sum(2*abs(x)*a+a*a for x, a in zip(d, lip))
            allowed = abs(gap)/(2*(1+variation))
            radius = min(radius, allowed)
            cert = document["neighborhood"]["residual_certificates"][20*t+index]
            assert cert["row_l1"] == list(map(str, lip))
            assert cert["quadratic_variation_bound"] == str(variation)
            assert cert["allowed_radius"] == str(allowed)
            forms.append((residual_forms, high))
            if index == 0:
                desired_high = k == 1 or k >= L-B-1
                assert high == desired_high
                assert (R(".35") < d[0] < R(".45")) if high else (R("-.05") < d[0] < R(".05"))
                target_info = dict(k=k, high=high, tau=anchors[j, i], H=failures[j, i][:])
            if k < L:
                deadline = anchors[j, i]+B+1
                known = sum(h >= max(1, deadline-L+1) for h in failures[j, i])
                defer = deadline-k+1 > B-known+1
                send = high and not defer
                actual_used = sum(h >= max(1, k-L+1) for h in failures[j, i])
                jam = bool(send and actual_used < B)
                receive = bool(send and not jam)
                assert [send, jam, receive] == [saved["attempts"][index], saved["blocks"][index], saved["successes"][index]]
                if jam:
                    failures[j, i].append(k)
                if not high or receive:
                    anchors[j, i] = k
                for r in range(2):
                    next_caches[j, i, r] = estimates[j, r] if receive else predictions[j, i, r]
                    assert str(dot(next_caches[j, i, r])) == saved["post_caches"][index][r]
                assert anchors[j, i] == saved["anchors_after"][index]
                assert k-anchors[j, i] <= B
                for end in range(1, k+1):
                    assert sum(max(1, end-L+1) <= h <= end for h in failures[j, i]) <= B
                if index == 0:
                    target_info.update(send=send, block=jam, success=receive)
        if k < L:
            caches = next_caches
        target_trace.append(target_info)
    assert document["frames"][-1]["communication_executed"] is False
    delta = min([R(1, 32)]+[(m-THRESHOLD2)/(4*m) for m in original_high_norms])
    assert 1-delta == scale and str(delta) == document["construction"]["delta"]
    assert failures[0, 1] == [1]+list(range(L-B, L-1))
    assert anchors[0, 1] == L-1
    assert target_trace[-2]["send"] and target_trace[-2]["success"]
    assert len(failures[0, 1]) == B
    assert radius == R(document["neighborhood"]["radius"]) > 0
    # Check conservative quadratic inequalities at the computed radius.
    for dforms, high in forms:
        d = [dot(row) for row in dforms]
        lips = [sum(map(abs, row.values()), R(0)) for row in dforms]
        variation = sum(2*abs(v)*c*radius+c*c*radius*radius for v, c in zip(d, lips))
        assert variation < abs(sum(v*v for v in d)-THRESHOLD2)/2
    # Exact action-independent endpoint checks with an exhaustive first-success
    # blocked suffix: frontier from window counts, not constructor metadata.
    H = failures[0, 1]
    D = anchors[0, 1]+B+1
    frontier = []
    for wait in range(D-L+1):
        occupied = H[:]
        tries = 0
        result = None
        for tick in range(L+wait, D+1):
            tries += 1
            count = sum(tick-L+1 <= h < tick for h in occupied)
            if count == B:
                result = tries
                break
            occupied.append(tick)
        frontier.append(result)
    m = frontier[0]
    safe = max(s for s, v in enumerate(frontier) if v is not None)
    cost = max(s for s, v in enumerate(frontier) if v == m)
    assert (m, safe, cost) == (1, min(B-1, L-B-2), 0)
    assert document["state_at_L"] == dict(anchor=L-1, failure_times=H, age=1,
        failure_ages=sorted(L-h for h in H), high=True, m_star=1, s_cost=0, s_safe=safe)
    return dict(B=B, L=L, triggers_checked=20*L, exact_nonzero_margins=True,
                full_network_radius_verified=True, radius=str(radius),
                min_squared_margin=str(min(abs(R(g)) for f in document["frames"] for g in f["squared_trigger_margins"])),
                frontier=frontier, target_trace=target_trace)


def no_gap_graph(B, L):
    """Independent protocol closure; no constructor or P5.2 code imported."""
    start = (1, ())
    pending = deque([start])
    reached = {start}
    while pending:
        a, ages = pending.popleft()
        room = B+1-a
        occupancy = lambda s: sum(x+s < L for x in ages)
        vals = []
        for wait in range(room+1):
            vals.append(next((m for m in range(1, room-wait+2)
                              if occupancy(wait+m-1)+m > B), None))
        valid = [s for s, m in enumerate(vals) if m is not None]
        assert valid
        assert max(valid) == max(s for s, m in enumerate(vals) if m == vals[0])
        older = tuple(x+1 for x in ages if x+1 < L)
        nxt = [(1, older)]
        if room-B+occupancy(room) > 0:
            nxt.append((a+1, older))
        elif len(ages) < B:
            nxt.append((a+1, (1,)+older))
        for dest in nxt:
            if dest not in reached:
                reached.add(dest); pending.append(dest)
    return len(reached)


def main():
    docs = [json.loads((DATA/"B2_L6_witness.json").read_text(encoding="utf-8"))]
    docs += json.loads((DATA/"parameterized_witnesses.json").read_text(encoding="utf-8"))["cases"]
    cases = [replay(w) for w in docs]
    # Exercise the general regularization lemma even though the six chosen
    # centers happen not to meet a threshold. Includes exact low equality.
    mathematical_norms = [R(0), THRESHOLD2, R("0.0400001"), R("0.16")]
    delta = min([R(1, 32)]+[(m-THRESHOLD2)/(4*m)
                          for m in mathematical_norms if m > THRESHOLD2])
    scaled = [(1-delta)**2*m for m in mathematical_norms]
    assert all((m > THRESHOLD2) == (v > THRESHOLD2)
               and v != THRESHOLD2 for m, v in zip(mathematical_norms, scaled))
    # Negative controls: B<=1 or L<=B+3, with complete symbolic closure.
    negative = [dict(B=B, L=L, states=no_gap_graph(B, L))
                for L in range(1, 11) for B in range(L)
                if B <= 1 or L <= B+3]
    # Verifier must reject corruption in measurements, margins, ACK, and radius.
    rejection = []
    for name in ("measurement", "margin", "ack", "radius"):
        copy = deepcopy(docs[0])
        if name == "measurement":
            copy["measurements"][0][0] = str(R(copy["measurements"][0][0])+1)
        if name == "margin":
            copy["frames"][0]["squared_trigger_margins"][0] = "0"
        if name == "ack":
            copy["frames"][0]["blocks"][0] = False
        if name == "radius":
            copy["neighborhood"]["radius"] = "1"
        try:
            replay(copy)
        except AssertionError:
            rejection.append(name)
        else:
            raise AssertionError("corruption not rejected: "+name)
    result = dict(status="PASS", independent_implementation=True,
                  imports_constructor=False, cases=cases, negative_controls=negative,
                  B2_L5_states=next(r["states"] for r in negative if r["B"] == 2 and r["L"] == 5),
                  rejected_corruptions=rejection, random_draws=0, formal_seeds=0,
                  exact_boundary_regularization_fixture=True,
                  verification_failures=0, negative_controls_are_not_physical_witnesses=True)
    (DATA/"regression_results.json").write_bytes((json.dumps(result, indent=2)+"\n").encode())
    print(json.dumps(dict(status="PASS", cases=len(cases), full_network_triggers=sum(c["triggers_checked"] for c in cases),
                          negative_parameter_pairs=len(negative),
                          negative_states=sum(r["states"] for r in negative),
                          corruption_rejections=len(rejection))))


if __name__ == "__main__":
    main()
