from __future__ import annotations

import json
import contextlib
import hashlib
import io
import platform
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import scipy

from .config_loader import FrozenConfig, read_json
from .environment_guard import verify_environment


class IntegrityError(ValueError):
    pass


def _event(row) -> tuple[int, int] | None:
    value = row.get("event")
    if value in (None, "", "null"):
        return None
    if isinstance(value, str):
        value = json.loads(value)
    return tuple(map(int, value))


def _bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if value in ("True", "true", "1", 1):
        return True
    if value in ("False", "false", "0", 0, None, ""):
        return False
    raise IntegrityError(f"invalid boolean result field: {value!r}")


def validate_batch_rows(config: FrozenConfig, group: str, seeds: tuple[int, ...],
                        rows: list[dict[str, Any]]) -> None:
    if group not in {"normal", "attack"}:
        raise IntegrityError(f"unknown scenario group {group!r}")
    if len(set(seeds)) != len(seeds):
        raise IntegrityError("duplicate seed in batch plan")
    expected_per_seed = len(config.methods) if group == "normal" else len(config.events) * len(config.ages) * len(config.methods)
    expected_rows = len(seeds) * expected_per_seed
    if len(rows) != expected_rows:
        raise IntegrityError(f"batch row count {len(rows)} != expected {expected_rows}")
    expected = set()
    for seed in seeds:
        if group == "normal":
            for method in config.methods:
                expected.add((int(seed), "normal", None, None, method))
        else:
            for event in config.events:
                for age in config.ages:
                    for method in config.methods:
                        expected.add((int(seed), "replay", event, age, method))
    observed = []
    model_cfg = read_json(config.model_config_path)["model"]
    for row in rows:
        if row.get("simulation_status") != "PASS":
            raise IntegrityError("non-PASS simulation cannot enter a completed batch")
        scenario = str(row["scenario"])
        event = _event(row)
        age = None if row.get("age") in (None, "", "null") else int(row["age"])
        key = (int(row["seed"]), scenario, event, age, str(row["method"]))
        observed.append(key)
        if key not in expected:
            raise IntegrityError(f"unexpected row key {key}")
        should_main = (group == "normal" or
                       (event == config.main_event and age == 64))
        if _bool(row["main_case"]) != should_main:
            raise IntegrityError(f"main-case label mismatch for {key}")
        norm = float(row["set_action_norm"])
        action = np.asarray(json.loads(row["final_action_json"]), dtype=float)
        proposal = np.asarray(json.loads(row["proposal_vector_json"]), dtype=float)
        proposal_norm = float(row["set_proposal_norm"])
        numbers = [norm, proposal_norm, float(row["score"]), float(row["threshold"])]
        if (action.shape != (2,) or proposal.shape != (2,)
                or not np.all(np.isfinite(action)) or not np.all(np.isfinite(proposal))
                or not np.all(np.isfinite(numbers)) or norm < 0 or proposal_norm < 0):
            raise IntegrityError(f"nonfinite or malformed proposal/action for {key}")
        if abs(float(np.linalg.norm(proposal)) - proposal_norm) > 1e-10:
            raise IntegrityError(f"pre-gate proposal norm mismatch for {key}")
        if abs(float(np.linalg.norm(action)) - norm) > 1e-10:
            raise IntegrityError(f"post-gate action norm mismatch for {key}")
        if float(row["threshold"]) != config.thresholds[str(row["method"])]:
            raise IntegrityError(f"calibration threshold mismatch for {key}")
        if norm > float(config.protocol["U_common"]) + 1e-12:
            raise IntegrityError(f"post-gate action exceeds common cap for {key}")
        executed = (str(row["gate_status"]) == "EXECUTED"
                    and str(row["proposal_status"]) == "VALID" and norm > 1e-12)
        if _bool(row["execution_success"]) != executed:
            raise IntegrityError(f"execution_success is inconsistent for {key}")
        if (str(row["proposal_status"]) != "VALID" or str(row["gate_status"]) != "EXECUTED") and norm > 1e-12:
            raise IntegrityError(f"rejected proposal has a nonzero executed action for {key}")
        if group == "attack":
            try:
                impact = np.asarray([row["true_impact_x"], row["true_impact_y"]], dtype=float)
            except (KeyError, TypeError, ValueError) as exc:
                raise IntegrityError(f"missing Replay true impact for {key}") from exc
            if not np.all(np.isfinite(impact)):
                raise IntegrityError(f"nonfinite Replay true impact for {key}")
            source = int(row["replay_source_time"])
            actual_age = int(row["actual_replay_age"])
            sender = model_cfg["edges_sender_receiver"][event[0]][0]
            gap = int(config.protocol["gap"])
            if (source != event[1] - age or actual_age != age or source < 0
                    or event[1] % gap != sender
                    or (source != 0 and source % gap != sender)):
                raise IntegrityError(f"actual Replay source/age/send mismatch for {key}")
            if int(row["cache_replacement_time"]) != event[1] + gap:
                raise IntegrityError(f"incorrect cache replacement time for {key}")
        if str(row["statistical_cluster"]) != f"{group}:{int(row['seed'])}" and group == "attack":
            raise IntegrityError(f"attack rows lost within-seed cluster label for {key}")
    if len(set(observed)) != len(observed):
        raise IntegrityError("duplicate seed/event/age/method row")
    if set(observed) != expected:
        missing = expected - set(observed)
        raise IntegrityError(f"missing planned rows: {len(missing)}")


def validate_full_run(config: FrozenConfig, normal_rows: list[dict[str, Any]],
                      attack_rows: list[dict[str, Any]]) -> None:
    validate_batch_rows(config, "normal", config.normal_seeds, normal_rows)
    validate_batch_rows(config, "attack", config.attack_seeds, attack_rows)


def source_hash_manifest(config: FrozenConfig, debug_cache: Path) -> dict[str, Any]:
    runtime_validation = verify_environment(config)
    runner_dir = Path(__file__).resolve().parent
    paths = list(runner_dir.rglob("*.py")) + [runner_dir / "authorization_template.json"] + [
        config.base / "protocol_v2.json",
        config.base / "code/e2_status_adapter.py",
        config.base / "code/e2_statistics.py",
        config.base / "code/v2_estimators.py",
        config.base / "model_builder_inputs_addendum.json",
        config.base / "results/.gitattributes",
        config.base / "results/g1r_e2_status_resolution_20261115_r01/e2_log_schema.json",
        config.base / "results/g1r_e2_status_resolution_20261115_r01/e2_run_manifest.template.json",
        config.base / "results/g1r_pre_e2_readonly_audit_20261115_r04/e2_seed_scan.json",
        config.base / "results/g1r_task5_calibration_20261115_r01/frozen_thresholds.json",
        config.base / "results/g1r_task5_calibration_20261115_r01/calibration_manifest.json",
        config.base / "results/g1r_task5_debug_20261115_r04/summary.json",
        config.matrix_path,
        config.model_config_path,
        config.root / "simulation/engine.py",
        config.root / "simulation/model.py",
        config.root / "simulation/config.json",
        config.root / "simulation/reference_exploration_plan.json",
        config.root / "reviews/g1_retroactive_recovery/code/minimal_recovery_screen.py",
        debug_cache,
    ]
    hashes = {}
    for path in sorted(set(paths), key=lambda item: item.as_posix()):
        relative = path.relative_to(config.root).as_posix()
        hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    blas = io.StringIO()
    with contextlib.redirect_stdout(blas):
        np.show_config()
    git_branch = subprocess.check_output(
        ["git", "branch", "--show-current"], cwd=config.root, text=True).strip()
    git_head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=config.root, text=True).strip()
    return {
        "run_id_scope": "dry-run verification source snapshot; no formal execution",
        "git_branch": git_branch,
        "git_head_at_snapshot": git_head,
        "python": platform.python_version(),
        "numpy": np.__version__, "scipy": scipy.__version__,
        "platform": platform.platform(),
        "blas_configuration": blas.getvalue(),
        "live_environment_validation": runtime_validation,
        "protocol_sha256": config.protocol_sha256,
        "thresholds_sha256": config.thresholds_sha256,
        "calibration_manifest_sha256": config.calibration_manifest_sha256,
        "matrix_sha256": config.matrix_sha256,
        "runner_and_frozen_source_sha256": hashes,
        "debug_cache_sha256": hashlib.sha256(debug_cache.read_bytes()).hexdigest(),
    }
