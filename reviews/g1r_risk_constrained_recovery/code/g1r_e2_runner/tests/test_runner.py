from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from ..authorization_guard import (AuthorizationError, RunAuthorization, authorize,
                                   require_formal_e2)
from ..batch_runner import BatchRunner
from ..checkpoint_manager import CheckpointError, CheckpointManager
from ..cli import build_parser
from ..config_loader import BASE, load_frozen_config, load_public_model
from ..integrity_checker import IntegrityError, validate_batch_rows
from ..offline_evaluator import evaluate, set_union_covers
from ..online_proposal import (OnlineInput, build_online_input, failed_proposal_record,
                               propose, record_dict)
from ..result_writer import write_exclusive
from ..scenario_builder import ScenarioBuilder


class RunnerAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load_frozen_config()
        cls.public_model = load_public_model(cls.config)
        cls.builder = ScenarioBuilder(cls.config, cls.public_model)
        cls.fixture = cls.builder.build_fixture_pair(0)

    def _record(self, case, method):
        online = build_online_input(case.online_input.z, self.public_model,
                                    self.config.thresholds[method], method)
        return online, propose(online)

    def test_normal_replay_fixture_reproduces_exactly(self):
        again = self.builder.build_fixture_pair(0)
        self.assertEqual(self.fixture.normal.online_input.z, again.normal.online_input.z)
        self.assertEqual(self.fixture.replay.online_input.z, again.replay.online_input.z)
        self.assertEqual(self.fixture.timing_checks, again.timing_checks)
        self.assertEqual(self.fixture.normal.offline_truth.healthy_target_estimate,
                         again.normal.offline_truth.healthy_target_estimate)

    def test_frozen_main_replay_timing_and_source_are_valid(self):
        checks = self.fixture.timing_checks
        self.assertEqual(checks["edge"], 0)
        self.assertEqual(checks["replay_time"], 200)
        self.assertEqual(checks["source_time"], 136)
        self.assertEqual(checks["actual_age"], 64)
        self.assertEqual(checks["cache_replacement_time"], 208)
        self.assertEqual(checks["first_pollution_state"], 201)
        self.assertEqual(checks["first_receiver_pollution_state"], 201)
        self.assertEqual(checks["innovation_times"], [211, 212, 213, 214, 215, 216])
        self.assertEqual(checks["decision_time"], 216)
        self.assertEqual(checks["target_time"], 217)
        self.assertTrue(checks["source_and_replay_are_sent"])
        self.assertTrue(checks["single_replacement"])

    def test_all_eight_events_and_three_ages_use_legal_historical_sends(self):
        grid = self.builder.build_fixture_grid(0)
        observed = set()
        for case, checks in zip(grid.replays, grid.timing_checks):
            truth = case.offline_truth
            observed.add((truth.event, truth.age))
            self.assertEqual(checks["source_time"], truth.event[1] - truth.age)
            self.assertEqual(checks["actual_age"], truth.age)
            self.assertGreater(checks["cache_replacement_time"], truth.event[1])
            self.assertTrue(checks["source_and_replay_are_sent"])
            self.assertTrue(checks["single_replacement"])
        expected = {(event, age) for event in self.config.events for age in self.config.ages}
        self.assertEqual(observed, expected)

    def test_innovation_is_twelve_finite_values(self):
        for case in (self.fixture.normal, self.fixture.replay):
            z = np.asarray(case.online_input.z)
            self.assertEqual(z.shape, (12,))
            self.assertTrue(np.all(np.isfinite(z)))

    def test_online_information_object_is_whitelisted(self):
        online = self.fixture.replay.online_input
        self.assertIs(type(online), OnlineInput)
        self.assertEqual(set(vars(online)), {"z", "frozen_public_model", "threshold", "method"})
        serialized = json.dumps(record_dict(propose(online)))
        for forbidden in ("true_state", "true_event", "true_theta", "true_replay_age",
                          "replay_source", "healthy_counterfactual", "future_measurements",
                          "whole_run_object", "offline_truth", "seed", "cache_replacement_time"):
            self.assertNotIn(forbidden, vars(online))
            self.assertNotIn(forbidden, serialized)
        with self.assertRaises(TypeError):
            propose(self.fixture)  # SceneCase bundles online and offline data.

    def test_hard_output_matches_frozen_estimator(self):
        self._assert_estimator_match("hard_gls_capped")

    def test_soft_output_matches_frozen_estimator(self):
        self._assert_estimator_match("correct_joint_soft_impact_capped")

    def test_set_output_matches_frozen_estimator(self):
        self._assert_estimator_match("set_constrained_chebyshev")

    def _assert_estimator_match(self, method):
        import sys
        sys.path.insert(0, str(BASE / "code"))
        import v2_estimators
        case = self.fixture.replay
        online, adapted = self._record(case, method)
        raw = v2_estimators.propose(np.asarray(online.z), online.frozen_public_model, method)
        gated = v2_estimators.apply_gate(raw, online.threshold)
        self.assertEqual(adapted.raw_status, raw.status)
        self.assertEqual(adapted.score, raw.score)
        self.assertEqual(adapted.proposal_vector, tuple(map(float, raw.action)))
        self.assertEqual(adapted.gate_status, gated.status)
        self.assertEqual(adapted.final_action, tuple(map(float, gated.action)))

    def test_status_adapter_preserves_gate_and_uses_post_gate_action(self):
        _, record = self._record(self.fixture.replay, "hard_gls_capped")
        self.assertEqual(record.action_norm_after_gate,
                         float(np.linalg.norm(record.final_action)))
        if record.gate_status != "EXECUTED":
            self.assertEqual(record.action_norm_after_gate, 0.0)
        self.assertEqual(record.validation_status, "VALID")

    def test_common_cap_applies_to_raw_and_executed_actions(self):
        cap = float(self.config.protocol["U_common"])
        for method in self.config.methods:
            _, record = self._record(self.fixture.replay, method)
            self.assertLessEqual(np.linalg.norm(record.proposal_vector), cap + 1e-12)
            self.assertLessEqual(np.linalg.norm(record.final_action), cap + 1e-12)
        self.assertEqual(cap, 0.051261)

    def test_solver_reject_is_fail_closed(self):
        import sys
        sys.path.insert(0, str(BASE / "code"))
        import v2_estimators
        original = v2_estimators.propose
        rejected = v2_estimators.Proposal("set_constrained_chebyshev", np.ones(2), 2.0,
                                           "SOLVER_REJECT", None,
                                           {"stage": "center", "reason": "test_reject",
                                            "gap_squared": 1.0})
        with patch.object(v2_estimators, "propose", return_value=rejected):
            record = propose(build_online_input(
                self.fixture.replay.online_input.z, self.public_model, 0.0,
                "set_constrained_chebyshev"))
        self.assertEqual(record.raw_status, "SOLVER_REJECT")
        self.assertEqual(record.proposal_status, "SOLVER_REJECT")
        self.assertEqual(record.action_norm_after_gate, 0.0)
        self.assertEqual(record.final_action, (0.0, 0.0))
        self.assertFalse(record.execution_success)
        self.assertIsNotNone(original)

    def test_proposal_record_is_immutable_and_contains_no_truth_fields(self):
        _, record = self._record(self.fixture.replay, "set_constrained_chebyshev")
        with self.assertRaises(FrozenInstanceError):
            record.gate_status = "EXECUTED"
        output = record_dict(record)
        for field in ("event", "age", "seed", "true_impact", "replay_source_time"):
            self.assertNotIn(field, output)

    def test_offline_coverage_is_independent_of_center_solver_status(self):
        import sys
        sys.path.insert(0, str(BASE / "code"))
        import v2_estimators
        case = self.fixture.replay
        z = np.asarray(case.online_input.z)
        sigma = np.asarray(self.public_model["Sigma_eta"])
        ellipses, _, _ = v2_estimators._build_set_ellipses(
            z, np.linalg.cholesky(sigma), self.public_model)
        self.assertTrue(ellipses)
        truth = replace(case.offline_truth, true_impact=tuple(map(float, ellipses[0].center)))
        failed = failed_proposal_record("set_constrained_chebyshev", 0.0, "center_test_reject", z)
        row = evaluate(failed, truth, self.public_model)
        self.assertTrue(row["coverage_confirmed"])
        self.assertEqual(row["proposal_status"], "MODEL_INVALID")
        self.assertEqual(row["set_action_norm"], 0.0)
        covered, count = set_union_covers(z, self.public_model, truth.true_impact)
        self.assertTrue(covered)
        self.assertGreater(count, 0)

    def test_duplicate_and_missing_batch_seed_rows_are_rejected(self):
        with self.assertRaises(IntegrityError):
            validate_batch_rows(self.config, "normal", (900000, 900000), [])
        with self.assertRaises(IntegrityError):
            validate_batch_rows(self.config, "normal", (900000, 900001), [])

    def test_duplicate_row_key_is_rejected(self):
        base = {
            "seed": 900000, "scenario": "normal", "main_case": True,
            "event": None, "age": None, "method": self.config.methods[0],
            "final_action_json": "[0.0,0.0]", "set_action_norm": 0.0,
            "proposal_status": "ZERO_PROPOSAL", "gate_status": "GATE_REJECT",
            "execution_success": False, "simulation_status": "PASS",
            "statistical_cluster": "normal:900000",
        }
        rows = [dict(base, sample_id=f"s{i}") for i in range(3)]
        rows[1]["method"] = rows[0]["method"]
        rows[2]["method"] = self.config.methods[1]
        with self.assertRaises(IntegrityError):
            validate_batch_rows(self.config, "normal", (900000,), rows)

    def _synthetic_grid(self, group: str, seed: int = 900000):
        rows = []
        methods = self.config.methods
        if group == "normal":
            cells = [(None, None)]
        else:
            cells = [(event, age) for event in self.config.events for age in self.config.ages]
        for event, age in cells:
            for method in methods:
                main = (group == "normal" or (event == self.config.main_event and age == 64))
                rows.append({
                    "seed": seed, "scenario": group if group == "normal" else "replay",
                    "main_case": main, "event": None if event is None else list(event),
                    "age": age, "method": method, "final_action_json": "[0.0,0.0]",
                    "set_action_norm": 0.0, "proposal_status": "SOLVER_REJECT",
                    "gate_status": "SOLVER_REJECT", "execution_success": False,
                    "simulation_status": "FAIL:deterministic_fixture",
                    "statistical_cluster": f"{group}:{seed}",
                    "coverage_confirmed": None if group == "normal" else False,
                    "true_impact_x": None,
                })
        return rows

    def test_integrity_accepts_complete_paired_event_age_fixture_grid(self):
        normal = self._synthetic_grid("normal")
        attack = self._synthetic_grid("attack")
        validate_batch_rows(self.config, "normal", (900000,), normal)
        validate_batch_rows(self.config, "attack", (900000,), attack)
        self.assertEqual(len(normal), 3)
        self.assertEqual(len(attack), 72)

    def test_integrity_rejects_missing_event_age_or_method_row(self):
        attack = self._synthetic_grid("attack")
        with self.assertRaises(IntegrityError):
            validate_batch_rows(self.config, "attack", (900000,), attack[:-1])

    def test_fixed_batch_plan_is_twenty_batches_of_twenty(self):
        runner = BatchRunner(self.config, authorize("dry_run", self.config),
                             Path(tempfile.gettempdir()) / "g1r-e2-plan-only")
        plan = runner._batch_plan()
        self.assertEqual(len(plan), 20)
        self.assertEqual([len(row[2]) for row in plan], [20] * 20)
        self.assertEqual(plan[0][2][0], self.config.normal_seeds[0])
        self.assertEqual(plan[9][2][-1], self.config.normal_seeds[-1])
        self.assertEqual(plan[10][2][0], self.config.attack_seeds[0])
        self.assertEqual(plan[19][2][-1], self.config.attack_seeds[-1])

    def test_checkpoint_resumes_without_replacing_completed_seed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkpoint_path = root / "checkpoint.json"
            online = root / "online.jsonl"
            offline = root / "offline.csv"
            online_sha = write_exclusive(online, b"online\n")
            offline_sha = write_exclusive(offline, b"offline\n")
            first = CheckpointManager(checkpoint_path, "dry-test", "dry_run")
            first.mark_seed_complete("normal", 900000, online, online_sha,
                                     offline, offline_sha)
            resumed = CheckpointManager(checkpoint_path, "dry-test", "dry_run")
            self.assertTrue(resumed.seed_is_complete("normal", 900000, online, offline))
            with self.assertRaises(CheckpointError):
                resumed.mark_seed_complete("normal", 900000, online, "0" * 64,
                                           offline, offline_sha)

    def test_interrupted_online_shard_is_reused_without_overwrite(self):
        from ..result_writer import ResultWriter
        case = self.fixture.normal
        online = build_online_input(case.online_input.z, self.public_model,
                                    self.config.thresholds[self.config.methods[0]],
                                    self.config.methods[0])
        record = propose(online)
        with tempfile.TemporaryDirectory() as directory:
            writer = ResultWriter(Path(directory))
            online_path, first_sha = writer.write_online_seed(
                "normal", 0, 900000, [record])
            # Simulate restart: deterministic re-computation must byte-match the orphan shard.
            resumed_path, resumed_sha = writer.write_online_seed(
                "normal", 0, 900000, [record])
            self.assertEqual((online_path, first_sha), (resumed_path, resumed_sha))
            truth = replace(case.offline_truth, seed=900000,
                            statistical_cluster="normal:900000")
            row = evaluate(record, truth, self.public_model)
            row["online_record_ordinal"] = 0
            row["trial_run_id"] = "dry-test:normal:900000"
            offline_path, offline_sha = writer.write_offline_seed(
                "normal", 0, 900000, [row])
            checkpoint = CheckpointManager(Path(directory) / "checkpoint.json",
                                           "dry-test", "dry_run")
            checkpoint.mark_seed_complete("normal", 900000, online_path, first_sha,
                                          offline_path, offline_sha)
            restarted = CheckpointManager(Path(directory) / "checkpoint.json",
                                         "dry-test", "dry_run")
            self.assertTrue(restarted.seed_is_complete("normal", 900000,
                                                       online_path, offline_path))

    def test_result_writer_is_no_overwrite_and_hashes_exact_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.json"
            digest = write_exclusive(path, b"immutable\n")
            self.assertEqual(digest, __import__("hashlib").sha256(path.read_bytes()).hexdigest())
            self.assertEqual(write_exclusive(path, b"immutable\n"), digest)
            with self.assertRaises(FileExistsError):
                write_exclusive(path, b"replacement\n")

    def test_statistics_helpers_match_independent_binomial_tail(self):
        import sys
        sys.path.insert(0, str(BASE / "code"))
        import e2_statistics
        for k in (1, 99, 100, 189, 190, 199, 200):
            self.assertLess(abs(e2_statistics.cp_lower(k, 200)
                                - e2_statistics.cp_lower_binomial_tail(k, 200)), 2e-10)
        for k in (0, 12, 13, 100, 199, 200):
            self.assertLess(abs(e2_statistics.cp_upper(k, 200)
                                - e2_statistics.cp_upper_binomial_tail(k, 200)), 2e-10)
        gate = e2_statistics.evaluate_e2_count_gate(190, 100, 12)
        self.assertEqual((gate.n, gate.normal_n), (200, 200))
        self.assertTrue(gate.coverage_pass and gate.attack_nonzero_pass and gate.normal_nonzero_pass)
        self.assertFalse(e2_statistics.evaluate_e2_count_gate(189, 99, 13).normal_nonzero_pass)

    def test_formal_mode_without_auth_is_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "must_not_exist"
            with self.assertRaises(AuthorizationError):
                authorize("formal_e2", self.config, None)
            self.assertFalse(out.exists())
            template_path = Path(__file__).resolve().parents[1] / "authorization_template.json"
            template = json.loads(template_path.read_text(encoding="utf-8"))
            self.assertIs(template["authorized"], False)
            with self.assertRaises(AuthorizationError):
                authorize("formal_e2", self.config, template_path)

    def test_unbound_authorization_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            authorization = Path(directory) / "unauthorized.json"
            authorization.write_text(json.dumps({
                "scope": "E2", "authorized": False, "owner": "test",
                "authorization_id": "test-only", "bindings": {},
            }), encoding="utf-8")
            with self.assertRaises(AuthorizationError):
                authorize("formal_e2", self.config, authorization)

    def test_wrong_code_or_seed_binding_invalidates_authorization(self):
        with tempfile.TemporaryDirectory() as directory:
            authorization = Path(directory) / "mismatched.json"
            authorization.write_text(json.dumps({
                "scope": "E2", "authorized": True, "owner": "test-owner",
                "authorization_id": "test-only",
                "bindings": {"final_code_sha256": "0" * 64},
            }), encoding="utf-8")
            with self.assertRaises(AuthorizationError):
                authorize("formal_e2", self.config, authorization)

    def test_forged_formal_receipt_is_rejected(self):
        forged = RunAuthorization("formal_e2", "fake", "fake", ())
        with self.assertRaises(AuthorizationError):
            require_formal_e2(forged, self.config)
        from unittest.mock import Mock
        original = self.builder._generate_data
        self.builder._generate_data = Mock(side_effect=AssertionError("must not generate"))
        try:
            with self.assertRaises(AuthorizationError):
                self.builder.prepare_formal_attack_seed(self.config.attack_seeds[0], forged)
            self.builder._generate_data.assert_not_called()
        finally:
            self.builder._generate_data = original

    def test_authorization_bindings_cover_required_frozen_assets(self):
        from ..authorization_guard import authorization_bindings
        bindings = authorization_bindings(self.config)
        self.assertEqual(set(bindings), {"final_code_sha256", "protocol_sha256",
                                         "calibration_thresholds_sha256",
                                         "seed_list_sha256", "experiment_config_sha256"})
        self.assertEqual(bindings["protocol_sha256"], self.config.protocol_sha256)
        self.assertEqual(bindings["calibration_thresholds_sha256"], self.config.thresholds_sha256)

    def test_frozen_config_is_deeply_immutable(self):
        with self.assertRaises(TypeError):
            self.config.thresholds[self.config.methods[0]] = 0.0
        with self.assertRaises(TypeError):
            self.config.protocol["U_common"] = 999.0
        with self.assertRaises(TypeError):
            self.config.protocol["nominal_prior"]["normal"] = 0.0

    def test_owner_bound_authorization_receipt_is_verified_without_running(self):
        from ..authorization_guard import authorization_bindings
        with tempfile.TemporaryDirectory() as directory:
            auth_path = Path(directory) / "owner_authorization.json"
            document = {"scope": "E2", "authorized": True,
                        "owner": "test-owner", "authorization_id": "test-id",
                        "bindings": authorization_bindings(self.config)}
            auth_path.write_text(json.dumps(document), encoding="utf-8")
            receipt = authorize("formal_e2", self.config, auth_path)
            require_formal_e2(receipt, self.config)
            self.assertEqual(receipt.authorization_file_sha256,
                             __import__("hashlib").sha256(auth_path.read_bytes()).hexdigest())

    def test_official_seed_cannot_enter_fixture_generation(self):
        from unittest.mock import Mock
        original = self.builder._generate_data
        self.builder._generate_data = Mock(side_effect=AssertionError("must not generate"))
        try:
            with self.assertRaises(ValueError):
                self.builder.build_fixture_pair(self.config.normal_seeds[0])
            self.builder._generate_data.assert_not_called()
        finally:
            self.builder._generate_data = original

    def test_cli_defaults_to_dry_run_and_can_print_bindings_read_only(self):
        from ..cli import execution_mode
        args = build_parser().parse_args([])
        self.assertEqual(execution_mode(args), "dry_run")
        self.assertIsNone(args.authorization)
        args = build_parser().parse_args(["--show-authorization-bindings"])
        self.assertTrue(args.show_authorization_bindings)
        self.assertEqual(execution_mode(args), "dry_run")
        self.assertFalse(args.formal_e2)


def run_tests() -> dict:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(RunnerAcceptanceTests)
    result = unittest.TestResult()
    suite.run(result)
    if not result.wasSuccessful():
        details = "\n".join([str(err[1]) for err in result.errors + result.failures])
        raise AssertionError(details)
    return {"result": "PASS_RUNNER_DETERMINISTIC_TESTS_ONLY",
            "tests_passed": result.testsRun,
            "official_seed_trajectories_generated": 0,
            "E2_executed": False, "E3_executed": False}


if __name__ == "__main__":
    print(json.dumps(run_tests(), ensure_ascii=False, indent=2))
