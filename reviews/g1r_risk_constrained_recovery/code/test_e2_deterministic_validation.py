"""Stage B deterministic numerical and E2-statistics validation only."""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import test_v2_estimators as base_tests
import v2_estimators as est
import test_e2_statistics as stat_tests


def test_circle_centers_inside_and_outside_budget_ball():
    inside = [est.Ellipse(np.array([.3, .4]), .2*np.eye(2), (0, 1))]
    c, cert = est._chebyshev(inside, .8)
    assert np.allclose(c, [.3, .4], atol=2e-8)
    assert abs(cert["upper_squared"] - .04) < 2e-8
    outside = [est.Ellipse(np.array([1., 0.]), .2*np.eye(2), (0, 1))]
    c, cert = est._chebyshev(outside, .1)
    assert np.allclose(c, [.1, 0.], atol=2e-8)
    assert abs(cert["upper_squared"] - 1.21) < 2e-8


def test_degenerate_line_and_single_point_ellipses():
    line = [est.Ellipse(np.array([2., 0.]), np.diag([.5, 0.]), (0, 1))]
    c, cert = est._chebyshev(line, .5)
    assert np.allclose(c, [.5, 0.], atol=2e-8)
    assert abs(cert["upper_squared"] - 4.) < 2e-8
    point = [est.Ellipse(np.array([.4, .2]), np.zeros((2, 2)), (0, 1))]
    c, cert = est._chebyshev(point, .5)
    assert np.allclose(c, [.4, .2], atol=2e-8)
    assert cert["upper_squared"] < 1e-10


def test_common_cap_boundary_and_opposite_direction_conflict():
    point = [est.Ellipse(np.array([10., 2.]), np.zeros((2, 2)), (0, 1))]
    c, cert = est._chebyshev(point, .05)
    assert abs(np.linalg.norm(c)-.05) < 1e-12
    assert cert["gap_squared"] <= 1e-10
    opposite = [est.Ellipse(np.array([2., 0.]), np.zeros((2, 2)), (0, 1)),
                est.Ellipse(np.array([-2., 0.]), np.zeros((2, 2)), (3, 2))]
    c, cert = est._chebyshev(opposite, .5)
    assert np.linalg.norm(c) < 1e-10
    assert cert["gap_squared"] <= 1e-10


def test_solver_resource_exhaustion_and_nonfinite_fail_closed():
    sets = [est.Ellipse(np.array([2., .3]), np.diag([.2, .1]), (0, 1)),
            est.Ellipse(np.array([-1., 1.]), np.diag([.1, .3]), (3, 2))]
    for call, stage in [(lambda: est._distance_hull(sets, max_iter=1), "hull"),
                        (lambda: est._chebyshev(sets, .05, max_iter=1), "center")]:
        try:
            call()
        except est.SolverReject as exc:
            assert exc.details["stage"] == stage
            assert exc.details["reason"] == "iteration_limit"
            assert exc.details["gap"] > 0
        else:
            raise AssertionError("resource exhaustion was not an explicit reject")
    model = base_tests.public_model()
    for method in ["hard_gls_capped", "correct_joint_soft_impact_capped",
                   "set_constrained_chebyshev"]:
        proposal = est.propose(np.array([math.nan, 0.]), model, method)
        assert proposal.status in {"INPUT_INVALID", "MODEL_INVALID"}
        assert np.all(proposal.action == 0.)


def test_zero_unresolved_status_is_visible_in_certificate():
    model = base_tests.public_model()
    proposal = est.propose_set(np.zeros(2), model)
    assert proposal.status == "VALID"
    assert proposal.score == 0.0
    assert np.all(proposal.action == 0.0)
    assert proposal.certificate["zero_or_unresolved"] is True
    # The frozen status contract separately names ZERO_OR_UNRESOLVED; the
    # current output uses VALID plus this certificate flag. Stage A/B report
    # records this schema mismatch for owner review.
    soft_invalid = est.propose_soft(np.array([math.nan, 0.0]), model)
    assert soft_invalid.status == "MODEL_INVALID"
    assert np.all(soft_invalid.action == 0.0)


def test_all_geometry_tests():
    for fn in [base_tests.test_support_and_distance,
               base_tests.test_zero_in_conflicting_convex_hull,
               base_tests.test_trust_region_hard_case_and_general_dual,
               base_tests.test_common_proposal_interface,
               base_tests.test_replay_event_compatibility_keeps_boundary]:
        fn()


def main(out: Path | None = None):
    tests = [test_circle_centers_inside_and_outside_budget_ball,
             test_degenerate_line_and_single_point_ellipses,
             test_common_cap_boundary_and_opposite_direction_conflict,
             test_solver_resource_exhaustion_and_nonfinite_fail_closed,
             test_zero_unresolved_status_is_visible_in_certificate,
             test_all_geometry_tests,
             stat_tests.test_beta_and_binomial_tail_formulas_agree,
             stat_tests.test_frozen_e2_count_boundaries,
             stat_tests.test_gate_uses_full_denominator_and_frozen_counts,
             stat_tests.test_failed_rows_stay_in_count_denominators,
             stat_tests.test_seed_or_row_deletion_is_rejected,
             stat_tests.test_frozen_seed_contract_is_not_injectable]
    for fn in tests:
        fn()
        print(fn.__name__, "PASS")
    record = {
        "result": "PASS_DETERMINISTIC_TESTS_WITH_STATUS_CONTRACT_FINDINGS",
        "tests_passed": len(tests),
        "test_names": [fn.__name__ for fn in tests],
        "findings": [
            "Set zero/unresolved returns VALID with certificate flag instead of frozen ZERO_OR_UNRESOLVED state",
            "Soft nonfinite z returns MODEL_INVALID instead of INPUT_INVALID; action still fails closed to zero",
        ],
        "new_random_trajectories": 0, "E2": False, "E3": False,
    }
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(record, ensure_ascii=False, indent=2)+"\n",
                       encoding="utf-8", newline="\n")
    print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    main(args.out if args.out is None or args.out.is_absolute() else ROOT / args.out)
