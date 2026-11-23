"""Frozen, paired evaluation of output-only recovery for the V2 model."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time

for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[key] = "1"
import numpy as np
from scipy.stats import t as student_t

HERE = Path(__file__).resolve().parent
REVIEWS = HERE.parent
STAGE4 = REVIEWS / "paper2_stage4_certified_correction_20261122"
STAGE5 = REVIEWS / "paper2_stage5_certification_acceleration_20261122"
STAGE6 = REVIEWS / "paper2_stage6_vector_correction_20261122"
STAGE7 = REVIEWS / "paper2_stage7_fixed_amplitude_20261122"
STAGE8 = REVIEWS / "paper2_stage8_restricted_certification_20261123"
AUDIT = REVIEWS / "paper2_stage7_output_audit_20261123"
for path in (STAGE4, STAGE5, STAGE6, STAGE7, STAGE8, AUDIT):
    sys.path.insert(0, str(path))

from cumulative_envelope import CertifiedParameterEnvelope, EvidenceRecord
from direction_cache_corrected import CorrectedFastEnvelope
from exact_linear import asfloat, inverse, matmul, transpose, update
from fixed_amplitude import capped_halfspace_action, transport_halfspace
from interval_arithmetic import Interval as I
from pilot_v2 import choose_point
from projection import inner
from restricted_certification import certify_direction_restricted


def read(path):
    return json.loads(path.read_text(encoding="utf8"))


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n",
                    encoding="utf8", newline="\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inputs(protocol):
    names = {
        HERE: ("paired_recovery.py", "cumulative_envelope.py", "check_stage9.py",
               "stage9_protocol.json", "stage9_checks.json"),
        STAGE4: ("interval_arithmetic.py",),
        STAGE5: ("strong_concavity.py",),
        STAGE6: ("model.json", "vector_record.py", "exact_linear.py", "projection.py", "pilot_v2.py"),
        STAGE7: ("fixed_amplitude.py", "direction_cache_corrected.py", "fresh_protocol.json"),
        STAGE8: ("restricted_certification.py",),
    }
    paths = [root / name for root, files in names.items() for name in files]
    paths += [source_path(index) for index in protocol["episode_indices"]]
    return {path.relative_to(REVIEWS).as_posix(): sha(path) for path in paths}


def source_path(index):
    return STAGE7 / "results" / "fresh_confirmation" / f"b0.25_episode{index:03d}.json"


def freeze(protocol, mode):
    path = HERE / f"{mode}_freeze.json"
    if mode == "fresh":
        replay = HERE / "replay_summary.json"
        if not replay.exists():
            raise RuntimeError("Complete the frozen replay before the independent experiment")
        prerequisite = sha(replay)
    else:
        prerequisite = None
    value = {"mode": mode, "inputs": inputs(protocol), "replay_results_sha256": prerequisite,
             "python": sys.version, "numpy": np.__version__,
             "scipy": __import__("scipy").__version__}
    if path.exists() and read(path) != value:
        raise RuntimeError(f"Frozen {mode} inputs have changed")
    if not path.exists():
        write(path, value)
    return sha(path)


class Restorer:
    """Use the same directional output cache for both parameter enclosures."""

    def __init__(self, model, version, config):
        self.cache = CorrectedFastEnvelope(model, track_responses=False)
        self.core = None
        self.version = version
        self.config = config
        self.halfspace = None
        self.envelope = None
        self.has_certificate = False
        self.cap = F(config["output_l1_cap"])
        self.bmax = F(model["attack_amplitude_cap"])
        self.time = {"advance": 0., "query": 0., "commit": 0., "output": 0.}
        self.count = {"likelihood": 0, "suffix_terms": 0, "query_boxes": 0,
                      "increment_updates": 0, "increment_log_calls": 0}

    def advance(self, record, sent, Fmat, K):
        tick = time.perf_counter()
        self.core = record.core
        if self.has_certificate:
            # Existing cache needs only F and K. Supply them through its two-state recurrence.
            assert self.cache.advance(sent) == (Fmat, K)
        else:
            self.cache.P = record.core.P
            self.cache.time = record.time
        if self.envelope is not None:
            self.envelope.advance(record)
            self._sync_intervals()
        self.halfspace = transport_halfspace(self.halfspace, Fmat, K, sent, self.bmax)
        self.time["advance"] += time.perf_counter() - tick

    def _sync_intervals(self):
        # For fixed k a linear support depends only on the extreme amplitudes.
        # The full list of components still enters the likelihood search.
        self.cache.bounds = {k: (F(items[0][0]), F(items[-1][1]))
                             for k, items in self.envelope.confidence_intervals().items()}
        self._prune_direction_cache()

    def _prune_direction_cache(self):
        for state in self.cache.direction_cache.values():
            state["q_lower"] = {k: state["q_lower"][k] for k in self.cache.bounds}

    def search(self, record, direction, z, bounds8):
        tick = time.perf_counter()
        before = record.core.stats.copy()
        budget = self.config["max_refinement_nodes"]
        if self.version == 9 and self.envelope is not None:
            result, cert = self.envelope.certify_direction(record, direction, z, max_nodes=budget)
        elif self.version == 8 and bounds8:
            with localcontext() as context:
                context.prec = 50
                target = D(z.numerator) / D(z.denominator)
            if F(target) != z:
                raise ValueError("Frozen query targets must have exact finite decimal representations")
            result = certify_direction_restricted(
                self.core, direction, str(target), bounds8,
                epsilon=record.epsilon, bmax=record.amplitude_cap, max_nodes=budget)
            cert = (direction, z) if result["certified"] else None
        else:
            result, issued = record.certify_full(direction, z, max_nodes=budget)
            cert = issued if self.version == 9 else ((issued.direction, issued.support) if issued else None)
        after = record.core.stats
        seconds = time.perf_counter() - tick
        evaluations = after["likelihood_evaluations"] - before["likelihood_evaluations"]
        suffix_terms = after["suffix_trigger_evaluations"] - before["suffix_trigger_evaluations"]
        boxes = result.get("boxes_tested", result.get(
            "segments_tested", after["segments_tested"] - before["segments_tested"]))
        self.time["query"] += seconds
        self.count["likelihood"] += evaluations
        self.count["suffix_terms"] += suffix_terms
        self.count["query_boxes"] += boxes
        return {"certified": result["certified"], "reason": result["reason"],
                "gain": result.get("guaranteed_gain", "0"), "seconds": seconds,
                "likelihood_calls": evaluations, "suffix_terms": suffix_terms,
                "boxes": boxes, "subdivisions": result["nodes"],
                "source_envelope_id": result.get("source_envelope_id")}, cert

    def accept(self, record, certificates):
        tick = time.perf_counter()
        before = self.core.stats["likelihood_evaluations"]
        for cert in certificates:
            if self.version == 9:
                if self.envelope is None:
                    self.envelope = CertifiedParameterEnvelope.start(
                        record, cert, refinement_budget=self.config["envelope_refinement_budget"],
                        refinement_tolerance=self.config["envelope_refinement_tolerance"])
                else:
                    self.envelope.apply_certificate(record, cert)
                self._sync_intervals()
                d, z = cert.direction, cert.support
            else:
                d, z = cert
                candidates = self.cache.bounds.keys() if self.has_certificate else range(self.core.n)
                kept = {}
                for k in candidates:
                    coefficient = self.core.support_coefficient(k, d).hi
                    if coefficient <= 0:
                        continue
                    lo = F((I.exact(z.numerator) / I.exact(z.denominator) / I.exact(coefficient)).lo)
                    lo = max(lo, self.cache.bounds.get(k, (F(0), self.bmax))[0])
                    if lo <= self.bmax:
                        kept[k] = (lo, self.bmax)
                self.cache.bounds = kept
            self.has_certificate = True
            if d not in self.cache.direction_cache:
                self.cache.direction_cache[d] = {
                    "d": d, "q_lower": {k: self.core.support_coefficient(k, d).lo for k in self.cache.bounds}}
            self._prune_direction_cache()
            _, old_gain = capped_halfspace_action(self.halfspace, self.core.W, self.cap)
            _, new_gain = capped_halfspace_action((d, z), self.core.W, self.cap)
            if new_gain > old_gain:
                self.halfspace = (d, z)
        self.count["likelihood"] += self.core.stats["likelihood_evaluations"] - before
        self.time["commit"] += time.perf_counter() - tick

    def audit(self, t0, b):
        if not self.has_certificate:
            return True
        if self.version == 9:
            return self.envelope.contains_parameter(t0, b)
        lo, hi = self.cache.bounds.get(t0, (F(1), F(0)))
        return lo <= b <= hi

    def domain(self):
        if not self.has_certificate:
            return {"onsets": self.core.n, "components": self.core.n,
                    "width": float(self.bmax * self.core.n)}
        if self.envelope is None:
            values = list(self.cache.bounds.values())
        else:
            values = [pair for items in self.envelope.confidence_intervals().values() for pair in items]
        return {"onsets": len(self.cache.bounds), "components": len(values),
                "width": float(sum((F(hi)-F(lo) for lo, hi in values), F(0)))}

    def output(self, monitor):
        tick = time.perf_counter()
        weight = self.core.W
        action, gain = capped_halfspace_action(self.halfspace, weight, self.cap)
        direction, support = self.halfspace or (None, None)
        for d in self.cache.direction_cache:
            candidate = self.cache.directional_action(d, self.cap)
            if candidate["guaranteed_gain"] > gain:
                action, gain = candidate["action"], candidate["guaranteed_gain"]
                direction, support = d, candidate["support"]
        gain = F(0) if self.has_certificate and not self.cache.bounds else gain
        if gain:
            # Audit the correction induced by subtracting from the actual binary64 output.
            output = tuple(float(x)-float(a) for x, a in zip(monitor, action))
            emitted = tuple(F.from_float(float(x))-F.from_float(y) for x, y in zip(monitor, output))
            rounding_error = tuple(x-y for x, y in zip(emitted, action))
            # Enclose |theta_j| using the same candidate H intervals as the likelihood.
            rho = [self.bmax * F(max(
                max(abs(self.core.candidates[k]["H"][j].lo.copy_abs()),
                    abs(self.core.candidates[k]["H"][j].hi.copy_abs()))
                for k in self.cache.bounds)) for j in range(len(action))]
            base_support = support * inner(direction, action, weight) / inner(direction, direction, weight)
            cost = sum(r * abs(sum(v*x for v, x in zip(row, rounding_error))) for r, row in zip(rho, weight))
            audited_gain = 2*(base_support-cost) - inner(emitted, emitted, weight)
            if audited_gain >= 0 and sum(map(abs, emitted)) <= self.cap:
                self.time["output"] += time.perf_counter() - tick
                return np.array([float(x) for x in emitted]), float(audited_gain)
        self.time["output"] += time.perf_counter() - tick
        return np.zeros(2), 0.0


def run_episode(mode, case, index, freeze_hash):
    config = read(HERE / "stage9_protocol.json")
    model = read(STAGE6 / "model.json")
    saved = read(source_path(index)) if mode == "replay" else None
    seed = config["replay_seed"] if saved else config["fresh_seed"]
    case_spec = config["cases"][case] if not saved else {"b": ".25", "onset": 50}
    b = F(case_spec["b"])
    t0 = case_spec["onset"]
    horizon = config["horizon"]
    steps = saved["steps"] if saved else t0+horizon
    seed_index = 2 if saved else case
    phys, events, phase = [np.random.default_rng(s) for s in
                           np.random.SeedSequence([seed, seed_index, index]).spawn(3)]
    A = np.array(model["A"], float)
    C = np.array(model["C"], float)
    Q = np.linalg.cholesky(np.array(model["Q"], float))
    error = np.linalg.cholesky(np.array(model["P0_prior"], float)) @ phys.normal(size=2)
    R, Z = math.sqrt(float(model["R"])), float(model["Z"])
    delta = float(model["quantization_half_width"])
    monitor = np.zeros(2)
    truth = np.zeros(2)
    point = np.zeros(2)
    point_b = 0.
    record = EvidenceRecord(model, config["epsilon"], model["attack_amplitude_cap"])
    methods = {version: Restorer(model, version, config) for version in (8, 9)}
    weight = np.array(model["W"], float)
    times = {"likelihood_record": 0., "point_score_and_transport": 0.,
             "gain_and_monitor_update": 0.}
    metrics = {name: {"loss":0., "conditional_gain":0., "guarantee":0., "nonzero_steps":0,
                      "first_nonzero":None, "first_useful":None, "false_steps":0,
                      "coverage_misses":0, "risk_violations":0}
               for name in ("monitor", "point", "8", "9")}
    queries, domains = [], []
    started = time.perf_counter()
    for t in range(steps):
        v = R * phys.normal()
        w = Q @ phys.normal(size=2)
        r = 0. if t == 0 else delta*(2*phase.random()-1)
        y = float((C @ error).item()+v)
        sent = bool(events.random() > math.exp(-.5*Z*(y-r)**2))
        injection = float(b) if sent and t >= t0 else 0.
        tick = time.perf_counter()
        _, Kmat, Tmat = update(record.core.P, record.core.C,
                               record.core.R + (0 if sent else 1/record.core.Z))
        Fmat = matmul(Tmat, record.core.A)
        K = np.asarray(asfloat(Kmat), dtype=float).ravel()
        T = np.asarray(asfloat(Tmat), dtype=float)
        residual = y+injection if sent else r
        post_error = error-K*residual
        monitor = monitor+K*residual
        times["gain_and_monitor_update"] += time.perf_counter()-tick
        truth = T@(A@truth)+K*injection

        tick = time.perf_counter()
        record.append(sent, repr(float(residual)) if sent else None, repr(float(r)))
        times["likelihood_record"] += time.perf_counter()-tick
        for method in methods.values():
            method.advance(record, sent, Fmat, Kmat)

        tick = time.perf_counter()
        point = np.array(asfloat(Fmat))@point+(K*point_b if sent else 0.)
        scheduled = t in config["certification_times"]
        if scheduled:
            d, point, estimate = choose_point(record.core, config["point_grid"])
            point_b = float(estimate)
        times["point_score_and_transport"] += time.perf_counter()-tick

        if scheduled and d is not None:
            if saved:
                wave = [(F(q["target_support"]), q["certified"])
                        for q in saved["certificate_queries"] if q["time"] == t]
                if any(tuple(F(x) for x in q["direction"]) != d
                       for q in saved["certificate_queries"] if q["time"] == t):
                    raise AssertionError("Saved and regenerated directions differ")
            else:
                wave = [(F(level)*sum(map(abs, d)), None) for level in config["certificate_levels"]]
            accepted = {8: [], 9: []}
            active = {8: True, 9: True}
            bounds8 = methods[8].cache.bounds.copy()
            for target, archived in wave:
                row = {"time": t, "target": str(target), "archived_success": archived}
                for version, method in methods.items():
                    if active[version]:
                        result, cert = method.search(record, d, target, bounds8)
                        row[str(version)] = result
                        if cert is not None:
                            accepted[version].append(cert)
                            if version == 9:
                                row["9"].update({"certificate_id": cert.certificate_id,
                                    "parent_certificate_ids": cert.parent_certificate_ids,
                                    "prefix_hash": cert.observation_prefix_hash})
                        elif not saved:
                            active[version] = False
                if len(row) > 3:
                    queries.append(row)
                if not any(active.values()):
                    break
            for version, method in methods.items():
                method.accept(record, accepted[version])
            domains.append({"time": t, **{str(v): m.domain() for v,m in methods.items()}})

        cap = float(config["output_l1_cap"])
        point_out = point * min(1., cap/max(cap, float(np.abs(point).sum())))
        actions = {"monitor": (np.zeros(2), 0.), "point": (point_out, 0.)}
        for version, method in methods.items():
            actions[str(version)] = method.output(monitor)
            if not method.audit(t0, b):
                metrics[str(version)]["coverage_misses"] += 1
        for name, (action, guarantee) in actions.items():
            metric = metrics[name]
            active_action = bool(np.any(action))
            if active_action:
                metric["nonzero_steps"] += 1
                if metric["first_nonzero"] is None:
                    metric["first_nonzero"] = t
                if t < t0 or not b:
                    metric["false_steps"] += 1
            if guarantee >= config["useful_risk_gain"] and metric["first_useful"] is None:
                metric["first_useful"] = t
            if t >= t0:
                recovered = post_error+action
                metric["loss"] += float(recovered@weight@recovered)
                conditional = float(2*truth@weight@action-action@weight@action)
                metric["conditional_gain"] += conditional
                metric["guarantee"] += guarantee
                if name in ("8", "9") and conditional+1e-10 < guarantee:
                    metric["risk_violations"] += 1
        error = A@post_error+w
        tick = time.perf_counter()
        monitor = A@monitor
        times["gain_and_monitor_update"] += time.perf_counter()-tick

    if saved:
        monitor_difference = metrics["monitor"]["loss"] - saved["snapshots"][str(horizon)]["monitor"]
        if abs(monitor_difference)>1e-9:
            raise AssertionError(("Saved monitor loss replay differs", monitor_difference))
    else:
        monitor_difference = None
    for metric in metrics.values():
        metric["sample_gain"] = metrics["monitor"]["loss"]-metric["loss"]
    timing = {}
    for version, method in methods.items():
        if method.envelope is not None:
            for key in ("increment_updates", "increment_log_calls"):
                method.count[key] = method.envelope.stats[key]
        timing[str(version)] = {**method.time,
            "end_to_end": sum(times.values())+sum(method.time.values()), "counts": method.count}
    return {"mode":mode, "case":case, "episode":index, "seed":seed, "amplitude":str(b), "onset":t0,
            "steps":steps, "horizon":horizon, "freeze_sha256":freeze_hash, "metrics":metrics,
            "queries":queries, "domains":domains, "timing":timing, "shared_timing":times,
            "monitor_replay_difference":monitor_difference, "final_prefix_hash":record.prefix_hash,
            "wall_seconds":time.perf_counter()-started}


def mean_ci(values):
    a = np.array(values, float)
    answer = {"mean":float(a.mean()), "t95":None}
    if len(a)>1:
        radius = float(student_t.ppf(.975, len(a)-1)*a.std(ddof=1)/math.sqrt(len(a)))
        answer["t95"] = [float(a.mean())-radius, float(a.mean())+radius]
    return answer


def summarize(rows, mode, freeze_hash):
    common = [(q["8"], q["9"]) for row in rows for q in row["queries"] if "8" in q and "9" in q]
    equal_success = [(a,b) for a,b in common if a["certified"] and b["certified"]]
    by_case = {}
    for case in sorted({row["case"] for row in rows}):
        group = [row for row in rows if row["case"] == case]
        labels = ["monitor","point","8","9"]
        by_case[str(case)] = {
            "n":len(group), "amplitude":group[0]["amplitude"], "onset":group[0]["onset"],
            "mean_cumulative_loss":{key:mean_ci([r["metrics"][key]["loss"] for r in group])["mean"] for key in labels},
            "gain_vs_monitor":{key:mean_ci([r["metrics"][key]["sample_gain"] for r in group]) for key in labels[1:]},
            "stage9_gain_vs_stage8":mean_ci([r["metrics"]["8"]["loss"]-r["metrics"]["9"]["loss"] for r in group]),
            "methods":{key:{
                "mean_conditional_gain":float(np.mean([r["metrics"][key]["conditional_gain"] for r in group])),
                "mean_guarantee":float(np.mean([r["metrics"][key]["guarantee"] for r in group])),
                "mean_nonzero_steps":float(np.mean([r["metrics"][key]["nonzero_steps"] for r in group])),
                "first_useful_times":[r["metrics"][key]["first_useful"] for r in group],
                "any_false_episode":sum(r["metrics"][key]["false_steps"]>0 for r in group),
                "false_steps":sum(r["metrics"][key]["false_steps"] for r in group),
                "coverage_misses":sum(r["metrics"][key]["coverage_misses"] for r in group),
                "risk_violations":sum(r["metrics"][key]["risk_violations"] for r in group)}
                for key in labels[1:]},
        }
    return {"mode":mode, "freeze_sha256":freeze_hash, "episode_count":len(rows), "cases":by_case,
            "common_queries":len(common), "joint_successes":len(equal_success),
            "different_decisions":sum(a["certified"] != b["certified"] for a,b in common),
            "different_guarantees_on_joint_successes":sum(F(a["gain"]) != F(b["gain"]) for a,b in equal_success),
            "query_totals":{str(v):{key:sum(row["timing"][str(v)]["counts"][key] for row in rows)
                                   for key in rows[0]["timing"][str(v)]["counts"]} for v in (8,9)},
            "time_totals":{str(v):{key:sum(r["timing"][str(v)][key] for r in rows)
                                   for key in ("advance","query","commit","output","end_to_end")} for v in (8,9)},
            "final_domain_means":{str(v):{field:float(np.mean([r["domains"][-1][str(v)][field] for r in rows]))
                                           for field in ("onsets","components","width")} for v in (8,9)}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("replay","fresh","smoke"))
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    config = read(HERE/"stage9_protocol.json")
    if args.mode == "smoke":
        row = run_episode("replay", -1, 3, "unfrozen")
        write(HERE/"smoke.tmp.json", row)
        return
    digest = freeze(config,args.mode)
    jobs = [(-1,i) for i in config["episode_indices"]] if args.mode=="replay" else [
        (case,index) for case in range(len(config["cases"]))
        for index in range(config["episodes_per_case"])]
    result_dir=HERE/f"{args.mode}_episodes"
    rows=[]
    pending={}
    with ProcessPoolExecutor(args.workers) as pool:
        for case,index in jobs:
            path=result_dir/f"case{case}_episode{index:03d}.json"
            if path.exists():
                row=read(path)
                if row["freeze_sha256"]!=digest:
                    raise RuntimeError("Output incompatible with freeze")
                rows.append(row)
                continue
            future=pool.submit(run_episode,args.mode,case,index,digest)
            pending[future]=path
        for future in as_completed(pending):
            row=future.result()
            write(pending[future],row)
            rows.append(row)
            print(row["mode"],row["case"],row["episode"],len(row["queries"]),
                  round(row["wall_seconds"],2),flush=True)
    rows.sort(key=lambda r:(r["case"],r["episode"]))
    summary=summarize(rows,args.mode,digest)
    write(HERE/f"{args.mode}_summary.json",summary)
    print(json.dumps(summary,indent=2),flush=True)


if __name__=="__main__":
    main()

