"""Locked independent-seed run including full likelihood certification."""
from __future__ import annotations
import os
for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[key] = "1"

import hashlib, json, math, time
from concurrent.futures import ProcessPoolExecutor, as_completed
from fractions import Fraction as F
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
STAGE6 = HERE.parent / "paper2_stage6_vector_correction_20261122"
import sys
sys.path.insert(0, str(STAGE6))

from vector_record import VectorRecord, I, D
from exact_linear import update, matmul, asfloat
from fixed_amplitude import transport_halfspace, capped_halfspace_action
from direction_cache_corrected import CorrectedFastEnvelope
import pilot_v2 as stage6_pilot


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf8"))


def verify_frozen():
    freeze = load_json(HERE / "fresh_confirmation_freeze.json")
    for name, digest in freeze["stage7_sources"].items():
        if sha(HERE / name) != digest:
            raise RuntimeError("Frozen Stage 7 source changed: " + name)
    for name, digest in freeze["stage6_inputs"].items():
        if sha(STAGE6 / name) != digest:
            raise RuntimeError("Stage 6 input changed: " + name)


def exact_mid(box):
    from decimal import localcontext
    with localcontext() as ctx:
        ctx.prec = 50
        return (box.lo + box.hi) / 2


def run_one(bi, index):
    verify_frozen()
    protocol = load_json(HERE / "fresh_protocol.json")
    model = load_json(STAGE6 / "model.json")
    b = protocol["attack_strengths"][bi]
    t0 = protocol["attack_start"]
    N = t0 + max(protocol["evaluation_windows"])
    output_path = HERE / "results" / "fresh_confirmation" / f"b{b:g}_episode{index:03d}.json"
    if output_path.exists():
        raise RuntimeError("Fresh confirmation output already exists")
    rngs = [np.random.default_rng(s) for s in np.random.SeedSequence(
        [protocol["seed"], bi, index]).spawn(3)]
    phys, events, phase = rngs
    A = np.array(model["A"], float)
    C = np.array(model["C"], float)
    Q = np.array(model["Q"], float)
    R, Z = float(model["R"]), float(model["Z"])
    delta = float(model["quantization_half_width"])
    W = [[F(x) for x in row] for row in model["W"]]
    record = VectorRecord(model)
    envelope = CorrectedFastEnvelope(model)
    error = np.linalg.cholesky(np.array(model["P0_prior"], float)) @ phys.normal(size=2)
    true_theta = np.zeros(2)
    old_cert = None
    new_directions = []
    total = {name: 0.0 for name in (
        "monitor", "old", "new", "old_gain", "new_gain", "old_conditional",
        "new_conditional", "old_gcert", "new_gcert")}
    timing = {name: 0.0 for name in (
        "record_and_likelihood_state", "response_and_direction_cache",
        "direction_proposal", "certificate_search", "support_and_output")}
    queries, successful, lag_rows, snapshots = [], [], {}, {}
    first_old_useful = first_new_useful = None
    coverage_violations = old_support_violations = monotonicity_violations = 0
    cap = F(str(protocol["output_l1_cap"]))
    useful = protocol["primary_useful_level"]
    started = time.perf_counter()

    for t in range(N):
        v = math.sqrt(R) * phys.normal()
        w = np.linalg.cholesky(Q) @ phys.normal(size=2)
        r = 0.0 if t == 0 else delta * (2 * phase.random() - 1)
        y = float((C @ error).item() + v)
        sent = bool(events.random() > math.exp(-.5 * Z * (y-r)**2))
        attack_input = b if sent and t >= t0 else 0.0

        prior = record.P
        noise = F(0) if sent else 1 / F(model["Z"])
        _, Kmat, Tmat = update(prior, record.C, record.R + noise)
        Fmat = matmul(Tmat, record.A)
        tick = time.perf_counter()
        Fcheck, Kcheck = envelope.advance(sent)
        if Fcheck != Fmat or Kcheck != Kmat:
            raise AssertionError("Record and response covariance recursions diverged")
        if old_cert is not None:
            old_cert = transport_halfspace(old_cert, Fmat, Kmat, sent,
                                           F(str(protocol["attack_strengths"][-1])))
        if new_directions:
            from exact_linear import inverse, transpose
            transported = []
            for d, origin in new_directions:
                Wd = matmul(envelope.W, [[x] for x in d])
                moved = matmul(inverse(envelope.W), matmul(transpose(inverse(Fmat)), Wd))
                transported.append((tuple(row[0] for row in moved), origin))
            new_directions = transported
        timing["response_and_direction_cache"] += time.perf_counter() - tick

        tick = time.perf_counter()
        record.append(sent, None if not sent else repr(float(y + attack_input)), repr(float(r)))
        timing["record_and_likelihood_state"] += time.perf_counter() - tick
        K = np.asarray(asfloat(Kmat), dtype=float).ravel()
        T = np.asarray(asfloat(Tmat), dtype=float)
        post_error = error - K * (y + attack_input) if sent else error - K * r
        true_theta = T @ (A @ true_theta) + K * attack_input

        if t in protocol["certification_times"]:
            tick = time.perf_counter()
            direction, point_estimate, b_est = stage6_pilot.choose_point(
                record, protocol["point_estimator_grid"])
            timing["direction_proposal"] += time.perf_counter() - tick
            if direction is not None:
                for level in protocol["certificate_levels"]:
                    scale = sum(abs(x) for x in direction)
                    target_fraction = F(str(level)) * scale
                    from decimal import localcontext
                    with localcontext() as ctx:
                        ctx.prec = 50
                        target = D(target_fraction.numerator) / D(target_fraction.denominator)
                    tick = time.perf_counter()
                    result = record.certify_direction(
                        direction, str(target), epsilon=str(protocol["confidence_failure"]),
                        max_nodes=protocol["max_refinement_nodes_per_query"])
                    timing["certificate_search"] += time.perf_counter() - tick
                    queries.append({"time": t, "level": level,
                                    "direction": [str(x) for x in direction], **result})
                    if result["certified"]:
                        d = tuple(F(x) for x in direction)
                        z = F(str(result["target_support"]))
                        if z <= 0:
                            raise AssertionError("Nonpositive successful certificate")
                        info = envelope.add_certificate(d, z)
                        if info["minimum_b_lower"] is not None:
                            info["minimum_b_lower"] = str(info["minimum_b_lower"])
                        new_directions.append((d, {"time": t, "z": str(z)}))
                        candidate_action, candidate_gain = capped_halfspace_action((d,z), W, cap)
                        _, old_gain = capped_halfspace_action(old_cert, W, cap)
                        if candidate_gain > old_gain:
                            old_cert = (d,z)
                        successful.append({"time": t, "level": level,
                                           "direction": [str(x) for x in d],
                                           "z": str(z), **info})
                    else:
                        break

        tick = time.perf_counter()
        old_action, old_bound = capped_halfspace_action(old_cert, W, cap)
        best_action = tuple(F(0) for _ in range(2))
        best_bound = F(0)
        best_support = None
        best_origin = None
        for d, origin in new_directions:
            candidate = envelope.directional_action(d, cap)
            if candidate["guaranteed_gain"] > best_bound:
                best_action = candidate["action"]
                best_bound = candidate["guaranteed_gain"]
                best_support = candidate["support"]
                best_origin = origin
        if best_bound < old_bound:
            best_action, best_bound = old_action, old_bound
            best_support = old_cert[1] if old_cert is not None else None
            best_origin = {"legacy_fallback": True}
        monotonicity_violations += int(best_bound < old_bound)
        timing["support_and_output"] += time.perf_counter() - tick

        if t >= t0:
            if successful and not envelope.contains_truth_amplitude(t0, F(str(b))):
                coverage_violations += 1
            if old_cert is not None and float(sum((old_cert[0][i] *
                    sum((W[i][j] * F(str(true_theta[j])) for j in range(2)), F(0))
                    for i in range(2)), F(0))) < float(old_cert[1]) - 2e-10:
                old_support_violations += 1
            old_np = np.asarray([float(x) for x in old_action])
            new_np = np.asarray([float(x) for x in best_action])
            old_cond = 2 * float(true_theta @ old_np) - float(old_np @ old_np)
            new_cond = 2 * float(true_theta @ new_np) - float(new_np @ new_np)
            old_loss = float((post_error + old_np) @ (post_error + old_np))
            new_loss = float((post_error + new_np) @ (post_error + new_np))
            monitor_loss = float(post_error @ post_error)
            total["monitor"] += monitor_loss
            total["old"] += old_loss
            total["new"] += new_loss
            total["old_gain"] += monitor_loss - old_loss
            total["new_gain"] += monitor_loss - new_loss
            total["old_conditional"] += old_cond
            total["new_conditional"] += new_cond
            total["old_gcert"] += float(old_bound)
            total["new_gcert"] += float(best_bound)
            if np.linalg.norm(old_np) >= useful - 1e-12 and first_old_useful is None:
                first_old_useful = t
            if np.linalg.norm(new_np) >= useful - 1e-12 and first_new_useful is None:
                first_new_useful = t

        for cert in successful:
            if cert["time"] == t:
                for lag in (0,1,10,25,50):
                    lag_rows[f"{t}+{lag}"] = {"target_time":t+lag,"lag":lag}
        for item in lag_rows.values():
            if item["target_time"] == t:
                item.update({"old_bound":float(old_bound),"new_bound":float(best_bound),
                             "old_action_norm":float(np.linalg.norm(np.asarray([float(x) for x in old_action]))),
                             "new_action_norm":float(np.linalg.norm(np.asarray([float(x) for x in best_action]))),
                             "new_support":None if best_support is None else format(float(best_support),".12g"),
                             "direction_origin":best_origin})

        H = t - t0 + 1
        if H in protocol["evaluation_windows"]:
            snapshots[str(H)] = {**total,
                "old_current_action_norm":float(np.linalg.norm(np.asarray([float(x) for x in old_action]))),
                "new_current_action_norm":float(np.linalg.norm(np.asarray([float(x) for x in best_action]))),
                "old_current_bound":float(old_bound),"new_current_bound":float(best_bound),
                "first_old_useful":first_old_useful,"first_new_useful":first_new_useful,
                "retained_onsets":len(envelope.bounds),"coverage_violations":coverage_violations,
                "old_support_violations":old_support_violations,
                "bound_monotonicity_violations":monotonicity_violations}
        error = A @ post_error + w

    row = {"b":b,"episode":index,"seed":protocol["seed"],"steps":N,
           "snapshots":snapshots,"lag_snapshots":lag_rows,"certificate_queries":queries,
           "successful_certificates":successful,"timing":timing,
           "total_seconds":time.perf_counter()-started,
           "coverage_violations":coverage_violations,
           "old_support_violations":old_support_violations,
           "bound_monotonicity_violations":monotonicity_violations,
           "numerics":"exact rational covariance/gains; outward Decimal interval response/amplitude bounds; float64 physical stream",
           "full_certificate_search":True,"confidence_failure":protocol["confidence_failure"],
           "freeze_sha256":sha(HERE/"fresh_confirmation_freeze.json")}
    output_path.parent.mkdir(parents=True,exist_ok=True)
    output_path.write_text(json.dumps(row,indent=2)+"\n",encoding="utf8",newline="\n")
    return row


def main():
    verify_frozen()
    protocol=load_json(HERE/"fresh_protocol.json")
    model=load_json(STAGE6/"model.json")
    outdir=HERE/"results"/"fresh_confirmation"
    jobs=[(bi,i) for bi,b in enumerate(protocol["attack_strengths"])
          for i in range(protocol["episodes_per_case"])
          if not (outdir/f"b{b:g}_episode{i:03d}.json").exists()]
    start=time.perf_counter();rows=[]
    with ProcessPoolExecutor(max_workers=protocol["workers"]) as pool:
        futures=[pool.submit(run_one,bi,i) for bi,i in jobs]
        for future in as_completed(futures):
            row=future.result();rows.append(row)
            print("fresh",f"b={row['b']:g}",row["episode"],
                  "certs",len(row["successful_certificates"]),
                  "new_gain512",round(row["snapshots"]["512"]["new_gain"],6),
                  "seconds",round(row["total_seconds"],2),flush=True)
    rows=[load_json(p) for p in sorted(outdir.glob("b*_episode*.json"))]
    failures=[(r["b"],r["episode"]) for r in rows if
              r["coverage_violations"] or r["old_support_violations"] or r["bound_monotonicity_violations"]]
    result={"status":"PASS" if len(rows)==36 and not failures else "CHECK_FAILURES",
            "episodes":len(rows),"failures":failures,"seed":protocol["seed"],
            "runtime_seconds":time.perf_counter()-start,
            "full_certificate_search":True,"independent_of_stage6_final_seeds":True}
    (HERE/"results"/"fresh_confirmation_completion.json").write_text(
        json.dumps(result,indent=2)+"\n",encoding="utf8",newline="\n")
    print(json.dumps(result,indent=2))


if __name__=="__main__":main()
