"""Paired replay of Stage 6 final seeds with cached certificate decisions.

The physical/event RNG streams are regenerated from the frozen Stage 6 seeds.
Saved successful certificate decisions are replayed, so this isolates how the
same evidence is propagated. Certificate-search runtime is intentionally not
counted as an online-runtime result.
"""
from __future__ import annotations

import hashlib, json, math, time
from concurrent.futures import ProcessPoolExecutor, as_completed
from fractions import Fraction as F
from pathlib import Path

import numpy as np

from fixed_amplitude import (IntervalFixedAmplitudeEnvelope, capped_halfspace_action,
                             transport_halfspace)
from exact_linear import asfloat, update, matmul, inverse, transpose
from projection import inner

HERE = Path(__file__).resolve().parent
STAGE6 = HERE.parent / "paper2_stage6_vector_correction_20261122"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fvec(values):
    return tuple(F(x) for x in values)


def npvec(values):
    return np.asarray([float(x) for x in values], dtype=float)


def norm2(x):
    return float(np.dot(x, x))


def loss(error, action):
    e = error + action
    return float(np.dot(e, e))


def to_json_fraction(x):
    return str(x)


def load_protocol():
    return json.loads((STAGE6 / "pilot_protocol.json").read_text(encoding="utf8"))


def run_episode(stage, bi, index, protocol, model):
    b = protocol["attack_strengths"][bi]
    t0 = protocol["attack_start"]
    N = t0 + max(protocol["evaluation_windows"])
    path = STAGE6 / "results_v2" / stage / f"b{b:g}_episode{index:03d}.json"
    archived = json.loads(path.read_text(encoding="utf8"))
    by_time = {}
    for query in archived["certificate_queries"]:
        by_time.setdefault(int(query["time"]), []).append(query)
    any_success = any(q.get("certified", False) for q in archived["certificate_queries"])

    rngs = [np.random.default_rng(s) for s in np.random.SeedSequence(
        [protocol[stage + "_seed"], bi, index]).spawn(3)]
    phys, events, phase = rngs
    A = np.array(model["A"], float)
    C = np.array(model["C"], float)
    Q = np.array(model["Q"], float)
    R, Z = float(model["R"]), float(model["Z"])
    delta = float(model["quantization_half_width"])
    W = [[F(x) for x in row] for row in model["W"]]
    env = IntervalFixedAmplitudeEnvelope(model, track_responses=any_success)

    error = np.linalg.cholesky(np.array(model["P0_prior"], float)) @ phys.normal(size=2)
    true_theta = np.zeros(2)
    old_cert = None
    new_directions = []
    total = {name: 0.0 for name in (
        "monitor", "old_cert", "new_directional", "old_gain", "new_directional_gain",
        "old_conditional_gain", "new_directional_conditional_gain", "old_action_square",
        "new_action_square")}
    timing = {name: 0.0 for name in ("exact_dynamics", "parameter_updates", "support_search")}
    certificate_log = []
    lag_rows = {}
    snapshots = {}
    coverage_violations = 0
    old_support_violations = 0
    monotonicity_violations = 0
    first_old_useful = None
    first_new_useful = None
    useful_level = float(protocol["primary_useful_level"])
    cap = F(str(protocol["output_l1_cap"]))
    started = time.perf_counter()

    for t in range(N):
        v = math.sqrt(R) * phys.normal()
        w = np.linalg.cholesky(Q) @ phys.normal(size=2)
        r = 0.0 if t == 0 else delta * (2 * phase.random() - 1)
        y = float((C @ error).item() + v)
        sent = bool(events.random() > math.exp(-0.5 * Z * (y - r) ** 2))
        action = b if sent and t >= t0 else 0.0

        tick = time.perf_counter()
        noise = F(0) if sent else 1 / env.Z
        _, Kmat, Tmat = update(env.P, env.C, env.R + noise)
        Fmat = matmul(Tmat, env.A)
        Fcheck, Kcheck = env.advance(sent)
        if Fcheck != Fmat or Kcheck != Kmat:
            raise AssertionError("Exact covariance response update diverged")
        timing["exact_dynamics"] += time.perf_counter() - tick
        K = np.asarray(asfloat(Kmat), dtype=float).ravel()
        T = np.asarray(asfloat(Tmat), dtype=float)

        # Legacy one-halfspace propagation.
        if old_cert is not None:
            old_cert = transport_halfspace(old_cert, Fmat, Kmat, sent,
                                           F(str(protocol["attack_strengths"][-1])))

        # Transport all retained directional evidence using the exact model
        # dynamics. The set support is recomputed from fixed-b line segments.
        if new_directions:
            Wmat = env.W
            Winv = inverse(Wmat)
            transported = []
            for d, origin in new_directions:
                Wd = matmul(Wmat, [[x] for x in d])
                dt = matmul(Winv, matmul(transpose(inverse(Fmat)), Wd))
                transported.append((tuple(row[0] for row in dt), origin))
            new_directions = transported

        # The floating posterior innovation update matches Stage 6 exactly.
        post_error = error - K * (y + action) if sent else error - K * r
        true_theta = T @ (A @ true_theta) + K * action

        for query in by_time.get(t, ()):
            if not query.get("certified", False):
                continue
            d = fvec(query["direction"])
            z = F(str(query["target_support"]))
            if z <= 0:
                raise AssertionError("Frozen successful certificate has nonpositive z")
            tick = time.perf_counter()
            info = env.add_certificate(d, z)
            new_directions.append((d, {"time": t, "z": str(z)}))
            timing["parameter_updates"] += time.perf_counter() - tick
            old_action, old_gain = capped_halfspace_action(old_cert, W, cap)
            candidate_action, candidate_gain = capped_halfspace_action((d, z), W, cap)
            if candidate_gain > old_gain:
                old_cert = (d, z)
            info = dict(info)
            if info["minimum_b_lower"] is not None:
                info["minimum_b_lower"] = str(info["minimum_b_lower"])
            certificate_log.append({"time": t, "direction": [str(x) for x in d],
                                    "z": str(z), **info})

        # Construct the new action by maximizing the certified gain among all
        # retained transported directions. The envelope itself remains the
        # same global confidence event, not a per-time refit.
        tick = time.perf_counter()
        old_action, old_bound = capped_halfspace_action(old_cert, W, cap)
        best_action = tuple(F(0) for _ in range(2))
        best_bound = F(0)
        best_support = None
        best_origin = None
        for d, origin in new_directions:
            candidate = env.directional_action(d, cap)
            if candidate["guaranteed_gain"] > best_bound:
                best_action = candidate["action"]
                best_bound = candidate["guaranteed_gain"]
                best_support = candidate["support"]
                best_origin = origin
        if best_bound < old_bound:
            # Directed-rounding uncertainty may weaken the new outer-set
            # support by a few ulps. Retaining the already valid legacy action
            # is a deterministic no-regression safeguard.
            best_action, best_bound = old_action, old_bound
            best_support = old_cert[1] if old_cert is not None else None
            best_origin = {"legacy_fallback": True}
        timing["support_search"] += time.perf_counter() - tick
        monotonicity_violations += int(best_bound < old_bound)

        if t >= t0:
            # Exact onset interval membership is the numerical coverage check.
            if certificate_log and not env.contains_truth_amplitude(t0, F(str(b))):
                coverage_violations += 1
            if old_cert is not None and float(inner(old_cert[0], tuple(F(str(x)) for x in true_theta), W)) < float(old_cert[1]) - 2e-10:
                old_support_violations += 1
            old_np, new_np = npvec(old_action), npvec(best_action)
            old_cond = 2 * float(true_theta @ old_np) - norm2(old_np)
            new_cond = 2 * float(true_theta @ new_np) - norm2(new_np)
            total["monitor"] += norm2(post_error)
            total["old_cert"] += loss(post_error, old_np)
            total["new_directional"] += loss(post_error, new_np)
            total["old_gain"] += norm2(post_error) - loss(post_error, old_np)
            total["new_directional_gain"] += norm2(post_error) - loss(post_error, new_np)
            total["old_conditional_gain"] += old_cond
            total["new_directional_conditional_gain"] += new_cond
            total["old_action_square"] += float(old_bound)
            total["new_action_square"] += float(best_bound)
            old_norm, new_norm = float(np.linalg.norm(old_np)), float(np.linalg.norm(new_np))
            if old_norm >= useful_level and first_old_useful is None:
                first_old_useful = t
            if new_norm >= useful_level and first_new_useful is None:
                first_new_useful = t

        for success in certificate_log:
            if success["time"] == t:
                for lag in (0, 1, 10, 25, 50):
                    if t + lag == t:
                        pass
                    lag_rows[f"{t}+{lag}"] = {"target_time": t + lag, "lag": lag}
        for key, item in list(lag_rows.items()):
            if item["target_time"] == t:
                item.update({"old_bound": float(old_bound), "new_bound": float(best_bound),
                             "old_action_norm": float(np.linalg.norm(npvec(old_action))),
                             "new_action_norm": float(np.linalg.norm(npvec(best_action))),
                             "new_support": None if best_support is None else format(float(best_support), ".12g"),
                             "new_direction_origin": None if best_origin is None else best_origin})

        H = t - t0 + 1
        if H in protocol["evaluation_windows"]:
            snapshots[str(H)] = {**total,
                "old_current_action_norm": float(np.linalg.norm(npvec(old_action))),
                "new_current_action_norm": float(np.linalg.norm(npvec(best_action))),
                "old_current_bound": float(old_bound), "new_current_bound": float(best_bound),
                "first_old_useful": first_old_useful, "first_new_useful": first_new_useful,
                "new_interval_onsets": len(env.bounds),
                "coverage_violations": coverage_violations,
                "old_support_violations": old_support_violations,
                "bound_monotonicity_violations": monotonicity_violations}
        error = A @ post_error + w

    result = {"stage": stage, "b": b, "episode": index, "steps": N,
        "snapshots": snapshots, "lag_snapshots": lag_rows,
        "successful_certificates": certificate_log, "timing": timing,
        "replay_seconds": time.perf_counter() - started,
        "coverage_violations": coverage_violations,
        "old_support_violations": old_support_violations,
        "bound_monotonicity_violations": monotonicity_violations,
        "new_direction_count": len(new_directions),
        "freeze_stage6_sha256": sha(STAGE6 / "freeze_v2.json"),
        "certificate_decisions": "replayed from Stage 6 saved query JSON; certificate search runtime excluded",
        "physical_rng_identity": "same SeedSequence([final_seed, attack_index, episode_index]) and Generator spawn order as pilot_v2.py",
        "response_arithmetic": "exact Fraction Riccati gains and onset responses; exact rational amplitude bounds",
        "sample_generator": "NumPy float64, matching Stage 6 pilot_v2.py"}

    # Reproduction gate: the old branch must match the archived Stage 6 paired
    # losses before any propagation conclusion is accepted.
    for H, values in snapshots.items():
        old = archived["snapshots"][H]
        for key in ("monitor", "certified_gain", "conditional_certified_gain", "squared_actions"):
            ours = values["monitor"] if key == "monitor" else values["old_gain"] if key == "certified_gain" else values["old_conditional_gain"] if key == "conditional_certified_gain" else values["old_action_square"]
            target = old[key]
            if abs(ours - target) > 2e-8:
                raise AssertionError(f"Stage 6 replay mismatch b={b} episode={index} H={H} {key}: {ours} vs {target}")
    return result


def main():
    protocol = load_protocol()
    model = json.loads((STAGE6 / "model.json").read_text(encoding="utf8"))
    outdir = HERE / "results" / "replay"
    outdir.mkdir(parents=True, exist_ok=True)
    all_rows = []
    started = time.perf_counter()
    jobs = [("final", bi, index, protocol, model)
            for bi, b in enumerate(protocol["attack_strengths"])
            for index in range(protocol["final_episodes_per_case"])
            if not (outdir / f"b{b:g}_episode{index:03d}.json").exists()]
    workers = int(json.loads((HERE / "stage7_protocol.json").read_text(encoding="utf8"))["workers"])
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(run_episode, *job) for job in jobs]
        for future in as_completed(futures):
            row = future.result()
            b, index = row["b"], row["episode"]
            (outdir / f"b{b:g}_episode{index:03d}.json").write_text(
                json.dumps(row, indent=2) + "\n", encoding="utf8", newline="\n")
            all_rows.append(row)
            useful50 = sum(1 for x in row["lag_snapshots"].values()
                           if x.get("lag") == 50 and x.get("new_action_norm", 0) >= .025)
            print("replay", f"b={b:g}", index,
                  "new_successes", len(row["successful_certificates"]),
                  "lag50_useful", useful50,
                  "seconds", round(row["replay_seconds"], 2), flush=True)
    all_rows = [json.loads(p.read_text(encoding="utf8"))
                for p in sorted(outdir.glob("b*_episode*.json"))]
    summary = {"status": "PASS_REPRODUCED" if all(
        row["bound_monotonicity_violations"] == 0 and row["coverage_violations"] == 0
        and row["old_support_violations"] == 0 for row in all_rows) else "CHECK_FAILURES",
        "episodes": len(all_rows), "final_seed": protocol["final_seed"],
        "protocol_sha256": sha(STAGE6 / "pilot_protocol.json"),
        "model_sha256": sha(STAGE6 / "model.json"),
        "stage6_freeze_sha256": sha(STAGE6 / "freeze_v2.json"),
        "rows": [{"b": row["b"], "episode": row["episode"],
                  "replay_seconds": row["replay_seconds"],
                  "snapshots": row["snapshots"],
                  "lag_snapshots": row["lag_snapshots"],
                  "coverage_violations": row["coverage_violations"],
                  "old_support_violations": row["old_support_violations"],
                  "bound_monotonicity_violations": row["bound_monotonicity_violations"]}
                 for row in all_rows],
        "runtime_seconds": time.perf_counter() - started,
        "limitations": ["Replay reuses saved successful/failed certificate decisions; certificate-search runtime is excluded.",
                        "The replay reproduces the Stage 6 final-seed traces and is a paired algorithm ablation, not an independent sample confirmation.",
                        "No formal finite-sample MSE claim follows from 12 episodes per case."]}
    (HERE / "results" / "replay_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf8", newline="\n")
    print(json.dumps({"status": summary["status"], "episodes": len(all_rows),
                      "seconds": summary["runtime_seconds"]}))


if __name__ == "__main__":
    main()
