"""Tests for the independent E2 state adapter; no RNG or trajectory generation."""
from __future__ import annotations
import argparse
import copy
import json
import math
from pathlib import Path
import sys
from unittest.mock import patch

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e2_status_adapter as adapter
import v2_estimators as frozen


def public_model():
    events = []
    for i in range(8):
        O = np.zeros((12, 2))
        O[:2] = (10.0+i)*np.eye(2)
        Sthz = np.zeros((2, 12))
        Sthz[:, :2] = .02*np.eye(2)
        events.append({"edge": 0 if i % 2 == 0 else 3,
                       "r": 176+i, "O": O, "G": np.eye(2),
                       "Sigma_zz": 2.0*np.eye(12),
                       "Sigma_theta_z": Sthz})
    return {"Sigma_eta": np.eye(12), "events": events,
            "G": [x["G"] for x in events],
            "prior": {"normal": .5, "each_event": .5/8},
            "t_Q": 11.536641991587517, "t_r": 26.498086492638055,
            "U": .051261}


def test_invalid_inputs_and_models_fail_closed():
    model = public_model()
    for method in adapter.METHODS:
        wrong = adapter.propose_adapted(np.zeros(11), model, 0.0, method)
        assert wrong.proposal_status == "INPUT_INVALID"
        assert wrong.validation_status == "INPUT_INVALID"
        assert np.all(wrong.final_action == 0.0)
        nan = adapter.propose_adapted(np.array([math.nan]+[0.0]*11),
                                      model, 0.0, method)
        assert nan.proposal_status == "INPUT_INVALID"
        assert np.all(nan.final_action == 0.0)
    bad_sigma = copy.deepcopy(model)
    bad_sigma["Sigma_eta"][0, 0] = -1.0
    raw = frozen.propose(np.ones(12), model, "hard_gls_capped")
    adapted = adapter.adapt(raw, np.ones(12), bad_sigma, 0.0)
    assert adapted.proposal_status == "MODEL_INVALID"
    assert adapted.raw is raw and adapted.gated is not None
    assert np.all(adapted.final_action == 0.0)
    bad_event = copy.deepcopy(model)
    bad_event["events"][1]["O"] = np.zeros((11, 2))
    result = adapter.propose_adapted(np.ones(12), bad_event, 0.0,
                                     "hard_gls_capped")
    assert result.proposal_status == "MODEL_INVALID"
    assert np.all(result.final_action == 0.0)


def test_zero_unresolved_and_zero_proposal_are_distinct():
    model = public_model()
    raw_set = frozen.propose(np.zeros(12), model, "set_constrained_chebyshev")
    assert raw_set.certificate["zero_or_unresolved"] is True
    mapped = adapter.adapt(raw_set, np.zeros(12), model, 0.0)
    assert mapped.raw is raw_set
    assert mapped.proposal_status == "ZERO_OR_UNRESOLVED"
    assert mapped.gate_status == "GATE_REJECT"
    raw_zero = frozen.Proposal("hard_gls_capped", np.zeros(2), 2.0,
                               "VALID", None, {})
    mapped_zero = adapter.adapt(raw_zero, np.ones(12), model, 1.0)
    assert mapped_zero.proposal_status == "ZERO_PROPOSAL"
    assert mapped_zero.gate_status == "EXECUTED"
    assert mapped_zero.action_norm_after_gate == 0.0
    row = adapter.make_log_record(987654321, "normal", True,
                                  raw_zero.method, mapped_zero, 1.0,
                                  {"coverage_confirmed": False})
    assert row["gate_status"] == "EXECUTED" and not row["execution_success"]
    assert row["set_action_norm"] == 0.0


def test_solver_reject_and_coverage_remain_separate():
    model = public_model()
    raw = frozen.Proposal("set_constrained_chebyshev", np.zeros(2), 0.0,
                          "SOLVER_REJECT", None,
                          {"stage": "center", "reason": "iteration_limit",
                           "gap_squared": 1.0, "coverage_candidates": 8})
    adapted = adapter.adapt(raw, np.ones(12), model, 0.0)
    row = adapter.make_log_record(630000, "replay", True, raw.method,
                                  adapted, 0.0,
                                  {"event": [0, 200], "age": 64,
                                   "coverage_confirmed": True})
    assert row["raw_status"] == "SOLVER_REJECT"
    assert row["proposal_status"] == row["gate_status"] == "SOLVER_REJECT"
    assert row["coverage_confirmed"] is True
    assert row["solver_stage"] == "center" and row["solver_gap"] == 1.0
    assert row["compatible_event_count"] == 8 and not row["execution_success"]


def test_gate_uses_exact_raw_object_and_actions_match():
    model = public_model()
    for method in adapter.METHODS:
        z = np.ones(12)
        raw = frozen.propose(z, model, method)
        threshold = raw.score
        calls = []
        original_gate = frozen.apply_gate
        def watched(candidate, cut):
            calls.append(candidate)
            return original_gate(candidate, cut)
        with patch.object(frozen, "apply_gate", watched):
            equal = adapter.adapt(raw, z, model, threshold)
        assert calls == [raw] and calls[0] is equal.raw
        expected_reject = original_gate(raw, threshold)
        assert equal.gate_status == expected_reject.status == "GATE_REJECT"
        assert np.array_equal(equal.final_action, expected_reject.action)
        lower = adapter.adapt(raw, z, model, threshold-1e-12)
        expected_exec = original_gate(raw, threshold-1e-12)
        assert lower.gate_status == expected_exec.status
        assert np.array_equal(lower.final_action, expected_exec.action)
        assert lower.score_before_gate == raw.score
        assert lower.action_norm_before_gate == float(np.linalg.norm(raw.action))
        assert lower.action_norm_after_gate == float(np.linalg.norm(expected_exec.action))


def test_logger_schema_and_offline_fields_are_separate():
    model = public_model()
    raw = frozen.propose(np.zeros(12), model, "set_constrained_chebyshev")
    adapted = adapter.adapt(raw, np.zeros(12), model, 0.0)
    normal = adapter.make_log_record(
        610000, "normal", True, raw.method, adapted, 0.0,
        {"coverage_confirmed": True, "event": [0, 200], "age": 64})
    assert normal["event"] is None and normal["age"] is None
    assert normal["coverage_confirmed"] is None
    replay = adapter.make_log_record(
        630000, "replay", True, raw.method, adapted, 0.0,
        {"coverage_confirmed": True, "event": [0, 200], "age": 64})
    assert replay["event"] == [0, 200] and replay["age"] == 64
    assert replay["coverage_confirmed"] is True
    schema = json.loads((HERE.parent / "e2_log_schema.json").read_text(encoding="utf-8"))
    assert tuple(normal) == tuple(schema["fields"])
    assert tuple(replay) == adapter.LOG_FIELDS


def main(out: Path | None = None):
    tests = [test_invalid_inputs_and_models_fail_closed,
             test_zero_unresolved_and_zero_proposal_are_distinct,
             test_solver_reject_and_coverage_remain_separate,
             test_gate_uses_exact_raw_object_and_actions_match,
             test_logger_schema_and_offline_fields_are_separate]
    for test in tests:
        test()
        print(test.__name__, "PASS")
    result = {"result": "PASS_ADAPTER_UNIT_TESTS_ONLY",
              "tests_passed": len(tests),
              "test_names": [test.__name__ for test in tests],
              "new_random_trajectories": 0, "E2": False, "E3": False}
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n",
                       encoding="utf-8", newline="\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    main(args.out)
