"""Rebuild the frozen-data audit and the standalone four-path timing comparison."""
import argparse
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import platform
import sys
from time import perf_counter, process_time

from method import A, B, Fast, QUERIES, ROOT, USEFUL, np
import scipy

HERE = Path(__file__).resolve().parent


def audit(path):
    row = json.loads(path.read_text())
    archived = {q["time"]: q for q in row["queries"]}
    fast = Fast()
    prior = np.zeros(2)
    mismatched_direction = []
    mismatched_decision = []
    useful = [0, 0]
    useful_diff = [0, 0]
    act_diff = [0, 0]
    checked = violations = gain_negative = 0
    queries_with_pass = 0
    nonzero_m3 = 0
    max_risk_shortfall = 0.
    hashes = [hashlib.sha256() for _ in range(2)]
    for frame in row["public"]:
        t, sent, center, payload = frame
        outputs, q, K, _ = fast.step(frame)
        if q is not None:
            d, decisions, _ = q
            old = archived[t]
            archived_d = [float(Fraction(v)) for v in old["direction"] or []]
            if not np.array_equal([] if d is None else d, archived_d):
                mismatched_direction.append(t)
            if decisions != [item["certified"] for item in old["levels"]]:
                mismatched_decision.append(t)
            queries_with_pass += any(decisions)
        # Score using separately propagated true-candidate mean, entirely offline.
        observed = payload-(row["b"] if t >= 50 else 0.) if sent else center
        posterior = prior+K*(observed-prior[0])
        prior = A@posterior+B@([.15, .05] if t % 120 < 60 else [.08, .05])
        contamination = fast.monitor-posterior
        for m, (action, bound) in enumerate(outputs):
            hashes[m].update(np.asarray(action, dtype=">f8").tobytes())
            nonzero = bool(np.any(action))
            if m == 1:
                nonzero_m3 += nonzero
            act_diff[m] += nonzero != (row["bounds"][t][m] > 0)
            if 50 <= t <= 561:
                useful[m] += bound >= USEFUL
                useful_diff[m] += int((bound >= USEFUL) != (row["bounds"][t][m] >= USEFUL))
            if nonzero:
                checked += 1
                actual_gain = 2*contamination@action-action@action
                max_risk_shortfall = max(max_risk_shortfall, bound-actual_gain)
                violations += int(bound-actual_gain > 1e-10)
                gain_negative += int(actual_gain < -1e-10)
    return dict(id=row["id"], group=row["group"], checked=checked, violations=violations,
                negative_gain_actions=gain_negative, max_shortfall=max_risk_shortfall,
                nonzero_m3=nonzero_m3, issued_queries=queries_with_pass,
                direction_mismatches=mismatched_direction, decision_mismatches=mismatched_decision,
                useful=[int(v) for v in useful], useful_mismatches=useful_diff,
                activity_mismatches=act_diff,
                hash_matches=[h.hexdigest()==row["actions_sha256"][m] for h,m in zip(hashes, ("M2","M3"))])


def timed(path):
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(ROOT / "code"))
    from experiment import D, Methods
    from engine import elementary_cache, trigger_cache
    reg = json.loads((ROOT / "registration.json").read_text())
    row = json.loads(path.read_text())
    frames = row["public"]
    ident = row["id"]
    results, vectors = {}, {}
    for method in (("M3-Exact","M3-Fast") if row["index"]==0 else ("M3-Fast","M3-Exact")):
        def initialize():
            return Fast() if method=="M3-Fast" else Methods(D(reg["strong"]), reg["threshold"], "M3")
        warm = initialize()
        for frame in frames[:8]:
            warm.step(frame)
        elementary_cache.cache_clear()
        trigger_cache.cache_clear()
        hash_act = hashlib.sha256()
        outputs = np.empty((len(frames), 2))
        queries = []
        w, c = perf_counter(), process_time()
        online = initialize()
        for frame in frames:
            ans = online.step(frame)
            if method == "M3-Fast":
                a = ans[0][1][0]
                if ans[1] is not None:
                    queries.append(ans[1][2])
            else:
                a = ans[0]["M3"][0]
                if ans[1] is not None:
                    queries.append(ans[1]["seconds"])
            out = np.asarray(a,dtype=">f8")
            hash_act.update(out.tobytes())
            outputs[frame[0]] = out
        results[method] = dict(wall=perf_counter()-w, cpu=process_time()-c, query=queries)
        vectors[method] = outputs
        if method=="M3-Exact" and hash_act.hexdigest()!=row["actions_sha256"]["M3"]:
            raise ValueError("Exact action replay differs from frozen archive")
    diff = np.max(np.abs(vectors["M3-Exact"]-vectors["M3-Fast"]),axis=1)
    return dict(id=ident, methods=results, max_abs_action_difference=float(diff.max()),
                count_action_difference_gt_1e_10=int(np.sum(diff>1e-10)), steps=len(diff))


def dump(name, obj):
    buf = HERE/(name+".tmp")
    buf.write_text(json.dumps(obj, indent=2, allow_nan=False, ensure_ascii=False)+"\n",encoding="utf8")
    buf.replace(HERE/name)


if __name__=="__main__":
    parse = argparse.ArgumentParser(description=__doc__)
    parse.add_argument("mode", choices=["audit","timing"])
    args = parse.parse_args()
    if args.mode=="timing":
        files = [ROOT/"results/confirmation"/f"strong_{sign}-{i:02d}.json"
                 for sign in ("positive","negative") for i in (0,1)]
        run = timed
    else:
        files = sorted((ROOT/"results/confirmation").glob("*.json"))
        files += sorted((ROOT/"supplement/results/transition").glob("*.json"))
        run = audit
    with ProcessPoolExecutor(4) as pool:
        records = list(pool.map(run, files))
    dump(args.mode+".json", dict(python=sys.version, numpy=np.__version__, scipy=scipy.__version__,
                                  platform=platform.platform(), records=records))
