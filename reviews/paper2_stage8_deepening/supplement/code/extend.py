"""Supplemental protocol and paired runs using the frozen Stage 8 implementation."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
SUPPLEMENT = HERE.parent
TASK = SUPPLEMENT.parent
sys.path.insert(0, str(TASK / "code"))

import numpy as np
import scipy
from experiment import (
    ROOT, REV, Methods, record, evaluate, read, save, digest,
    A, B, control, TIMES, WINDOW, point_output,
)

BASE = read(TASK / "registration.json")
THRESHOLDS = {"h0": "0"}
maxima = sorted(max(map(Decimal, row["scores"]))
                for row in read(TASK / "results/calibration.json")["rows"])
THRESHOLDS["q95"] = str(maxima[189])
THRESHOLDS["M1"] = BASE["threshold"]


def protocol():
    return read(SUPPLEMENT / "registration.json")


def register():
    target = SUPPLEMENT / "registration.json"
    if target.exists() or (SUPPLEMENT / "results/transition").exists():
        raise FileExistsError("Supplement already registered")
    paths = [TASK / "registration.json", TASK / "results/calibration.json"]
    paths += list(HERE.glob("*.py"))
    paths += [REV / name for name in BASE["inputs"]]
    reg = {
        "baseline": "240cb7ec938ecd7dcdf28cd2fd063ff9cad96883",
        "source_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=TASK, text=True).strip(),
        "versions": [sys.version, np.__version__, scipy.__version__],
        "new_seed": 202611253001,
        "diagnostic_seed": 202611253002,
        "transition_groups": {
            "transition_positive": {"rng_group": 0, "amplitude": 0.25, "count": 12},
            "transition_negative": {"rng_group": 1, "amplitude": -0.25, "count": 12},
        },
        "cap": BASE["strong"],
        "thresholds": THRESHOLDS,
        "frozen_test_seed": BASE["test_seed"],
        "workers": 4,
        "onset": 50,
        "steps": 608,
        "loss_window": [50, 561],
        "queries": list(TIMES),
        "Z_confirmation": 2,
        "Z_health_diagnostics": [2, 20],
        "diagnostic_count_per_Z": 12,
        "purpose": "descriptive supplementary transition experiment and point-gate replay",
        "stop": "all 24 new IDs plus all 116 gate replays and 24 health diagnostics",
        "interval": "two-sided paired trajectory Student-t 95%, descriptive",
        "old_gate_replay": "same archived public record and re-created physical states, no certificate queries",
        "new_gate_replay": "new public record, same h0/q95/M1 frozen calibration thresholds",
        "failure_handling": "save errors; rerun same seed only; require matching registration ID to reuse",
        "unchanged_original": "92 tank rows and 130 V2 rows remain separate evidence cohorts",
        "inputs": {
            p.relative_to(REV).as_posix(): digest(p)
            for p in sorted(set(paths))
        },
    }
    save(target, reg)


def check_registration():
    reg = protocol()
    for name, value in reg["inputs"].items():
        if digest(REV / name) != value:
            raise ValueError("Supplement source hash mismatch: " + name)
    if reg["versions"] != [sys.version, np.__version__, scipy.__version__]:
        raise ValueError("Runtime differs from registration")
    return reg


def transition(name, index):
    reg = protocol()
    identity = digest(SUPPLEMENT / "registration.json")
    output = SUPPLEMENT / "results/transition" / f"{name}-{index:02d}.json"
    if output.exists():
        row = read(output)
        assert row["supplement_registration"] == identity
        return row["id"]
    spec = reg["transition_groups"][name]
    start = time.process_time()
    public, states = record(
        reg["new_seed"], spec["rng_group"], index, spec["amplitude"])
    row = evaluate(public, states, spec["amplitude"], Decimal(reg["cap"]), reg["thresholds"]["M1"])
    row.update(
        id=output.stem, group=name, index=index, b=spec["amplitude"],
        seed=reg["new_seed"], rng_group=spec["rng_group"],
        supplement_registration=identity, cpu=time.process_time()-start,
    )
    save(output, row)
    return row["id"]


def point_gates(row, states):
    """Share original point-grid work and propagate each gated branch separately."""
    reg = protocol()
    method = Methods(Decimal(reg["cap"]), "0", mode="M1")
    branches = {name: (np.zeros(2), 0.0) for name in reg["thresholds"]}
    metrics = {
        name: dict(loss=0.0, conditional=0.0, nonzero=0, first=None, active_steps=0, end=False)
        for name in branches
    }
    hashes = {name: hashlib.sha256() for name in branches}
    true_prior = np.zeros(2)
    H = np.zeros(2)
    b = row["b"]
    score_checks = []
    for frame, state in zip(row["public"], states, strict=True):
        t, sent, center, payload = frame
        _, query, gain, dynamics = method.step(frame)
        active = sent and t >= reg["onset"]
        measurement = payload - (b if active else 0.0) if sent else center
        mu = true_prior + gain*(measurement-true_prior[0])
        true_prior = A @ mu + B @ control(t)
        H = dynamics @ H + (gain if active else 0.0)
        delta = b*H
        assert np.max(np.abs(method.monitor-mu-delta)) <= 1e-9
        for name, (point, amplitude) in branches.items():
            point = dynamics @ point + (gain*amplitude if sent else 0.0)
            if query is not None:
                if Decimal(query["score"]) > Decimal(reg["thresholds"][name]):
                    # The original method has clipped the same point proposal once.
                    point, amplitude = method.point.copy(), method.b
                else:
                    point, amplitude = np.zeros(2), 0.0
            point, actual = point_output(method.monitor, point)
            branches[name] = point, amplitude
            hashes[name].update(np.asarray(actual, dtype=">f8").tobytes())
            a = np.asarray(actual, float)
            metric = metrics[name]
            on = bool(any(actual))
            metric["nonzero"] += int(on)
            if t in WINDOW:
                error = state-method.monitor+a
                metric["loss"] += float(error@error)
                metric["conditional"] += float(2*delta@a-a@a)
                metric["active_steps"] += int(on)
                if on and metric["first"] is None:
                    metric["first"] = t
                if t == 561:
                    metric["end"] = on
        if query:
            score_checks.append(query["score"])
    assert score_checks == [q["score"] for q in row["queries"]]
    assert hashes["M1"].hexdigest() == row["actions_sha256"]["M1"]
    assert abs(metrics["M1"]["loss"]-row["metrics"]["M1"]["loss"]) < 1e-10
    return dict(
        id=row["id"], group=row["group"], b=b, metrics=metrics,
        gate_action_hashes={name: value.hexdigest() for name, value in hashes.items()},
        original_M1_identical=True,
        M0_loss=row["metrics"]["M0"]["loss"],
        opportunity=row["metrics"]["Oracle"]["conditional"],
        sending_steps=sum(frame[1] for frame in row["public"]),
        step_count=len(row["public"]),
    )


def ladder(source):
    path = Path(source)
    original = read(path)
    reg = protocol()
    identity = digest(SUPPLEMENT / "registration.json")
    output = SUPPLEMENT / "results/ladder" / path.name
    if output.exists():
        assert read(output)["supplement_registration"] == identity
        return path.stem
    if original["group"].startswith("transition"):
        spec = reg["transition_groups"][original["group"]]
        seed, group = reg["new_seed"], spec["rng_group"]
    else:
        seed = reg["frozen_test_seed"]
        group = list(BASE["groups"]).index(original["group"])
    start = time.process_time()
    public, states = record(seed, group, original["index"], original["b"])
    assert public == original["public"]
    result = point_gates(original, states)
    result.update(
        supplement_registration=identity,
        source_path=path.relative_to(TASK).as_posix(),
        source_sha256=digest(path), cpu=time.process_time()-start,
    )
    save(output, result)
    return path.stem


def diagnose(args):
    z, index = args
    reg = protocol()
    # Run the original simulator with a process-local model parameter. No result
    # from this diagnostic is used to tune the supplementary confirmation.
    from experiment import MODEL
    previous = MODEL["Z"]
    MODEL["Z"] = str(z)
    try:
        public, _ = record(reg["diagnostic_seed"], 0, index, 0.0)
    finally:
        MODEL["Z"] = previous
    return dict(Z=z, index=index, sent=sum(frame[1] for frame in public),
                steps=len(public), seed=reg["diagnostic_seed"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["register", "transition", "ladder", "diagnostic"])
    args = parser.parse_args()
    if args.stage == "register":
        register()
        return
    reg = check_registration()
    with ProcessPoolExecutor(max_workers=reg["workers"]) as pool:
        if args.stage == "transition":
            jobs = [
                (name, i) for name, item in reg["transition_groups"].items()
                for i in range(item["count"])
            ]
            futures = [pool.submit(transition, *item) for item in jobs]
            folder = SUPPLEMENT / "results/transition/errors"
        elif args.stage == "ladder":
            sources = sorted((TASK / "results/confirmation").glob("*.json"))
            sources += sorted((SUPPLEMENT / "results/transition").glob("*.json"))
            assert len(sources) == 116
            futures = [pool.submit(ladder, str(path)) for path in sources]
            folder = SUPPLEMENT / "results/ladder/errors"
        else:
            inputs = [(z, i) for z in reg["Z_health_diagnostics"]
                      for i in range(reg["diagnostic_count_per_Z"])]
            save(SUPPLEMENT / "results/trigger_diagnostic.json",
                 list(pool.map(diagnose, inputs)))
            return
        for index, future in enumerate(as_completed(futures)):
            try:
                print(index+1, future.result(), flush=True)
            except Exception:
                import traceback
                save(folder / f"failure-{time.time_ns()}.json",
                     dict(traceback=traceback.format_exc(),
                          registration=digest(SUPPLEMENT / "registration.json")))
                raise


if __name__ == "__main__":
    main()
