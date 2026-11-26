from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from decimal import Decimal as D, MAX_EMAX, MIN_EMIN, getcontext
from fractions import Fraction as F
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
sys.dont_write_bytecode = True

import numpy as np

getcontext().Emax = MAX_EMAX
getcontext().Emin = MIN_EMIN

TASK = Path(__file__).resolve().parent
STAGE8 = TASK.parent
REPO = STAGE8.parents[1]
sys.path.insert(0, str(STAGE8 / "code"))

import experiment as experiment_module
from experiment import (
    A as A_NOM_FLOAT,
    B as B_FLOAT,
    CAP,
    MODEL,
    TIMES,
    USEFUL,
    WINDOW,
    W,
    Methods,
    control,
    digest,
    point_output,
    publish,
    read,
    record as frozen_record,
)
from exact_linear import add, asfloat, inverse, matmul, matrix, transpose, update
from fixed_amplitude import capped_halfspace_action

PLANT = read(STAGE8 / "config/plants.json")["plants"]["industrial_two_tank"]
SPEC = read(STAGE8 / "config/confirmation_protocol.json")
SUPP_REG = read(STAGE8 / "supplement/registration.json")
GROUPS = list(SPEC["groups"])
GROUP_CODE = {name: index for index, name in enumerate(GROUPS)}
A_NOM = matrix(PLANT["A"])
B_EXACT = matrix(PLANT["B"])
C_EXACT = matrix(PLANT["C"])
Q_EXACT = matrix(PLANT["Q"])
R_EXACT = F(PLANT["R"][0][0])
Z_EXACT = F(PLANT["Z"])
P0_EXACT = matrix(PLANT["P0"])
W_EXACT = matrix(PLANT["W"])
SQRT_Q = np.linalg.cholesky(np.asarray(PLANT["Q"], dtype=float))
QUANT_HALF_WIDTH = float(MODEL["quantization_half_width"])

ORIGINAL_CHOOSE_POINT = experiment_module.choose_point
LAST_POINT_PROPOSAL = None
ORIGINAL_EXPERIMENT_UPDATE = experiment_module.update
CAPTURED_EXACT_UPDATE = None


def capture_choose_point(scored, grid):
    global LAST_POINT_PROPOSAL
    direction, point, amplitude = ORIGINAL_CHOOSE_POINT(scored, grid)
    LAST_POINT_PROPOSAL = {
        "direction": direction,
        "point": np.asarray(point, dtype=float).copy(),
        "amplitude": D(amplitude),
        "score": D(scored.score),
    }
    return direction, point, amplitude


def capture_exact_update(covariance, observation, variance):
    global CAPTURED_EXACT_UPDATE
    CAPTURED_EXACT_UPDATE = ORIGINAL_EXPERIMENT_UPDATE(covariance, observation, variance)
    return CAPTURED_EXACT_UPDATE


experiment_module.choose_point = capture_choose_point
experiment_module.update = capture_exact_update


def atomic_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n",
        encoding="utf8",
        newline="\n",
    )
    temporary.replace(path)


def source_hashes():
    paths = [
        STAGE8 / "registration.json",
        STAGE8 / "supplement/registration.json",
        STAGE8 / "config/confirmation_protocol.json",
        STAGE8 / "config/plants.json",
        STAGE8 / "code/experiment.py",
        STAGE8 / "code/signed_certify.py",
        STAGE8 / "code/run.py",
        REPO / "reviews/paper2_stage6_vector_correction_20261122/exact_linear.py",
        REPO / "reviews/paper2_stage6_vector_correction_20261122/vector_record.py",
        REPO / "reviews/paper2_stage7_fixed_amplitude_20261122/fixed_amplitude.py",
    ]
    return {path.relative_to(REPO).as_posix(): digest(path) for path in paths}


def registration_data():
    calibration = read(STAGE8 / "results/calibration.json")
    return {
        "task": "Stage 8 model-boundary and mismatch robustness exploration",
        "source_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO, text=True
        ).strip(),
        "runtime": {"python": sys.version, "numpy": np.__version__},
        "seed_rule": {
            "base_test_seed": SPEC["test_seed"],
            "numpy_seedsequence": "[base_test_seed, frozen_group_index, trajectory_index]",
            "streams": ["physical_process_and_measurement", "event_randomization", "center_jitter"],
            "paired_indices": "first 12 indices from the frozen confirmation groups",
            "group_order": GROUPS,
        },
        "frozen_model": {
            "A": PLANT["A"], "B": PLANT["B"], "C": PLANT["C"], "Q": PLANT["Q"],
            "R": PLANT["R"], "Z": PLANT["Z"], "W": PLANT["W"], "P0": PLANT["P0"],
            "m0": ["0", "0"], "b_max_cm": "0.35", "action_l1_cap": "1",
            "horizon": 608, "window_inclusive": [50, 561], "window_length": 512,
            "queries": list(TIMES), "epsilon": SPEC["epsilon"],
            "branch_nodes_per_query": SPEC["budget"],
            "useful_lower_bound": SPEC["useful_gain"],
            "center_jitter_half_width": MODEL["quantization_half_width"],
        },
        "frozen_point_gates": {
            "h0": "0", "q95": SUPP_REG["thresholds"]["q95"],
            "M1": calibration["threshold"], "M1_rank": calibration["rank"],
            "calibration_n": SPEC["calibration_n"],
        },
        "quantizer": {
            "levels": [None, 12, 10, 8, 6, 4],
            "range_cm": [-5.0, 5.0],
            "rule": "endpoint-inclusive uniform mid-rise with 2^B levels; nearest level, ties-to-even, endpoint saturation",
            "spacing": "10/(2^B-1)",
            "continuous_baseline": "received binary64 payload, no quantizer",
            "center_feedback": "the quantized received payload updates the shared nominal monitor and later centers",
        },
        "drift": {
            "onset": 50, "baseline_bias_cm": "0.35",
            "fractions_of_initial_bias_over_511_steps": [0, 0.05, 0.10, 0.20, 0.35, 0.50],
            "rho_formula": "0.35*fraction/511",
            "decay": "clip(0.35-rho*(t-50), -0.35, 0.35)",
            "enhance": "clip(0.35+rho*(t-50), -0.35, 0.35); saturates at +0.35 and is identical to the constant path",
            "periodic_optional": "not run",
            "M3_rho_status": "downstream mechanism exploration only; upstream likelihood certificate is not statistically valid under variable bias",
        },
        "model_mismatch": {
            "A_plant_formula": "A_nom*(1+epsilon_A), elementwise",
            "epsilon_A": ["0", "+0.01", "-0.01", "+0.02", "-0.02", "+0.05", "-0.05"],
            "algorithm_and_event_center_model": "frozen nominal model",
        },
        "sample_plan": {
            "quantization": "12 each for strong_positive, strong_negative, and health at each bit depth",
            "drift": "12 paired positive-bias traces at each unique decay level; clipped enhancement aliases the constant trace",
            "model_mismatch": "12 per group at 0%, +/-1%, +/-2%; 2 per group at +/-5% extreme pilot due exact rational compute budget",
            "model_mismatch_batch_size": 6,
            "model_mismatch_batch_order": "standard cases indices 0-5 and 6-11; extreme pilot indices 0-1 per group",
            "workers": 6,
        },
        "source_hashes": source_hashes(),
        "decimal_exponent_range": {"Emax": MAX_EMAX, "Emin": MIN_EMIN},
        "matrix_batch_runner_sha256": digest(TASK / "run_matrix_batches_v4.py"),
        "implementation_sha256": hashlib.sha256((TASK / "run_exploration.py").read_bytes()).hexdigest(),
        "rebuild_report_sha256": digest(TASK / "rebuild_report_final.py"),
        "reproduce_sha256": digest(TASK / "reproduce.py"),
    }


def register():
    target = TASK / "registration.json"
    if target.exists() and any((TASK / "data_v4").rglob("*.json")):
        raise FileExistsError("Cannot revise the registration after trial data exist")
    atomic_json(target, registration_data())
    print("registered", digest(target))


def verify_registration():
    registration = read(TASK / "registration.json")
    if registration["source_hashes"] != source_hashes():
        raise RuntimeError("Frozen source hash mismatch")
    if registration["runtime"] != {"python": sys.version, "numpy": np.__version__}:
        raise RuntimeError("Registered runtime mismatch")
    implementation_hash = hashlib.sha256((TASK / "run_exploration.py").read_bytes()).hexdigest()
    if implementation_hash != registration["implementation_sha256"]:
        raise RuntimeError("Exploration implementation differs from registration")
    if digest(TASK / "rebuild_report_final.py") != registration["rebuild_report_sha256"]:
        raise RuntimeError("Report rebuild script differs from registration")
    if digest(TASK / "reproduce.py") != registration["reproduce_sha256"]:
        raise RuntimeError("Reproduction entry differs from registration")
    if registration.get("decimal_exponent_range") != {"Emax": MAX_EMAX, "Emin": MIN_EMIN}:
        raise RuntimeError("Registered Decimal exponent range mismatch")
    if digest(TASK / "run_matrix_batches_v4.py") != registration["matrix_batch_runner_sha256"]:
        raise RuntimeError("Matrix batch runner differs from registration")
    return registration, digest(TASK / "registration.json")


def quantize(value, bits):
    if bits is None:
        return float(value)
    levels = 2 ** bits
    spacing = 10.0 / (levels - 1)
    clipped = min(5.0, max(-5.0, value))
    code = int(np.rint((clipped + 5.0) / spacing))
    code = min(levels - 1, max(0, code))
    return float(-5.0 + code * spacing)


def bias_at(task, time_index):
    onset = 50
    kind = task["bias_kind"]
    if kind == "health":
        return F(0)
    if kind in ("constant", "model_constant"):
        return F(task.get("bias", "0")) if time_index >= onset else F(0)
    rho = F(task["rho"])
    if time_index < onset:
        return F(0)
    if kind == "decay":
        value = F("0.35") - rho * (time_index - onset)
    elif kind == "enhance":
        value = F("0.35") + rho * (time_index - onset)
    else:
        raise ValueError(kind)
    return max(F("-0.35"), min(F("0.35"), value))


def generate_record(seed, group, index, task):
    physical, trigger, phase = [
        np.random.default_rng(child)
        for child in np.random.SeedSequence([seed, GROUP_CODE[group], index]).spawn(3)
    ]
    epsilon = F(task.get("epsilon", "0"))
    a_plant = [[value * (F(1) + epsilon) for value in row] for row in A_NOM]
    a_float = np.asarray([[float(value) for value in row] for row in a_plant])
    state = np.linalg.cholesky(np.asarray(PLANT["P0"], dtype=float)) @ physical.normal(size=2)
    center_prior = np.zeros(2)
    center_covariance = P0_EXACT
    frames, states, raw_payloads, biases = [], [], [], []

    for time_index in range(SPEC["steps"]):
        clean = float(state[0] + math.sqrt(float(R_EXACT)) * physical.normal())
        jitter = (
            QUANT_HALF_WIDTH * 0.999999999 * (2 * phase.random() - 1)
            if time_index else 0.0
        )
        center = float(center_prior[0] + jitter)
        sent = bool(
            trigger.random()
            > math.exp(-float(Z_EXACT) * (clean - center) ** 2 / 2)
        )
        bias = bias_at(task, time_index) if sent else F(0)
        raw = float(clean + float(bias)) if sent else None
        received = quantize(raw, task.get("bits")) if sent else None
        frames.append([time_index, sent, center, received])
        states.append(state.copy())
        raw_payloads.append(raw)
        biases.append(str(bias))

        variance = R_EXACT + (F(0) if sent else F(1) / Z_EXACT)
        post_covariance, gain, _ = update(center_covariance, C_EXACT, variance)
        center_covariance = add(
            matmul(matmul(A_NOM, post_covariance), transpose(A_NOM)),
            Q_EXACT,
        )
        observation = received if sent else center
        posterior = center_prior + np.asarray(asfloat(gain)).ravel() * (
            observation - center_prior[0]
        )
        center_prior = A_NOM_FLOAT @ posterior + B_FLOAT @ control(time_index)
        state = a_float @ state + B_FLOAT @ control(time_index) + SQRT_Q @ physical.normal(size=2)

    return frames, states, raw_payloads, biases, a_plant


def exact_matvec(a, x):
    return [sum((coefficient * value for coefficient, value in zip(row, x)), F(0)) for row in a]


def exact_add_vectors(a, b):
    return [x + y for x, y in zip(a, b)]


def exact_dot(a, b):
    return sum((x * y for x, y in zip(a, b)), F(0))


def conditional_gain(delta, action):
    weighted_action = exact_matvec(W_EXACT, action)
    return 2 * exact_dot(delta, weighted_action) - exact_dot(action, weighted_action)


def move_direction(direction, transition):
    if W_EXACT != [[F(1), F(0)], [F(0), F(1)]]:
        raise NotImplementedError("The optimized projection recursion requires W=I")
    inverse_transpose = transpose(inverse(transition))
    moved = tuple(row[0] for row in matmul(inverse_transpose, [[value] for value in direction]))
    scale = max(map(abs, moved))
    return tuple(value / scale for value in moved), scale


def suffix_drift_margins(send_times, projections, anchor_time, rho):
    suffix = [F(0)] * len(send_times)
    running = F(0)
    for index in range(len(send_times) - 1, -1, -1):
        running += rho * abs(send_times[index] - anchor_time) * abs(projections[index])
        suffix[index] = running
    return suffix


def initialize_direction_state(direction, injection_response, send_times):
    weighted_direction = exact_matvec(W_EXACT, direction)
    projections = [
        exact_dot(weighted_direction, injection_response[send_time])
        for send_time in send_times
    ]
    return {"direction": tuple(direction), "projections": projections}


def advance_direction_states(states, directions, transition, gain, sent,
                             injection_response, send_times):
    updated = []
    for state in states:
        direction, scale = move_direction(state["direction"], transition)
        projections = [value / scale for value in state["projections"]]
        if sent:
            projections.append(exact_dot(exact_matvec(W_EXACT, direction), gain))
        updated.append({"direction": direction, "projections": projections})
    for direction in directions[len(updated):]:
        updated.append(initialize_direction_state(direction, injection_response, send_times))
    if len(updated) != len(directions):
        raise AssertionError("Direction propagation state does not match certified directions")
    if any(state["direction"] != tuple(direction)
           for state, direction in zip(updated, directions)):
        raise AssertionError("Adjoint direction recurrence diverged from the frozen method")
    return updated


def m3_rho_action(method, m2_action, m3_action, rho, anchors, direction_states):
    if rho == 0:
        return m3_action
    if method.intervals == {}:
        return (F(0), F(0)), F(0)

    old_action, legacy_floor = capped_halfspace_action(method.old, W, CAP)
    best = publish(method.monitor, old_action, method.radius)[:2]
    send_times = method.core.send_times
    for state in direction_states:
        direction = state["direction"]
        robust_support = None
        margins_by_anchor = {}
        for onset, amplitude_interval in method.intervals.items():
            anchor_time = anchors.get(onset, method.core.n)
            if anchor_time not in margins_by_anchor:
                margins_by_anchor[anchor_time] = suffix_drift_margins(
                    send_times, state["projections"], anchor_time, rho
                )
            coefficient = method.core.support_coefficient(onset, direction)
            static_support = min(
                F(endpoint) * amplitude
                for endpoint in (coefficient.lo, coefficient.hi)
                for amplitude in amplitude_interval
            )
            candidate = static_support - margins_by_anchor[anchor_time][onset]
            robust_support = candidate if robust_support is None else min(robust_support, candidate)
        if robust_support is None or robust_support <= 0:
            continue
        requested, legacy_gain = capped_halfspace_action((direction, robust_support), W, CAP)
        if legacy_gain < legacy_floor:
            continue
        published = publish(method.monitor, requested, method.radius)[:2]
        if published[1] > best[1]:
            best = published
    return best

def build_tasks(kind):
    tasks = []
    indices = range(12)
    if kind == "quantization":
        for bits in (None, 12, 10, 8, 6, 4):
            scenario = "continuous" if bits is None else f"{bits}bit"
            for group in ("strong_positive", "strong_negative", "health"):
                bias = "0" if group == "health" else ("0.35" if group == "strong_positive" else "-0.35")
                for index in indices:
                    tasks.append(dict(experiment=kind, scenario=scenario, bits=bits,
                                      group=group, index=index, bias_kind="constant", bias=bias))
    elif kind == "drift":
        fractions = (0, 5, 10, 20, 35, 50)
        for fraction in fractions:
            rho = F("0.35") * F(fraction, 100) / 511
            scenario = f"decay_{fraction:02d}"
            for index in indices:
                tasks.append(dict(experiment=kind, scenario=scenario, group="strong_positive",
                                  index=index, bias_kind="constant" if fraction == 0 else "decay",
                                  bias="0.35", fraction=fraction, rho=str(rho)))
        for fraction in fractions[1:]:
            rho = F("0.35") * F(fraction, 100) / 511
            for index in indices:
                tasks.append(dict(experiment=kind, scenario=f"enhance_{fraction:02d}",
                                  group="strong_positive", index=index, bias_kind="enhance",
                                  bias="0.35", fraction=fraction, rho=str(rho), alias_of="decay_00"))
    elif kind == "model_mismatch":
        epsilons = (F(0), F(".01"), F("-.01"), F(".02"), F("-.02"), F(".05"), F("-.05"))
        for epsilon in epsilons:
            scenario = f"eps_{float(epsilon):+.2%}"
            for group in ("health", "strong_positive", "strong_negative"):
                bias = "0" if group == "health" else ("0.35" if group == "strong_positive" else "-0.35")
                sample_indices = range(2) if abs(epsilon) == F(".05") else indices
                for index in sample_indices:
                    tasks.append(dict(experiment=kind, scenario=scenario, epsilon=str(epsilon),
                                      group=group, index=index, bias_kind="model_constant", bias=bias))
    else:
        raise ValueError(kind)
    return tasks


def output_path(task):
    scenario = task["scenario"].replace("%", "pct").replace("+", "p").replace("-", "m")
    directory = "data_v4" if task["experiment"] == "model_mismatch" else "data_v2"
    return TASK / directory / task["experiment"] / f"{scenario}_{task['group']}_{task['index']:02d}.json"

def evaluate_task(task, registration_hash):
    global CAPTURED_EXACT_UPDATE
    start_wall = time.perf_counter()
    start_cpu = time.process_time()
    registration = read(TASK / "registration.json")
    seed = registration["seed_rule"]["base_test_seed"]
    frames, states, raw_payloads, biases, a_plant = generate_record(
        seed, task["group"], task["index"], task
    )
    method = Methods(D("0.35"), D(registration["frozen_point_gates"]["M1"]), mode="paired")
    gate_thresholds = {
        name: D(value)
        for name, value in registration["frozen_point_gates"].items()
        if name in ("h0", "q95", "M1")
    }
    gate_states = {name: (np.zeros(2), 0.0) for name in gate_thresholds}
    nominal_prior = [F(0), F(0)]
    true_covariance = P0_EXACT
    true_prior = [F(0), F(0)]
    anchors = {}
    injection_response = {}
    direction_states = []
    metrics = {
        name: {
            "loss": 0.0, "actual_gain": 0.0, "conditional_gain": F(0),
            "conditional_negative_steps": 0, "certificate_checks": 0,
            "risk_violations": 0, "useful_steps": 0, "nonzero_steps": 0,
            "first_useful": None, "endpoint_useful": False, "false_action": False,
        }
        for name in ("M0", "M1_h0", "M1_q95", "M1", "M2", "M3", "M3_rho")
    }
    window = set(range(SPEC["window"][0], SPEC["window"][1] + 1))
    zero = (F(0), F(0))
    max_nominal_filter_error = 0.0
    true_amplitude = [F(value) for value in biases]
    rho = F(task.get("rho", "0")) if task["experiment"] == "drift" else F(0)

    for time_index, frame in enumerate(frames):
        sent = frame[1]
        old_direction_count = len(method.directions)
        CAPTURED_EXACT_UPDATE = None
        actual_actions, query, point_gain, point_transition = method.step(frame)
        if CAPTURED_EXACT_UPDATE is None:
            raise RuntimeError("Nominal exact Kalman update was not captured")
        _, nominal_gain, nominal_transition = CAPTURED_EXACT_UPDATE
        nominal_f = matmul(nominal_transition, A_NOM)
        for send_time in list(injection_response):
            injection_response[send_time] = exact_matvec(nominal_f, injection_response[send_time])
        if sent:
            injection_response[time_index] = tuple(row[0] for row in nominal_gain)
        direction_states = advance_direction_states(
            direction_states, method.directions, nominal_f,
            tuple(row[0] for row in nominal_gain), sent,
            injection_response, method.core.send_times,
        )
        if len(method.directions) < old_direction_count:
            raise AssertionError("The frozen method removed an existing direction")

        for gate_name, threshold in gate_thresholds.items():
            point, amplitude = gate_states[gate_name]
            proposed = point_transition @ point + (point_gain * amplitude if sent else 0.0)
            if query:
                proposal = LAST_POINT_PROPOSAL
                if proposal is None:
                    raise RuntimeError("Missing shared point proposal at a query")
                if proposal["score"] > threshold:
                    proposed = proposal["point"].copy()
                    amplitude = float(proposal["amplitude"])
                else:
                    proposed = np.zeros(2)
                    amplitude = 0.0
            proposed, published = point_output(method.monitor, proposed)
            gate_states[gate_name] = proposed, amplitude
            if gate_name == "M1":
                if published != actual_actions["M1"][0]:
                    raise AssertionError("Shared M1 gate replay differs from frozen action")
            else:
                actual_actions[f"M1_{gate_name}"] = published, None

        if query and any(level.get("certified") for level in query.get("levels", [])):
            for onset in method.intervals or {}:
                anchors[onset] = time_index

        observation = F(str(frame[3])) if sent else F(str(frame[2]))
        nominal_post = [
            nominal_prior[index] + nominal_gain[index][0] * (observation - nominal_prior[0])
            for index in range(2)
        ]
        nominal_prior = exact_add_vectors(
            exact_matvec(A_NOM, nominal_post),
            exact_matvec(B_EXACT, [F(str(float(value))) for value in control(time_index)]),
        )
        method_float = np.asarray(method.monitor, dtype=float)
        max_nominal_filter_error = max(
            max_nominal_filter_error,
            max(abs(float(nominal_post[i]) - method_float[i]) for i in range(2)),
        )

        event_variance = R_EXACT + (F(0) if sent else F(1) / Z_EXACT)
        post_covariance, true_gain, _ = update(true_covariance, C_EXACT, event_variance)
        if sent:
            true_observation = F(str(raw_payloads[time_index])) - true_amplitude[time_index]
        else:
            true_observation = F(str(frame[2]))
        innovation = true_observation - true_prior[0]
        true_post = [
            true_prior[index] + true_gain[index][0] * innovation
            for index in range(2)
        ]
        true_prior = exact_add_vectors(
            exact_matvec(a_plant, true_post),
            exact_matvec(B_EXACT, [F(str(float(value))) for value in control(time_index)]),
        )
        true_covariance = add(
            matmul(matmul(a_plant, post_covariance), transpose(a_plant)),
            Q_EXACT,
        )
        delta = [nominal_post[i] - true_post[i] for i in range(2)]

        actual_actions["M0"] = zero, None
        actual_actions["M3_rho"] = m3_rho_action(
            method, actual_actions["M2"][0], actual_actions["M3"],
            rho, anchors, direction_states,
        )
        if task["experiment"] == "drift" and rho == 0 and actual_actions["M3_rho"] != actual_actions["M3"]:
            raise AssertionError("M3-rho at rho=0 did not reproduce M3")

        for name, (action, lower_bound) in actual_actions.items():
            result = metrics[name]
            result["nonzero_steps"] += int(any(action))
            value = conditional_gain(delta, action) if time_index in window else None
            if value is not None:
                result["conditional_gain"] += value
                result["conditional_negative_steps"] += int(value < 0)
            if lower_bound is not None and lower_bound > 0:
                result["certificate_checks"] += 1
                if value is None:
                    value = conditional_gain(delta, action)
                result["risk_violations"] += int(value + F(1, 10**10) < lower_bound)
            useful = (
                lower_bound is not None and lower_bound >= USEFUL
                if name in ("M2", "M3", "M3_rho")
                else bool(any(action))
            )
            if time_index in window:
                state_error = states[time_index] - method_float
                corrected_error = state_error + np.asarray([float(item) for item in action])
                actual_gain = float(state_error @ state_error - corrected_error @ corrected_error)
                result["loss"] += -actual_gain
                result["actual_gain"] += actual_gain
                result["useful_steps"] += int(useful)
                if useful and result["first_useful"] is None:
                    result["first_useful"] = time_index
                if time_index == SPEC["window"][1]:
                    result["endpoint_useful"] = bool(useful)
            result["false_action"] = result["false_action"] or bool(any(action))

    for result in metrics.values():
        result["conditional_gain"] = float(result["conditional_gain"])
    a_float = np.asarray([[float(value) for value in row] for row in a_plant])
    return {
        **task,
        "seed": seed,
        "seed_group_index": GROUP_CODE[task["group"]],
        "registration_hash": registration_hash,
        "transmissions": sum(int(frame[1]) for frame in frames),
        "horizon": len(frames),
        "max_nominal_filter_error": max_nominal_filter_error,
        "spectral_radius_A_plant": float(max(abs(np.linalg.eigvals(a_float)))),
        "metrics": metrics,
        "cpu_seconds": time.process_time() - start_cpu,
        "wall_seconds": time.perf_counter() - start_wall,
        "public_history_sha256": hashlib.sha256(
            json.dumps(frames, separators=(",", ":")).encode("utf8")
        ).hexdigest(),
    }


def save_task(task, registration_hash):
    path = output_path(task)
    if path.exists():
        if read(path).get("registration_hash") != registration_hash:
            raise RuntimeError(f"Foreign checkpoint: {path.name}")
        return path
    if task.get("alias_of"):
        source_task = dict(task)
        source_task["scenario"] = task["alias_of"]
        source_task.pop("alias_of")
        source_path = output_path(source_task)
        if not source_path.exists():
            raise RuntimeError(f"Missing alias source: {source_path.name}")
        source = read(source_path)
        alias = dict(source)
        alias.update(task)
        alias["aliased_identical_bias_path"] = True
        atomic_json(path, alias)
        return path
    try:
        row = evaluate_task(task, registration_hash)
        atomic_json(path, row)
        return path
    except Exception:
        directory = "data_v4" if task["experiment"] == "model_mismatch" else "data_v2"
        error_dir = TASK / directory / task["experiment"] / "errors"
        error_dir.mkdir(parents=True, exist_ok=True)
        atomic_json(error_dir / f"{path.stem}_{time.time_ns()}.json",
                    {"task": task, "traceback": traceback.format_exc()})
        raise


def check_projection_recurrence():
    transitions = [
        matrix([["1.01", "0.1"], ["0.02", "0.97"]]),
        matrix([["0.99", "0.08"], ["0.01", "1.02"]]),
        matrix([["1.03", "0.04"], ["0.03", "0.96"]]),
        matrix([["0.98", "0.12"], ["0.02", "1.01"]]),
        matrix([["1.02", "0.06"], ["0.01", "0.99"]]),
    ]
    gains = [
        (F("0.2"), F("0.03")), (F("0.18"), F("0.02")),
        (F("0.16"), F("0.04")), (F("0.14"), F("0.01")),
        (F("0.12"), F("0.05")),
    ]
    sends = (True, False, True, True, False)
    state = {"direction": (F(1), F(1, 3)), "projections": []}
    responses = {}
    send_times = []
    for time_index, (transition, gain, sent) in enumerate(zip(transitions, gains, sends)):
        for send_time in list(responses):
            responses[send_time] = exact_matvec(transition, responses[send_time])
        if sent:
            responses[time_index] = gain
            send_times.append(time_index)
        direction, scale = move_direction(state["direction"], transition)
        projections = [value / scale for value in state["projections"]]
        if sent:
            projections.append(exact_dot(direction, gain))
        state = {"direction": direction, "projections": projections}
        direct = [
            exact_dot(exact_matvec(W_EXACT, direction), responses[send_time])
            for send_time in send_times
        ]
        if state["projections"] != direct:
            raise AssertionError("Adjoint scalar projection recurrence is not exact")
    print("adjoint projection recurrence: exact rational equality passed")

def check_generator():
    seed = SPEC["test_seed"]
    for group, index, bias in (
        ("strong_positive", 0, .35),
        ("strong_negative", 0, -.35),
        ("health", 0, 0.0),
    ):
        task = dict(bias_kind="constant", bias=str(bias), epsilon="0", bits=None)
        frames, states, _, _, _ = generate_record(seed, group, index, task)
        frozen_frames, frozen_states = frozen_record(seed, GROUP_CODE[group], index, bias)
        if frames != frozen_frames:
            raise AssertionError(f"Generated public record differs from frozen {group}")
        if not np.array_equal(np.asarray(states), np.asarray(frozen_states)):
            raise AssertionError(f"Generated physical states differ from frozen {group}")
    print("generator parity: 3/3 frozen records and states match")
    check_projection_recurrence()


def run_kind(kind, workers=6, scenario_filter=None, group_filter=None, index_start=0, index_stop=12):
    _, registration_hash = verify_registration()
    tasks = build_tasks(kind)
    tasks = [task for task in tasks if (scenario_filter is None or task["scenario"] == scenario_filter) and (group_filter is None or task["group"] == group_filter) and index_start <= task["index"] < index_stop]
    if not tasks:
        raise ValueError("The requested registered batch is empty")
    todo = []
    for task in tasks:
        path = output_path(task)
        if path.exists():
            if read(path).get("registration_hash") != registration_hash:
                raise RuntimeError(f"Registration mismatch: {path.name}")
        elif not task.get("alias_of"):
            todo.append(task)
    started = time.perf_counter()
    completed = 0
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(save_task, task, registration_hash) for task in todo]
        for future in as_completed(futures):
            future.result()
            completed += 1
            if completed % 12 == 0 or completed == len(todo):
                print(f"{kind}: {completed}/{len(todo)} computed", flush=True)
    for task in tasks:
        if task.get("alias_of") and not output_path(task).exists():
            save_task(task, registration_hash)
    rows = [read(output_path(task)) for task in tasks]
    cpu_seconds = sum(row["cpu_seconds"] for row in rows if not row.get("aliased_identical_bias_path"))
    wall_seconds = time.perf_counter() - started
    log_name = "run_log_v4.json" if kind == "model_mismatch" else "run_log_v2.json"
    log_path = TASK / log_name
    log = read(log_path) if log_path.exists() else []
    log.append(dict(experiment=kind, scenario=scenario_filter, group=group_filter,
                    index_start=index_start, index_stop=index_stop,
                    requested=len(tasks), newly_computed=len(todo),
                    cpu_seconds=cpu_seconds, wall_seconds=wall_seconds, workers=workers))
    atomic_json(log_path, log)
    print(f"{kind}: {len(rows)} rows; {cpu_seconds/3600:.3f} CPU h; {wall_seconds/3600:.3f} wall h")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "phase",
        choices=("register", "check", "quantization", "drift", "model_mismatch", "all"),
    )
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--scenario")
    parser.add_argument("--group")
    parser.add_argument("--index-start", type=int, default=0)
    parser.add_argument("--index-stop", type=int, default=12)
    args = parser.parse_args()
    if args.phase == "register":
        register()
    elif args.phase == "check":
        verify_registration()
        check_generator()
    elif args.phase == "all":
        if not (TASK / "registration.json").exists():
            register()
        check_generator()
        run_kind("drift", args.workers)
        for epsilon in ("eps_+0.00%", "eps_+1.00%", "eps_-1.00%",
                        "eps_+2.00%", "eps_-2.00%", "eps_+5.00%", "eps_-5.00%"):
            for group in ("health", "strong_positive", "strong_negative"):
                for index_start in (0, 6):
                    run_kind("model_mismatch", args.workers, epsilon, group,
                             index_start, index_start + 6)
    else:
        verify_registration()
        check_generator()
        run_kind(args.phase, args.workers, args.scenario, args.group,
                 args.index_start, args.index_stop)


if __name__ == "__main__":
    main()























