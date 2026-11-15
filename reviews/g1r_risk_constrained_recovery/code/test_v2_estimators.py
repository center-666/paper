"""Deterministic fixed-case tests for the v2 proposal algorithms."""
from __future__ import annotations

import json
import math
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import v2_estimators as est


def public_model():
    eye = np.eye(2)
    events = []
    for edge, r, scale in [(0, 176, 1000.0), (3, 178, 900.0)]:
        O = scale * eye
        G = eye.copy()
        cross = 0.0005 * eye
        events.append({"edge": edge, "r": r, "O": O, "G": G,
                       "Sigma_theta_z": cross, "Sigma_zz": 2.0 * eye})
    return {"Sigma_eta": np.eye(2), "events": events, "G": [e["G"] for e in events],
            "prior": {"normal": 0.5, "each_event": 0.25},
            "t_Q": 11.536641991587517, "t_r": 26.498086492638055,
            "U": 0.051261}


def test_support_and_distance():
    e = est.Ellipse(np.array([2., 0.]), np.diag([.5, 0.]), (0, 1))
    assert np.allclose(est._support(e, np.array([1., 0.])), [2.5, 0.])
    assert np.allclose(est._support(e, np.array([-1., 0.])), [1.5, 0.])
    ellipses = [est.Ellipse(np.array([2., 0.]), np.zeros((2, 2)), (0, 1))]
    lo, hi, _, _ = est._distance_hull(ellipses)
    assert 2. - 1e-12 <= lo <= hi <= 2. + 1e-12


def test_zero_in_conflicting_convex_hull():
    ellipses = [est.Ellipse(np.array([2., 0.]), np.zeros((2, 2)), (0, 1)),
                est.Ellipse(np.array([-2., 0.]), np.zeros((2, 2)), (3, 2))]
    lo, hi, p, _ = est._distance_hull(ellipses)
    assert lo == 0. and hi < 1e-10 and np.linalg.norm(p) < 1e-10
    center, cert = est._chebyshev(ellipses, .5)
    assert np.allclose(center, [0., 0.], atol=1e-10)
    assert cert["gap_squared"] <= 1e-10


def test_trust_region_hard_case_and_general_dual():
    L = np.diag([2., 1.])
    lo, hi, v = est._trust_max(np.zeros(2), L, (0, 1))
    assert lo <= 4. <= hi and hi - lo <= 1e-10
    a = np.array([.3, -.7])
    L2 = np.array([[.7, .1], [.2, .4]])
    lo, hi, v = est._trust_max(a, L2, (0, 1))
    grid = np.linspace(0., 2.*math.pi, 20001)
    points = np.stack([np.cos(grid), np.sin(grid)])
    brute = np.max(np.sum((a[:, None] + L2 @ points) ** 2, axis=0))
    value_at_returned_point = float(np.linalg.norm(a + L2 @ v) ** 2)
    assert lo <= hi and hi - lo <= 1e-9
    assert lo <= value_at_returned_point <= hi
    # The angular grid is a lower approximation to the continuous trust
    # maximum; it is used only as a sanity check against the certified upper.
    assert brute <= hi + 1e-8


def test_common_proposal_interface():
    model = public_model()
    z = np.array([5., -2.])
    expected = {"hard_gls_capped", "correct_joint_soft_impact_capped",
                "set_constrained_chebyshev"}
    outputs = {name: est.propose(z, model, name) for name in expected}
    for name, out in outputs.items():
        assert out.method == name
        assert out.status == "VALID", (name, out.status, out.certificate)
        assert np.all(np.isfinite(out.action)) and np.isfinite(out.score)
        assert np.linalg.norm(out.action) <= model["U"] + 1e-14
        assert out.action.shape == (2,)
    assert outputs["set_constrained_chebyshev"].certificate["coverage_candidates"] == 2
    assert outputs["set_constrained_chebyshev"].certificate["gap_squared"] <= 1e-10
    gated = est.apply_gate(outputs["hard_gls_capped"], outputs["hard_gls_capped"].score)
    assert gated.status == "GATE_REJECT"  # strict threshold comparison
    executed = est.apply_gate(outputs["hard_gls_capped"], outputs["hard_gls_capped"].score - 1e-12)
    assert executed.status == "EXECUTED"
    invalid = est.propose(np.array([math.nan, 0.]), model, "hard_gls_capped")
    assert invalid.status == "INPUT_INVALID" and np.all(invalid.action == 0.)


def test_replay_event_compatibility_keeps_boundary():
    model = public_model()
    z = np.array([3., 1.])
    ellipses, rejected, boundary = est._build_set_ellipses(z, np.linalg.cholesky(model["Sigma_eta"]), model)
    assert len(ellipses) == 2 and not rejected
    assert set(boundary).issubset({e.event for e in ellipses})


def main():
    tests = [test_support_and_distance, test_zero_in_conflicting_convex_hull,
             test_trust_region_hard_case_and_general_dual,
             test_common_proposal_interface, test_replay_event_compatibility_keeps_boundary]
    for test in tests:
        test()
        print(test.__name__, "PASS")
    print(json.dumps({"result": "PASS_FIXED_DETERMINISTIC_TESTS_ONLY",
                      "test_count": len(tests), "trajectories": 0,
                      "random_seeds": [], "normal_calibration": False,
                      "E2": False, "E3": False}))


if __name__ == "__main__":
    main()
