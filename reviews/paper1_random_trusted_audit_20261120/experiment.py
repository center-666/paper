"""Random trusted-audit experiment. No manuscript edits and no adaptive reruns."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import platform
import sys
import traceback
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.dont_write_bytecode = True
LEGACY = REPO / "reviews/paper1_e1_scalar_execution/code/run_e1.py"
spec = importlib.util.spec_from_file_location("frozen_e1", LEGACY)
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)
INPUTS = HERE / "inputs"
RESULTS = HERE / "results" / "run_20261120_v1"
PROTOCOL_PATH = HERE / "protocol.json"
FREEZE_PATH = HERE / "freeze.json"
INPUT_MANIFEST = HERE / "input_manifest.json"
Z95 = 1.959963984540054
Z99_ONE_SIDED = 2.3263478740408408
Z80 = 0.8416212335729143


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                    encoding="utf-8", newline="\n")


def read_protocol():
    return json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))


def freeze() -> None:
    if FREEZE_PATH.exists():
        raise SystemExit("freeze.json already exists; refusing to replace it.")
    protocol = read_protocol()
    result = {
        "base_commit": protocol["base_commit"],
        "protocol_sha256": sha(PROTOCOL_PATH),
        "experiment_script_sha256": sha(Path(__file__)),
        "saved_e1_script_sha256": sha(LEGACY),
        "other_scripts_sha256": {p.name: sha(p) for p in HERE.glob("*.py")},
        "python": sys.version,
        "numpy": np.__version__,
        "platform": platform.platform(),
        "input_generation_started": False,
        "simulation_started": False,
    }
    write_json(FREEZE_PATH, result)
    print(json.dumps(result, ensure_ascii=True, indent=2))


def verify_frozen():
    if not FREEZE_PATH.exists():
        raise SystemExit("freeze.json missing.")
    f = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    if f["protocol_sha256"] != sha(PROTOCOL_PATH):
        raise SystemExit("Protocol changed after freeze.")
    if f["experiment_script_sha256"] != sha(Path(__file__)):
        raise SystemExit("Experiment code changed after freeze.")
    if f["saved_e1_script_sha256"] != sha(LEGACY):
        raise SystemExit("Legacy E1 code changed.")
    for name, digest in f["other_scripts_sha256"].items():
        if sha(HERE / name) != digest:
            raise SystemExit(f"Frozen helper changed: {name}")
    return f


def generate_inputs() -> None:
    frozen = verify_frozen()
    if INPUTS.exists() and any(INPUTS.iterdir()):
        raise SystemExit("Input directory is nonempty; refusing to overwrite frozen inputs.")
    INPUTS.mkdir(parents=True, exist_ok=True)
    protocol = read_protocol()
    split_sizes = {
        "cal": protocol["calibration_episodes"],
        "test": protocol["test_episodes"],
    }
    files = {}
    model_ids = {"S1": 1, "U1": 2}
    for model in protocol["models"]:
        for split_id, (split, n) in enumerate(split_sizes.items(), start=1):
            streams = []
            for stream_id in range(8):
                rng = np.random.Generator(np.random.PCG64(
                    np.random.SeedSequence([protocol["master_seed"], model_ids[model["id"]],
                                            split_id, stream_id])))
                streams.append(rng)
            x0 = model["m0"] + np.sqrt(model["P0"]) * streams[0].standard_normal(n)
            w0 = np.sqrt(model["Q"]) * streams[1].standard_normal(n)
            v0 = np.sqrt(model["R"]) * streams[2].standard_normal(n)
            v1 = np.sqrt(model["R"]) * streams[3].standard_normal(n)
            u0 = streams[4].random(n)
            u1 = streams[5].random(n)
            sign_u = streams[6].random(n)
            accept_u = streams[7].random(n)
            audit_u = np.random.Generator(np.random.PCG64(
                np.random.SeedSequence([protocol["master_seed"], model_ids[model["id"]],
                                        split_id, 8]))).random(n)
            name = f"{split}_{model['id']}.npz"
            path = INPUTS / name
            np.savez_compressed(path, x0=x0, w0=w0, v0=v0, v1=v1, u0=u0, u1=u1,
                                sign_u=sign_u, accept_u=accept_u, audit_u=audit_u)
            files[name] = {"sha256": sha(path), "episodes": n, "model": model["id"],
                           "split": split, "independent_unit": "one two-time physical episode"}
    manifest = {
        "protocol_sha256": sha(PROTOCOL_PATH),
        "experiment_script_sha256": sha(Path(__file__)),
        "freeze_sha256": sha(FREEZE_PATH),
        "generator": "NumPy PCG64; independent vectorized substreams by model/split/stream",
        "files": files,
        "all_inputs_generated_before_simulation": True,
    }
    write_json(INPUT_MANIFEST, manifest)
    print(json.dumps({"inputs": files, "manifest_sha256": sha(INPUT_MANIFEST)},
                     ensure_ascii=True))


def verify_inputs():
    frozen = verify_frozen()
    if not INPUT_MANIFEST.exists():
        raise SystemExit("Input manifest missing.")
    manifest = json.loads(INPUT_MANIFEST.read_text(encoding="utf-8"))
    if manifest["protocol_sha256"] != sha(PROTOCOL_PATH):
        raise SystemExit("Input manifest protocol hash mismatch.")
    if manifest["experiment_script_sha256"] != sha(Path(__file__)):
        raise SystemExit("Input manifest code hash mismatch.")
    for name, row in manifest["files"].items():
        if sha(INPUTS / name) != row["sha256"]:
            raise SystemExit(f"Input hash mismatch: {name}")
    if manifest["freeze_sha256"] != sha(FREEZE_PATH):
        raise SystemExit("Input manifest freeze hash mismatch.")
    return manifest


def quantize(x, delta):
    return legacy.quantize(x, delta)[1]


def log_send_density(u, model):
    s0, z = model["P0"] + model["R"], model["Z"]
    u = np.asarray(u)
    log_base = -0.5 * np.log(2.0 * np.pi * s0) - u * u / (2.0 * s0)
    prob = -np.expm1(-0.5 * z * u * u)
    with np.errstate(divide="ignore"):
        return log_base + np.log(prob)


def model_constants(model):
    P0, R, A = (model[k] for k in ("P0", "R", "A"))
    k = P0/(P0+R)
    return k, A*k, A*A*P0*R/(P0+R)+model["Q"]+R


def sent_moments(d, s, Z):
    """Unnormalized moments of Y-c, including the actual next-send selection."""
    t = 1.0 + Z*s
    L = np.exp(-.5*np.log(t) - Z*d*d/(2*t))
    v, e = s/t, d/t
    return (
        1-L,
        d-L*e,
        d*d+s-L*(e*e+v),
        d**3+3*d*s-L*(e**3+3*e*v),
        d**4+6*d*d*s+3*s*s-L*(e**4+6*e*e*v+3*v*v),
    )


def health_coefficients(z, model, delta):
    z = np.asarray(z)
    _, lam, s = model_constants(model)
    c1 = quantize(lam * z, delta)
    d = lam * z - c1
    b0, b1, b2, b3, b4 = sent_moments(d, s, model["Z"])
    mu = b1 / b0
    var = b2 / b0 - mu * mu
    c4 = b4 - 4.0 * mu * b3 + 6.0 * mu**2 * b2 - 4.0 * mu**3 * b1 + mu**4 * b0
    var_energy = c4 / b0 - var * var
    var = np.maximum(var, np.finfo(float).tiny)
    var_energy = np.maximum(var_energy, np.finfo(float).tiny)
    return c1, mu, var, var_energy, d


def conditional_residual_features(z, y1, model, delta):
    """Only a target received value and a next continuous value enter this score."""
    c1, mu, var, var_energy, d = health_coefficients(z, model, delta)
    residual = np.asarray(y1) - c1
    oriented = -np.sign(d) * (residual - mu) / np.sqrt(var)
    energy = ((residual - mu) ** 2 - var) / np.sqrt(var_energy)
    return oriented + energy, oriented, energy, c1


def simulate(model, arrays, delta):
    u = arrays["x0"] + arrays["v0"]
    x0 = arrays["x0"]
    y1 = model["A"] * x0 + arrays["w0"] + arrays["v1"]
    send0 = arrays["u0"] > np.exp(-0.5 * model["Z"] * u * u)
    lam = model["A"] * model["P0"] / (model["P0"] + model["R"])
    center_m = quantize(lam * u, delta)
    gate, _, _ = legacy.witness(
        0, send0, np.where(send0, u, np.nan), np.zeros_like(u),
        np.full_like(u, model["P0"]), model["A"], model["R"], delta, 0.0, 0)
    eta = min(0.1, delta / (2.0 * abs(lam)))

    z_cell = u + np.where(arrays["sign_u"] < 0.5, 1.0, -1.0) * eta * gate
    disclosed = np.where(send0, u, 0.0)
    f_log_u = log_send_density(disclosed, model)
    c_u = quantize(lam*disclosed, delta)
    t_ref = 2.0 * c_u / lam - disclosed
    raw_index = (lam * disclosed + delta) / (2.0 * delta)
    boundary = send0 & (raw_index == np.rint(raw_index))
    t_ref = np.where(boundary, disclosed, t_ref)
    f_log_t = log_send_density(t_ref, model)
    alpha = np.zeros_like(u)
    valid = send0 & np.isfinite(f_log_u)
    alpha[valid] = np.minimum(1.0, np.exp(np.minimum(0.0, f_log_t[valid] - f_log_u[valid])))
    accepted = valid & (arrays["accept_u"] < alpha)
    z_ref = np.where(accepted, t_ref, u)

    clean_post = np.where(send0, model["P0"]/(model["P0"]+model["R"]) * u, 0.0)
    clean_error = (x0 - clean_post) ** 2
    outputs = {}
    for name, z in [("healthy", u), ("cell_sign", z_cell), ("balanced_reflection", z_ref)]:
        z_recv = np.where(send0, z, 0.0)
        post = np.where(send0, model["P0"]/(model["P0"]+model["R"]) * z_recv, 0.0)
        m1_prior = model["A"] * post
        c1 = quantize(m1_prior, delta)
        send1 = arrays["u1"] > np.exp(-0.5 * model["Z"] * (y1 - c1) ** 2)
        p0_post = np.where(send0,
            model["P0"]*model["R"]/(model["P0"]+model["R"]),
            model["P0"]*(model["R"]+1/model["Z"])/(model["P0"]+model["R"]+1/model["Z"]))
        p1_prior = model["A"]**2*p0_post+model["Q"]
        r1 = np.where(send1,model["R"],model["R"]+1/model["Z"])
        gain1 = p1_prior/(p1_prior+r1)
        m1_post = m1_prior+gain1*(np.where(send1,y1,c1)-m1_prior)
        p1_post = p1_prior*(1-gain1)
        g, f1, f2, _ = conditional_residual_features(z_recv, y1, model, delta)
        available = send0 & send1
        g = np.where(available, g, 0.0)
        f1 = np.where(available, f1, 0.0)
        f2 = np.where(available, f2, 0.0)
        mse = (x0 - post) ** 2
        outputs[name] = {
            "score": g, "feature_oriented": f1, "feature_energy": f2,
            "available": available, "send0": send0, "send1": send1,
            "zeta0": z_recv, "y1": y1, "mse": mse,
            "damage_paired": mse - clean_error,
            "action": np.where(send0, z - u, 0.0),
            "cell_gate": gate if name == "cell_sign" else np.zeros_like(gate),
            "reflection_accept": accepted if name == "balanced_reflection" else np.zeros_like(gate),
            "reflection_boundary": boundary if name == "balanced_reflection" else np.zeros_like(gate),
            "c1": c1, "P0_post": p0_post,"P1_post":p1_post,"m1_post":m1_post,
        }
    outputs["healthy_mse_reference"] = clean_error
    return outputs


def conformal_threshold(values, alpha=0.01):
    v = np.sort(np.asarray(values, dtype=float))
    if not len(v):
        return float("inf")
    index = max(0, math.ceil((len(v) + 1) * (1.0 - alpha)) - 1)
    if index >= len(v):
        raise ValueError("Too few calibration values for requested finite quantile.")
    return float(v[index])


def wilson(k, n, z=Z95):
    if n == 0:
        return (None, None)
    p = k / n
    den = 1.0 + z*z/n
    ctr = (p + z*z/(2*n))/den
    half = z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return max(0.0, ctr-half), min(1.0, ctr+half)


def score_row(k, n, alpha):
    lo, hi = wilson(k, n)
    return {"events": int(k), "trials": int(n), "rate": (k/n if n else None),
            "wilson95_low": lo, "wilson95_high": hi}


def weighted_quadrature(model, delta, attack, order):
    """Fixed Gauss-Legendre audit of score moments; planning only, no samples."""
    nodes, weights = np.polynomial.legendre.leggauss(order)
    s0 = model["P0"] + model["R"]
    k, lam, s1 = model_constants(model)
    eta = min(0.1, delta/(2*abs(lam)))
    length = 10*math.sqrt(s0)
    # Split at all cell centers and quarter-cell points; no phase averaging.
    step = delta/(2*abs(lam))
    lo = math.floor(-length/step)
    hi = math.ceil(length/step)
    boundaries = np.arange(lo, hi+1)*step
    left = np.maximum(boundaries[:-1], -length)
    right = np.minimum(boundaries[1:], length)
    valid = right > left
    mid = (left[valid]+right[valid])/2
    half = (right[valid]-left[valid])/2
    u = (mid[:,None]+half[:,None]*nodes).ravel()
    du = (half[:,None]*np.broadcast_to(weights, (len(half), order))).ravel()
    base = du*np.exp(log_send_density(u, model))
    cu = quantize(lam*u, delta)
    if attack == "healthy":
        branches = [(u, np.ones_like(u))]
    elif attack == "cell_sign":
        gate = np.abs(lam*u-cu) < delta/2
        branches = [(u+eta*gate, np.full_like(u,.5)),
                    (u-eta*gate, np.full_like(u,.5))]
    else:
        target = 2*cu/lam-u
        acc = np.exp(np.minimum(0.0, log_send_density(target,model)-log_send_density(u,model)))
        branches = [(target,acc),(u,1-acc)]
    mean = second = pair = damage = action_probability = energy_mean = energy_second = 0.0
    for z, prob in branches:
        c, mu, var, var_energy, d = health_coefficients(z,model,delta)
        b0,b1,b2,b3,b4 = sent_moments(lam*u-c,s1,model["Z"])
        r1 = b1-mu*b0
        r2 = b2-2*mu*b1+mu*mu*b0
        r3 = b3-3*mu*b2+3*mu*mu*b1-mu**3*b0
        r4 = b4-4*mu*b3+6*mu*mu*b2-4*mu**3*b1+mu**4*b0
        a = -np.sign(d)/np.sqrt(var)
        b = 1/np.sqrt(var_energy)
        e = b*(r2-var*b0)
        e2 = b*b*(r4-2*var*r2+var*var*b0)
        g1 = a*r1+e
        g2 = a*a*r2+2*a*b*(r3-var*r1)+e2
        mass = base*prob
        mean += float(np.sum(mass*g1))
        second += float(np.sum(mass*g2))
        pair += float(np.sum(mass*b0))
        energy_mean += float(np.sum(mass*e))
        energy_second += float(np.sum(mass*e2))
        damage += float(np.sum(mass*k*k*(z-u)**2))
        action_probability += float(np.sum(mass*(z!=u)))
    silent0 = (1+model["Z"]*s0)**(-.5)
    p0_silent = model["P0"]*(model["R"]+1/model["Z"])/(s0+1/model["Z"])
    s_silent1 = model["A"]**2*p0_silent+model["Q"]+model["R"]
    silent_branch_next = silent0*(1-(1+model["Z"]*s_silent1)**(-.5))
    return {"E_score": mean, "E_score2": second,
            "E_energy_feature": energy_mean, "E_energy_feature2": energy_second,
            "P_pair_send": pair, "P_next_send": pair+silent_branch_next,
            "target_damage":damage, "action_probability":action_probability,
            "order":order,"u_truncation_sd":10,"y_moments":"analytic full Gaussian integrals"}


def run_experiment() -> None:
    if RESULTS.exists():
        raise SystemExit("Result directory already exists; refusing rerun or overwrite.")
    manifest = verify_inputs()
    RESULTS.mkdir(parents=True)
    (RESULTS / "raw").mkdir()
    (RESULTS / "calibration").mkdir()
    preflight = {
        "protocol_sha256": sha(PROTOCOL_PATH),
        "script_sha256": sha(Path(__file__)),
        "input_manifest_sha256": sha(INPUT_MANIFEST),
        "input_files": manifest["files"],
        "run_started": True,
        "simulations": "New fixed-design two-time experiment; no changes after inputs were frozen.",
    }
    write_json(RESULTS / "run_preflight.json", preflight)
    protocol = read_protocol()
    model_by_id = {m["id"]: m for m in protocol["models"]}
    calibration = {}
    raw_cal = {}
    try:
        # Independent healthy calibration.
        for mid, model in model_by_id.items():
            arrays = dict(np.load(INPUTS / f"cal_{mid}.npz"))
            for delta in model["delta_grid"]:
                out = simulate(model, {k:v for k,v in arrays.items() if k != "audit_u"}, delta)
                h = out["healthy"]
                vals = h["score"][h["available"]]
                threshold = conformal_threshold(vals, .01)
                key = f"{mid}_{delta:.12g}"
                calibration[key] = {"single_threshold": threshold,
                                    "n_healthy_available": int(len(vals)),
                                    "n_healthy_episodes": int(len(arrays["x0"])),
                                    "available_rate": float(np.mean(h["available"]))}
                raw_cal[key] = {
                    "score": h["score"], "feature_oriented": h["feature_oriented"],
                    "feature_energy": h["feature_energy"], "available": h["available"],
                    "send0": h["send0"], "send1": h["send1"]}
        write_json(RESULTS / "calibration_thresholds.json", calibration)
        for key, data in raw_cal.items():
            np.savez_compressed(RESULTS / "calibration" / f"{key}.npz", **data)

        rows, window_rows, planning_rows, auth_rows, audit_checks = [], [], [], [], []
        for mid, model in model_by_id.items():
            arrays = dict(np.load(INPUTS / f"test_{mid}.npz"))
            cal_audit_uniform = dict(np.load(INPUTS / f"cal_{mid}.npz"))["audit_u"]
            n = len(arrays["x0"])
            for delta in model["delta_grid"]:
                key = f"{mid}_{delta:.12g}"
                out = simulate(model, {k:v for k,v in arrays.items() if k != "audit_u"}, delta)
                h = out["healthy"]
                for attack in protocol["attacks"]:
                    item=out[attack]
                    assert np.all(np.abs(item["action"]) <= protocol["b"])
                    assert np.array_equal(h["c1"],item["c1"]), "Attack crossed a cell"
                    assert np.array_equal(h["send0"],item["send0"])
                    assert np.array_equal(h["send1"],item["send1"])
                    assert np.array_equal(h["P0_post"],item["P0_post"])
                    assert np.array_equal(h["P1_post"],item["P1_post"])
                    assert np.isfinite(item["score"]).all()
                    assert np.all(item["action"][~item["send0"]]==0)
                audit_checks.append({"case":key,"attack_timing_budget_and_B_path_identity":"PASS"})
                np.savez_compressed(RESULTS / "raw" / f"{key}_healthy.npz",
                    **{k:h[k] for k in ["score","feature_oriented","feature_energy","available",
                                       "send0","send1","mse","c1","P0_post","P1_post","m1_post"]})
                threshold = calibration[key]["single_threshold"]
                # Empirical health test-set FPR is reported, never used to retune.
                hvals = h["score"][h["available"]]
                h_alarm = hvals > threshold
                for attack in ["cell_sign", "balanced_reflection"]:
                    a = out[attack]
                    np.savez_compressed(RESULTS / "raw" / f"{key}_{attack}.npz",
                        score=a["score"], feature_oriented=a["feature_oriented"],
                        feature_energy=a["feature_energy"], available=a["available"],
                        send0=a["send0"], send1=a["send1"],
                        action=a["action"], damage_paired=a["damage_paired"],
                        cell_gate=a["cell_gate"], reflection_accept=a["reflection_accept"],
                        reflection_boundary=a["reflection_boundary"],
                        c1=a["c1"],P0_post=a["P0_post"],P1_post=a["P1_post"],
                        m1_post=a["m1_post"],mse=a["mse"])
                    auth_rows.append({
                        "model":mid,"delta":delta,"attempted_attack":attack,
                        "baseline":"ALL_AUTH_target_and_next",
                        "damage":0.0,"mse":float(np.mean(h["mse"])),
                        "auth_packets_per_episode":float(np.mean(
                            h["send0"].astype(int)+h["send1"].astype(int))),
                        "ideal_rejected_modifications_per_episode":float(np.mean(a["action"]!=0)),
                        "rejection_given_actual_nonzero_modification":1.0,
                        "residual_detection_rate":"not applicable: attack prevented before update",
                    })
                    for rho in protocol["audit_probabilities"]:
                        audit = arrays["audit_u"] < rho
                        eligible = audit & a["available"]
                        alarms = eligible & (a["score"] > threshold)
                        health_eligible = audit & h["available"]
                        health_alarm = health_eligible & (h["score"] > threshold)
                        ci_cond = score_row(int(np.sum(alarms)), int(np.sum(eligible)), .01)
                        ci_ep = score_row(int(np.sum(alarms)), n, .01)
                        hcond = score_row(int(np.sum(health_alarm)), int(np.sum(health_eligible)), .01)
                        hep = score_row(int(np.sum(health_alarm)), n, .01)
                        rows.append({
                            "model": mid, "delta": delta, "attack": attack, "rho": rho,
                            "n_episodes": n, "threshold_health_calibration": threshold,
                            "n_audited": int(np.sum(audit)),
                            "next_payload_audit_fraction": float(np.mean(audit & a["send1"])),
                            "paired_usable_fraction": float(np.mean(eligible)),
                            "next_send_given_audit": (float(np.mean(a["send1"][audit]))
                                                      if np.any(audit) else None),
                            "attack_action_rate": float(np.mean(a["action"] != 0)),
                            "attack_action_mean_abs": float(np.mean(np.abs(a["action"]))),
                            "damage_mean": float(np.mean(a["damage_paired"])),
                            "damage_paired_se":float(np.std(a["damage_paired"],ddof=1)/np.sqrt(n)),
                            "healthy_mse": float(np.mean(h["mse"])),
                            "attacked_mse": float(np.mean(a["mse"])),
                            "auth_packets_random_audit": float(np.mean(audit & a["send1"])),
                            "damage_model_formula_mean":float(np.mean(
                                (model["P0"]/(model["P0"]+model["R"]))**2*a["action"]**2)),
                            "auth_packets_all_auth": float(np.mean(a["send0"].astype(int)+a["send1"].astype(int))),
                            "base_packets": float(np.mean(a["send0"].astype(int)+a["send1"].astype(int))),
                            "auth_packet_fraction_vs_all_auth":
                                float(np.mean(audit & a["send1"]) / np.mean(a["send0"].astype(int)+a["send1"].astype(int))),
                            "tag_bytes_per_episode_illustrative":protocol["illustrative_tag_bytes"]*
                                float(np.mean(audit & a["send1"])),
                            "audit_flag_logical_bits_per_episode":1 if rho not in (0,1) else 0,
                            "alert_difference_vs_health_paired":float(np.mean(
                                alarms.astype(int)-health_alarm.astype(int))),
                            "alert_difference_paired_se":float(np.std(
                                alarms.astype(int)-health_alarm.astype(int),ddof=1)/np.sqrt(n)),
                            "single_test_fpr_conditional":
                                score_row(int(np.sum(h_alarm)), int(np.sum(h["available"])), .01),
                            "single_test_fpr_per_episode":
                                score_row(int(np.sum(health_alarm)), n, .01),
                            "conditional_detection": ci_cond,
                            "per_episode_detection": ci_ep,
                            "conditional_fpr_random_audit": hcond,
                            "per_episode_fpr_random_audit": hep,
                            "fpr_target_conditional": .01,
                            "window_detection_deferred": "see window_results.csv",
                        })

                        for bsize in protocol["window_sizes"]:
                            nc = (len(raw_cal[key]["score"]) // bsize) * bsize
                            cal_h = raw_cal[key]["score"][:nc].copy()
                            cal_av = raw_cal[key]["available"][:nc]
                            cal_u = cal_audit_uniform[:nc]
                            cal_vec = np.where(cal_av & (cal_u < rho), cal_h, 0.0)
                            cal_blocks = cal_vec.reshape(-1, bsize).sum(axis=1)/np.sqrt(bsize)
                            wth = conformal_threshold(cal_blocks, .01)
                            nt = (n // bsize) * bsize
                            hvec = np.where(h["available"][:nt] & (arrays["audit_u"][:nt] < rho),
                                            h["score"][:nt], 0.0)
                            avec = np.where(a["available"][:nt] & (arrays["audit_u"][:nt] < rho),
                                            a["score"][:nt], 0.0)
                            hb = hvec.reshape(-1, bsize).sum(axis=1)/np.sqrt(bsize)
                            ab = avec.reshape(-1, bsize).sum(axis=1)/np.sqrt(bsize)
                            window_rows.append({
                                "model": mid, "delta": delta, "attack": attack, "rho": rho,
                                "episodes_per_nonoverlap_block": bsize, "blocks_test": len(ab),
                                "threshold_healthy_calibration": wth,
                                "test_fpr": score_row(int(np.sum(hb > wth)), len(hb), .01),
                                "detection_rate": score_row(int(np.sum(ab > wth)), len(ab), .01),
                                "mean_audited_next_samples_per_block": float(np.mean(
                                    ((arrays["audit_u"][:nt]<rho)&a["send1"][:nt])
                                    .reshape(-1,bsize).sum(axis=1))),
                                "mean_usable_paired_samples_per_block": float(np.mean(
                                    ((arrays["audit_u"][:nt]<rho)&a["available"][:nt])
                                    .reshape(-1,bsize).sum(axis=1))),
                            })

                # Quadrature moments at fixed orders; not used to adjust thresholds.
                for attack in ["healthy", "cell_sign", "balanced_reflection"]:
                    q16 = weighted_quadrature(model, delta, attack, 16)
                    q32 = weighted_quadrature(model, delta, attack, 32)
                    planning_rows.append({
                        "model": mid, "delta": delta, "attack": attack,
                        "quadrature16": q16, "quadrature32": q32,
                        "mean_score_abs_diff": abs(q16["E_score"]-q32["E_score"]),
                        "second_moment_abs_diff": abs(q16["E_score2"]-q32["E_score2"]),
                        "no_samples_generated_for_quadrature": True,
                    })
                for attack in ["cell_sign", "balanced_reflection"]:
                    qa = weighted_quadrature(model, delta, attack, 32)
                    qh = weighted_quadrature(model, delta, "healthy", 32)
                    mu0, e20 = qh["E_score"], qh["E_score2"]
                    mua, e2a = qa["E_score"], qa["E_score2"]
                    effect = mua-mu0
                    for rho in protocol["audit_probabilities"]:
                        if rho == 0 or effect <= 0:
                            nplan = None
                        else:
                            v0 = max(1e-18, rho*e20-rho*rho*mu0*mu0)
                            va = max(1e-18, rho*e2a-rho*rho*mua*mua)
                            nplan = math.ceil(((Z99_ONE_SIDED*math.sqrt(v0)+Z80*math.sqrt(va))
                                               /(rho*effect))**2)
                        usable = rho*qa["P_pair_send"]
                        next_audit = rho*qa["P_next_send"]
                        planning_rows.append({
                            "model": mid, "delta": delta, "attack": attack, "rho": rho,
                            "healthy_score_mean_no_audit": mu0,
                            "attack_score_mean_no_audit": mua,
                            "difference_no_audit": effect,
                            "planned_episodes_for_1pct_fpr_80pct_power_normal_approx": nplan,
                            "planned_effective_paired_audits": (nplan*usable if nplan else None),
                            "planned_next_auth_packets": (nplan*next_audit if nplan else None),
                            "planning_scope": "independent episodes, one-sided CLT approximation; not empirical guarantee",
                        })
                print(mid, delta, "completed", flush=True)
        for name, content in [
            ("single_test_results.csv", rows),
            ("window_results.csv", window_rows),
            ("full_auth_results.csv", auth_rows),
            ("quadrature_and_sample_planning.json", planning_rows),
        ]:
            if name.endswith(".csv"):
                with (RESULTS / name).open("w", encoding="utf-8-sig", newline="") as stream:
                    fields = sorted({key for row in content for key in row})
                    writer = csv.DictWriter(stream, fieldnames=fields)
                    writer.writeheader()
                    for row in content:
                        writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v,(dict,list))
                                         else v for k,v in row.items()})
            else:
                write_json(RESULTS / name, content)
        checks = {
            "n_test_episodes_per_model": protocol["test_episodes"],
            "single_sample_test_rows": len(rows),
            "window_rows": len(window_rows),
            "planning_rows": len(planning_rows),
            "simulation_completed": True,
            "calibration_thresholds_saved": True,
            "no_thresholds_refit_on_test": True,
            "sample_unit": "independent two-time episode; rho configurations share base paths and are paired",
        }
        write_json(RESULTS / "run_completion.json", checks)
        write_json(RESULTS / "runtime_assertions.json",audit_checks)
        # Hash every immutable output before the validation file exists.
        hashes = {p.relative_to(RESULTS).as_posix(): sha(p)
                  for p in sorted(RESULTS.rglob("*")) if p.is_file()
                  and p.name != "result_manifest.json"}
        write_json(RESULTS / "result_manifest.json", {
            "protocol_sha256": sha(PROTOCOL_PATH),
            "script_sha256": sha(Path(__file__)),
            "input_manifest_sha256": sha(INPUT_MANIFEST),
            "files_sha256": hashes,
            "simulations_executed": True,
            "parameter_changes_after_freeze": False,
            "threshold_changes_after_calibration": False,
        })
        print(json.dumps(checks, ensure_ascii=True, indent=2))
    except Exception:
        write_json(RESULTS / "failure_record.json", {
            "status": "FAIL", "traceback": traceback.format_exc(),
            "inputs_preserved": True, "samples_deleted": False,
        })
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["freeze", "generate", "run"])
    args = parser.parse_args()
    if args.command == "freeze":
        freeze()
    elif args.command == "generate":
        generate_inputs()
    else:
        run_experiment()


if __name__ == "__main__":
    main()
