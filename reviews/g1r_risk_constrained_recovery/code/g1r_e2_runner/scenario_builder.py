from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
import sys
from typing import Any

import numpy as np

from .authorization_guard import RunAuthorization, require_formal_e2
from .config_loader import FrozenConfig, read_json
from .online_proposal import OnlineInput, build_online_input


@dataclass(frozen=True)
class OfflineTruth:
    scenario: str
    seed: int
    main_case: bool
    event: tuple[int, int] | None
    age: int | None
    replay_source_time: int | None
    actual_replay_age: int | None
    cache_replacement_time: int | None
    first_pollution_state: int | None
    first_receiver_pollution_state: int | None
    true_impact: tuple[float, float] | None
    healthy_target_estimate: tuple[float, float] | None
    attacked_target_estimate: tuple[float, float] | None
    simulation_status: str
    statistical_cluster: str


@dataclass(frozen=True)
class ScenarioCase:
    online_input: OnlineInput
    offline_truth: OfflineTruth


@dataclass(frozen=True)
class FixturePair:
    normal: ScenarioCase
    replay: ScenarioCase
    timing_checks: dict


@dataclass(frozen=True)
class FixtureGrid:
    normal: ScenarioCase
    replays: tuple[ScenarioCase, ...]
    timing_checks: tuple[dict, ...]


@dataclass(frozen=True)
class AttackSeedContext:
    seed: int
    model: Any
    x: np.ndarray
    y: np.ndarray
    seeds: np.ndarray
    schedule: np.ndarray
    healthy_run: Any


class ScenarioBuilder:
    """Uses the frozen model helpers and shared Yang simulator unchanged."""

    def __init__(self, config: FrozenConfig, public_model):
        self.config = config
        self.public_model = public_model
        sim_path = str(config.root / "simulation")
        old_path = str(config.root / "reviews/g1_retroactive_recovery/code")
        for path in (sim_path, old_path):
            if path not in sys.path:
                sys.path.insert(0, path)
        from engine import simulate
        from model import generate_data
        from minimal_recovery_screen import build_model, common_schedule

        self._simulate = simulate
        self._generate_data = generate_data
        self._build_model = build_model
        self._common_schedule = common_schedule
        self._declared_model = read_json(config.model_config_path)["model"]

    def _verify_frozen_model(self, model):
        declared = self._declared_model
        checks = {
            "N": int(model.cfg["N"]), "n": int(model.cfg["n"]), "T": int(model.cfg["T"]),
            "A": model.A, "Q": model.Q, "P0": model.P0,
            "edges_sender_receiver": model.edges,
            "epsilon": float(model.cfg["epsilon"]),
            "send_delta_squared": float(model.cfg["send_delta_squared"]),
            "max_interval": int(model.cfg["max_interval"]),
        }
        for key in ("N", "n", "T", "epsilon", "send_delta_squared", "max_interval"):
            if checks[key] != declared[key]:
                raise ValueError(f"built model differs from frozen Yang config: {key}")
        for key in ("A", "Q", "P0", "edges_sender_receiver"):
            if not np.array_equal(np.asarray(checks[key]), np.asarray(declared[key])):
                raise ValueError(f"built model differs from frozen Yang config: {key}")
        if "H_matrices" in declared:
            expected_h = np.asarray(declared["H_matrices"], dtype=float)
        else:
            expected_h = np.asarray([scale * np.eye(model.cfg["n"])
                                     for scale in declared["H_scales"]])
        if not np.array_equal(model.H, expected_h):
            raise ValueError("built model differs from frozen Yang config: H")
        if "R_matrices" in declared:
            expected_r = np.asarray(declared["R_matrices"], dtype=float)
        else:
            expected_r = np.asarray([variance * np.eye(model.cfg["n"])
                                     for variance in declared["R_variances"]])
        if not np.array_equal(model.R, expected_r):
            raise ValueError("built model differs from frozen Yang config: R")

    def _model_and_data(self, seed: int, authorization: RunAuthorization | None = None,
                        fixture: bool = False):
        if fixture:
            if int(seed) != 0:
                raise PermissionError("only fixture seed 0 is allowed in dry-run generation")
        else:
            require_formal_e2(authorization, self.config)
            if int(seed) not in set(self.config.attack_seeds) | set(self.config.normal_seeds):
                raise PermissionError("study Seed is outside the frozen E2 seed lists")
        model = self._build_model()
        self._verify_frozen_model(model)
        data_seed = np.asarray([int(seed)], dtype=np.int64)
        x, y = self._generate_data(model, data_seed)
        if (x.shape != (1, model.cfg["T"] + 1, model.cfg["n"])
                or y.shape != (1, model.cfg["T"], model.cfg["N"], model.cfg["n"])
                or not np.all(np.isfinite(x)) or not np.all(np.isfinite(y))):
            raise ValueError("data generator produced invalid/nonfinite arrays")
        schedule = self._common_schedule(model, 1)
        ticks = np.arange(model.cfg["T"])
        expected = np.zeros_like(schedule)
        for node in range(model.cfg["N"]):
            expected[:, :, node] = (ticks % 8) == node
        expected[:, 0, :] = True
        if not np.array_equal(schedule, expected):
            raise AssertionError("scenario builder schedule differs from frozen external gap-8 plan")
        return model, x, y, data_seed, schedule

    def _innovation(self, model, run, y) -> np.ndarray:
        receiver = int(self.config.protocol["receiver"])
        times = np.asarray(self.config.protocol["innovation_times"], dtype=int)
        estimates = run.estimates[0, times, receiver]
        measurements = y[0, times, receiver]
        value = (measurements - np.einsum("ab,tb->ta", model.H[receiver], estimates)).reshape(-1)
        if value.shape != (12,) or not np.all(np.isfinite(value)):
            raise ValueError("generated innovation contains nonfinite values")
        return value

    @staticmethod
    def _first_different_state(reference, candidate, receiver: int | None = None,
                               start: int = 0, tolerance: float = 1e-12):
        difference = np.linalg.norm(candidate.estimates[0] - reference.estimates[0], axis=-1)
        if receiver is not None:
            indices = np.flatnonzero(difference[start:, receiver] > tolerance)
            return None if not len(indices) else int(start + indices[0])
        indices = np.argwhere(difference[start:] > tolerance)
        return None if not len(indices) else int(start + indices[:, 0].min())

    @staticmethod
    def _replacement_time(schedule, sender: int, r: int) -> int:
        times = np.flatnonzero(schedule[0, r + 1:, sender])
        if not len(times):
            raise ValueError("no later legitimate send can replace the replayed cache")
        return int(r + 1 + times[0])

    @contextmanager
    def _replay_attack(self, model, event: tuple[int, int], age: int):
        edge_id, r = map(int, event)
        if not (0 <= edge_id < len(model.edges)):
            raise ValueError(f"edge index outside frozen topology: {edge_id}")
        if age not in self.config.ages or age % 8:
            raise ValueError(f"replay age is outside frozen gap-8 design: {age}")
        sender, receiver = map(int, model.edges[edge_id])
        old = deepcopy(model.cfg["attack"])
        model.cfg["attack"].update(
            sender=sender, receiver=receiver, start=r, end_inclusive=r,
            replay_packet_lag=age // 8)
        try:
            yield sender, receiver, r
        finally:
            model.cfg["attack"].clear()
            model.cfg["attack"].update(old)

    def build_fixture_pair(self, seed: int = 0) -> FixturePair:
        """Build the frozen main case only, for fast single-case tests."""
        if int(seed) != 0:
            raise ValueError("dry-run trajectory generation is restricted to fixture seed 0")
        context = self._prepare_seed(0, fixture=True)
        normal = self._normal_fixture_case(context)
        replay, _, checks = self._build_replay(context, self.config.main_event, 64, fixture=True)
        if (checks["actual_age"] != 64 or not checks["single_replacement"]
                or replay.offline_truth.true_impact is None
                or np.linalg.norm(replay.offline_truth.true_impact) <= 0):
            raise AssertionError("frozen main fixture failed its replay/pollution check")
        return FixturePair(normal, replay, checks)

    def build_fixture_grid(self, seed: int = 0) -> FixtureGrid:
        """Build the 8x3 event-age grid on one fixed non-study fixture trajectory."""
        if int(seed) != 0:
            raise ValueError("dry-run trajectory generation is restricted to fixture seed 0")
        context = self._prepare_seed(0, fixture=True)
        normal_case = self._normal_fixture_case(context)
        replay_cases, timing_checks = [], []
        for event in self.config.events:
            for age in self.config.ages:
                case, _, checks = self._build_replay(context, event, age, fixture=True)
                if checks["source_time"] != event[1] - age or checks["actual_age"] != age:
                    raise AssertionError("Replay source/age mismatch")
                if not (checks["source_and_replay_are_sent"] and checks["single_replacement"]):
                    raise AssertionError("fixture must Replay exactly one captured legitimate packet")
                replay_cases.append(case)
                timing_checks.append(checks)
        if len(replay_cases) != 24:
            raise AssertionError("fixture grid must contain all 8 events x 3 ages")
        main = next(case for case in replay_cases
                    if case.offline_truth.event == self.config.main_event
                    and case.offline_truth.age == 64)
        if main.offline_truth.true_impact is None or np.linalg.norm(main.offline_truth.true_impact) <= 0:
            raise AssertionError("fixed main fixture failed to create target-state pollution")
        return FixtureGrid(normal_case, tuple(replay_cases), tuple(timing_checks))

    def _normal_fixture_case(self, context: AttackSeedContext) -> ScenarioCase:
        model, y, healthy = context.model, context.y, context.healthy_run
        receiver = int(self.config.protocol["receiver"])
        target = int(self.config.protocol["target"])
        online = build_online_input(
            self._innovation(model, healthy, y), self.public_model,
            self.config.thresholds[self.config.methods[0]], self.config.methods[0])
        truth = OfflineTruth(
            "normal", 0, True, None, None, None, None, None, None, None, None,
            tuple(map(float, healthy.estimates[0, target, receiver])), None,
            "PASS", "fixture:0")
        return ScenarioCase(online, truth)

    def build_formal_normal(self, seed: int, authorization: RunAuthorization) -> ScenarioCase:
        require_formal_e2(authorization, self.config)
        if int(seed) not in self.config.normal_seeds:
            raise ValueError("normal seed is not in the frozen E2 list")
        context = self._prepare_seed(int(seed), authorization=authorization)
        model, y, run = context.model, context.y, context.healthy_run
        receiver, target = int(self.config.protocol["receiver"]), int(self.config.protocol["target"])
        online = build_online_input(self._innovation(model, run, y), self.public_model,
                                    self.config.thresholds[self.config.methods[0]],
                                    self.config.methods[0])
        truth = OfflineTruth("normal", int(seed), True, None, None, None, None,
                             None, None, None, None,
                             tuple(map(float, run.estimates[0, target, receiver])), None,
                             "PASS", f"normal:{int(seed)}")
        return ScenarioCase(online, truth)

    def build_formal_replay(self, seed: int, event: tuple[int, int], age: int,
                            authorization: RunAuthorization,
                            context: AttackSeedContext) -> ScenarioCase:
        require_formal_e2(authorization, self.config)
        if int(seed) not in self.config.attack_seeds:
            raise ValueError("attack seed is not in the frozen E2 list")
        if tuple(map(int, event)) not in self.config.events or int(age) not in self.config.ages:
            raise ValueError("event or age is outside the frozen E2 design")
        if context.seed != int(seed):
            raise ValueError("attack seed context does not match requested seed")
        case, _, _ = self._build_replay(context, event, age, fixture=False)
        return case

    def prepare_formal_attack_seed(self, seed: int,
                                   authorization: RunAuthorization) -> AttackSeedContext:
        require_formal_e2(authorization, self.config)
        if int(seed) not in self.config.attack_seeds:
            raise ValueError("attack seed is not in the frozen E2 list")
        return self._prepare_seed(int(seed), authorization=authorization)

    def _prepare_seed(self, seed: int, authorization: RunAuthorization | None = None,
                      fixture: bool = False) -> AttackSeedContext:
        model, x, y, seeds, schedule = self._model_and_data(
            int(seed), authorization=authorization, fixture=fixture)
        healthy = self._simulate(model, x, y, seeds, "yang", scenario="clean",
                                 schedule=schedule, collect=False)
        self._validate_simulator_output(healthy, model, schedule)
        return AttackSeedContext(int(seed), model, x, y, seeds, schedule, healthy)

    @staticmethod
    def _validate_simulator_output(run, model, schedule):
        # Frozen engine.Run has no status field. If an external wrapper adds
        # one it must be PASS, and arrays must always be complete and finite.
        if getattr(run, "simulation_status", "PASS") != "PASS":
            raise ValueError("Yang simulator reported non-PASS status")
        if (run.estimates.shape != (1, model.cfg["T"] + 1, model.cfg["N"], model.cfg["n"])
                or not np.all(np.isfinite(run.estimates))):
            raise ValueError("Yang simulator returned invalid states")
        if not np.array_equal(run.sends, schedule):
            raise ValueError("Yang simulator changed frozen send schedule")

    def _build_replay(self, context: AttackSeedContext, event: tuple[int, int],
                      age: int, fixture: bool):
        model, x, y, seeds, schedule = (context.model, context.x, context.y,
                                         context.seeds, context.schedule)
        event = tuple(map(int, event))
        age = int(age)
        with self._replay_attack(model, event, age) as (sender, receiver, r):
            attacked = self._simulate(model, x, y, seeds, "yang", scenario="replay_packet",
                                      schedule=schedule, collect=False)
        self._validate_simulator_output(attacked, model, schedule)
        source = int(attacked.replay_source[0, r])
        if not (schedule[0, r, sender] and source >= 0 and schedule[0, source, sender]):
            raise AssertionError("formal replay did not use a captured legitimate send")
        actual_age = r - source
        if actual_age != age:
            raise AssertionError(f"frozen replay age mismatch: expected {age}, observed {actual_age}")
        q = self._replacement_time(schedule, sender, r)
        target = int(self.config.protocol["target"])
        healthy = context.healthy_run
        target_delta = attacked.estimates[0, target, receiver] - healthy.estimates[0, target, receiver]
        first_network = self._first_different_state(healthy, attacked, start=r + 1)
        first_receiver = self._first_different_state(healthy, attacked, receiver, start=r + 1)
        z = self._innovation(model, attacked, y)
        main = tuple(map(int, event)) == self.config.main_event and int(age) == 64
        online = build_online_input(z, self.public_model,
                                    self.config.thresholds[self.config.methods[0]],
                                    self.config.methods[0])
        truth = OfflineTruth(
            "replay", int(context.seed), main, event, age, source,
            actual_age, q, first_network, first_receiver,
            tuple(map(float, target_delta)),
            tuple(map(float, healthy.estimates[0, target, receiver])),
            tuple(map(float, attacked.estimates[0, target, receiver])),
            "PASS", f"attack:{int(context.seed)}")
        checks = {
            "edge": event[0], "sender": sender, "receiver": receiver,
            "replay_time": r, "source_time": source, "actual_age": actual_age,
            "cache_replacement_time": q, "first_pollution_state": first_network,
            "first_receiver_pollution_state": first_receiver,
            "innovation_times": list(self.config.protocol["innovation_times"]),
            "decision_time": int(self.config.protocol["decision"]),
            "target_time": target, "source_and_replay_are_sent": True,
            "single_replacement": bool(attacked.injected[0, r]
                                      and np.count_nonzero(attacked.injected[0]) == 1),
            "yang_shared_engine": True,
        }
        if not checks["single_replacement"]:
            raise AssertionError("Replay fixture must change exactly one sent payload")
        return ScenarioCase(online, truth), attacked, checks
