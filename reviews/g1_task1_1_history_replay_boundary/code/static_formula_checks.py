"""Static algebra and archived-gain checks only; no simulated state/noise path."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    checks = []

    def check(name, passed, **details):
        if not passed:
            raise AssertionError(name)
        checks.append({"name": name, "status": "PASS", **details})

    theta = .12
    a = 1.01 * np.eye(2)
    eps = .08
    old, recent, now = np.array([0., 0.]), np.array([.6, 0.]), np.array([.1, 0.])
    check("strict_broadcast_history_age_counterexample",
          np.sum((recent-old)**2) > theta and np.sum((now-recent)**2) > theta
          and np.linalg.norm(old-now) < np.linalg.norm(recent-now),
          older_age=2, younger_age=1,
          older_norm=float(np.linalg.norm(old-now)), younger_norm=float(np.linalg.norm(recent-now)),
          scope="analytic estimate values; model support proven in report, not a generated trajectory")

    v = eps*a@np.array([-.124, 0.])
    e = np.array([-.34, 0.])
    g0 = float(e@e-theta)
    ga = float((e+v)@(e+v)-theta)
    check("timeout_masks_real_model_support_example", g0 < 0 < ga and 10-0 >= 10,
          g0=g0, ga=ga, h=v.tolist(), source_tick=0, injection_tick=9, decision_tick=10,
          sender_previous_packet=.6, sender_injection_packet=.124,
          sender_true_send=(.124-.6)**2 > theta)
    check("reference_cancellation_algebra_only",
          np.allclose(e+v-v, e, atol=1e-15, rtol=0),
          scope="not a claim that nonzero h=b is reachable by a legal single Replay")
    guard_cases = 0
    for g, dg, u in itertools.product([-.2, 0., .2], [-.3, 0., .3], [False, True]):
        direct = ((g>0) or u) != ((g+dg>0) or u)
        formula = (not u) and ((g<=0<g+dg) or (g>0>=g+dg))
        check_pass = direct == formula
        if abs(g) > abs(dg):
            check_pass = check_pass and ((g>0) == (g+dg>0))
        if not check_pass:
            raise AssertionError("strict_guard_OR")
        guard_cases += 1
    check("strict_guard_OR_and_margin_bound", True, cases=guard_cases)

    gain_path = HERE/"evidence/nominal_gains.npz"
    digest = hashlib.sha256(gain_path.read_bytes()).hexdigest()
    if digest != "7c636e9372461091c149818ab45a87b12920cccaff98669bf04b8388afbc0f33":
        raise AssertionError("archive gain SHA")
    with np.load(gain_path, allow_pickle=False) as archive:
        gains = archive["gains"]
    sv = np.linalg.svd(gains, compute_uv=False)
    check("gain_inverse_support_on_saved_horizon", sv.min() > 0,
          min_singular=float(sv.min()), max_singular=float(sv.max()),
          scope="saved k=0..399 only; gains not regenerated")

    # Form an algebraic operator at one archived time, not an estimator trajectory.
    edges = [(0,1),(1,0),(1,2),(2,1),(2,3),(3,2),(3,4),(4,3),(4,0),(0,4)]
    H = [s*np.eye(2) for s in [1.,.8,1.2,.9,1.1]]
    J = np.zeros((20,10))
    V = np.zeros((10,20))
    F = np.zeros((10,10))
    for edge,(sender,receiver) in enumerate(edges):
        J[edge*2:edge*2+2,sender*2:sender*2+2] = np.eye(2)
        V[receiver*2:receiver*2+2,edge*2:edge*2+2] = np.eye(2)
    for i in range(5):
        F[2*i:2*i+2,2*i:2*i+2] = a-gains[200,i]@H[i]-2*eps*a
    L = np.kron(np.eye(5),a)@V
    AE = np.kron(np.eye(10),a)
    inject = np.zeros((40,2))
    inject[2:4] = eps*a
    inject[20:22] = a
    W = np.zeros((2,40))
    W[:,2:4] = np.eye(2)
    W[:,12:14] = -np.eye(2)
    check("C_initial_injection_dimension_and_value", np.array_equal(W@inject,eps*a),
          injection_shape=list(inject.shape), selector_shape=list(W.shape))
    errors = []
    delta = np.array([-.3,.4])  # arithmetic vector, not a selected attack or new trajectory
    for bits in itertools.product([0,1],repeat=5):
        S = np.kron(np.diag(bits),np.eye(2))
        R = np.kron(np.diag([bits[j] for j,i in edges]),np.eye(2))
        M = np.block([
            [F+eps*L@R@J, np.zeros((10,10)), eps*L@(np.eye(20)-R)],
            [S,np.eye(10)-S,np.zeros((10,20))],
            [AE@R@J,np.zeros((20,10)),AE@(np.eye(20)-R)],
        ])
        C = W@M@inject
        d = M@(inject@delta)
        errors.append(float(np.max(np.abs(C@delta-(d[2:4]-d[12:14])))))
        vi = C@delta
        direct = float((e+vi)@(e+vi)-e@e)
        quadratic = float(2*e@C@delta+delta@C.T@C@delta)
        errors.append(abs(direct-quadratic))
    check("C_selects_h_minus_b_and_quadratic_form", max(errors)<1e-12,
          mode_count=32, max_abs_error=max(errors),
          scope="operator identity for enumerated modes; no reachability claim or mode trajectory")

    # Actual first-Replay values retained by Task 0.5; compare the two reset branches.
    task05 = HERE.parent/"g1_communication_behavior/task0_5"
    old = json.loads((task05/"01_data_integrity_audit.json").read_text(encoding="utf-8-sig"))
    row = next(r for r in old["summary"]["first_replay"]["all_rows"] if r["seed"]==40000)
    e0 = np.asarray(row["e0_trigger_difference"])
    h = np.asarray(row["state_observed"])
    reference_true = -e0  # Sa=0, S0=1, b=0
    reference_false_common = h
    check("post_split_common_matrix_reset_is_wrong", not np.allclose(reference_true,reference_false_common),
          seed=40000, decision_tick=203,
          correct_reference_difference=reference_true.tolist(),
          incorrect_common_mode_reference_difference=reference_false_common.tolist())

    output = {"status":"PASS", "scope":"static algebra plus archived matrices; no simulation/RNG",
              "check_groups":len(checks), "checks":checks}
    content = json.dumps(output,indent=2,ensure_ascii=False,allow_nan=False)+"\n"
    target = HERE/"data/static_formula_checks.json"
    if args.verify:
        if target.read_bytes() != content.encode("utf-8"):
            raise AssertionError("static output bytes differ")
        print("PASS: static formula checks reproduce")
    else:
        target.write_bytes(content.encode("utf-8"))
        print(json.dumps({"status":"PASS","check_groups":len(checks)}))


if __name__ == "__main__":
    main()
