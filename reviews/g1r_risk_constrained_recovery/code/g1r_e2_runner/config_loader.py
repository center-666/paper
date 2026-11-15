from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "reviews/g1r_risk_constrained_recovery"
RUNNER_DIR = Path(__file__).resolve().parent
AUDIT_RUN = BASE / "results/g1r_e2_status_resolution_20261115_r01"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True, allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


@dataclass(frozen=True)
class FrozenConfig:
    root: Path
    base: Path
    protocol: dict[str, Any]
    run_template: dict[str, Any]
    schema: dict[str, Any]
    thresholds: dict[str, float]
    normal_seeds: tuple[int, ...]
    attack_seeds: tuple[int, ...]
    events: tuple[tuple[int, int], ...]
    ages: tuple[int, ...]
    methods: tuple[str, ...]
    batch_size: int
    attack_seed_scan_sha256: str
    protocol_sha256: str
    thresholds_sha256: str
    calibration_manifest_sha256: str
    matrix_sha256: str
    schema_sha256: str
    run_template_sha256: str
    runner_config_sha256: str

    @property
    def matrix_path(self) -> Path:
        return self.root / self.protocol["joint_statistics_npz"]

    @property
    def model_config_path(self) -> Path:
        return self.root / self.protocol["model_config"]

    @property
    def calibration_path(self) -> Path:
        return self.base / "results/g1r_task5_calibration_20261115_r01/frozen_thresholds.json"

    @property
    def main_event(self) -> tuple[int, int]:
        return tuple(map(int, self.protocol["main_event"]))

    @property
    def decision_time(self) -> int:
        return int(self.protocol["decision"])

    @property
    def target_time(self) -> int:
        return int(self.protocol["target"])

    def contract_dict(self) -> dict[str, Any]:
        return {
            "protocol_sha256": self.protocol_sha256,
            "thresholds_sha256": self.thresholds_sha256,
            "calibration_manifest_sha256": self.calibration_manifest_sha256,
            "matrix_sha256": self.matrix_sha256,
            "schema_sha256": self.schema_sha256,
            "run_template_sha256": self.run_template_sha256,
            "seed_scan_sha256": self.attack_seed_scan_sha256,
            "normal_seeds": list(self.normal_seeds),
            "attack_seeds": list(self.attack_seeds),
            "events": [list(event) for event in self.events],
            "ages": list(self.ages),
            "methods": list(self.methods),
            "thresholds": self.thresholds,
            "U_common": float(self.protocol["U_common"]),
            "batch_size": self.batch_size,
        }


def _verify_package() -> dict[str, Any]:
    manifest = read_json(AUDIT_RUN / "package_manifest.json")
    if manifest.get("run_id") != AUDIT_RUN.name:
        raise ValueError("B.1 audit package run ID mismatch")
    for name, expected in manifest["files_sha256"].items():
        path = AUDIT_RUN / name
        if not path.is_file() or sha256_file(path) != expected:
            raise ValueError(f"B.1 audit package file mismatch: {name}")
    return read_json(AUDIT_RUN / "environment_freeze.json")


def load_frozen_config(root: Path = ROOT) -> FrozenConfig:
    """Load and hash-check frozen inputs without loading or generating samples."""
    base = root / "reviews/g1r_risk_constrained_recovery"
    audit_run = base / "results/g1r_e2_status_resolution_20261115_r01"
    package = read_json(audit_run / "package_manifest.json")
    if package.get("run_id") != audit_run.name:
        raise ValueError("B.1 audit package run ID mismatch")
    for name, expected in package["files_sha256"].items():
        path = audit_run / name
        if not path.is_file() or sha256_file(path) != expected:
            raise ValueError(f"B.1 audit package file mismatch: {name}")

    environment = read_json(audit_run / "environment_freeze.json")
    for relative, expected in environment["source_sha256"].items():
        path = root / relative
        if not path.is_file() or sha256_file(path) != expected:
            raise ValueError(f"frozen source SHA mismatch: {relative}")
    if not environment.get("all_runtime_and_core_hashes_match"):
        raise ValueError("B.1 runtime/core verification is not clean")
    seed_scan = read_json(audit_run / "e2_seed_scan.json")
    if (seed_scan.get("collision_count") != 0
            or len(seed_scan.get("per_seed", [])) != 400
            or any(row.get("status") != "NO_COLLISION_IN_SCANNED_SCOPE"
                   for row in seed_scan["per_seed"])):
        raise ValueError("E2 reserved seed collision scan is incomplete")

    protocol_path = base / "protocol_v2.json"
    protocol = read_json(protocol_path)
    template = read_json(audit_run / "e2_run_manifest.template.json")
    schema = read_json(audit_run / "e2_log_schema.json")
    threshold_path = base / "results/g1r_task5_calibration_20261115_r01/frozen_thresholds.json"
    threshold_record = read_json(threshold_path)
    calibration_manifest = base / "results/g1r_task5_calibration_20261115_r01/calibration_manifest.json"
    calibration = read_json(calibration_manifest)
    matrix_path = root / protocol["joint_statistics_npz"]

    for relative, expected in protocol.get("input_sha256", {}).items():
        path = root / relative
        if not path.is_file() or sha256_file(path) != expected:
            raise ValueError(f"protocol-frozen input SHA mismatch: {relative}")

    protocol_sha = sha256_file(protocol_path)
    thresholds_sha = sha256_file(threshold_path)
    calibration_sha = sha256_file(calibration_manifest)
    matrix_sha = sha256_file(matrix_path)
    schema_sha = sha256_file(audit_run / "e2_log_schema.json")
    run_template_sha = sha256_file(audit_run / "e2_run_manifest.template.json")
    if protocol_sha != template["protocol_v2_sha256"]:
        raise ValueError("protocol hash differs from the B.1 frozen template")
    if thresholds_sha != template["calibration_thresholds_sha256"]:
        raise ValueError("threshold hash differs from the B.1 frozen template")
    if calibration_sha != environment["calibration_manifest_sha256"]:
        raise ValueError("Task 5 calibration manifest changed")
    if matrix_sha != calibration["source_sha256"][protocol["joint_statistics_npz"]]:
        raise ValueError("frozen joint matrix hash changed")

    normal = tuple(range(int(template["seeds"]["normal"]["start"]),
                         int(template["seeds"]["normal"]["start"])
                         + int(template["seeds"]["normal"]["count"])))
    attack = tuple(range(int(template["seeds"]["attack"]["start"]),
                         int(template["seeds"]["attack"]["start"])
                         + int(template["seeds"]["attack"]["count"])))
    if len(set(normal) & set(attack)):
        raise ValueError("formal normal and attack seed groups overlap")
    events = tuple(tuple(map(int, event)) for event in template["model_and_attack"]["candidate_events"])
    ages = (int(template["model_and_attack"]["pressure_ages"][0]),
            int(template["model_and_attack"]["nominal_age"]),
            int(template["model_and_attack"]["pressure_ages"][1]))
    methods = tuple(template["methods"])
    if methods != tuple(protocol["methods"]):
        raise ValueError("method list mismatch between protocol and E2 template")
    thresholds = {str(k): float(v) for k, v in threshold_record["thresholds"].items()}
    if thresholds != {str(k): float(v) for k, v in template["thresholds"].items()}:
        raise ValueError("threshold values differ between calibration and E2 template")
    if float(protocol["U_common"]) != float(template["common_constraints"]["U"]):
        raise ValueError("common action cap differs from frozen template")
    protocol_events = tuple(tuple(map(int, event)) for event in protocol["events_edge_r"])
    if protocol_events != events:
        raise ValueError("candidate event dictionary differs from frozen protocol")
    if template.get("state") != "TEMPLATE_NOT_EXECUTED" or template.get("execution_authorized") is not False:
        raise ValueError("E2 manifest template must remain explicitly unauthorized")
    if int(template["seeds"]["normal"]["count"]) != 200 or int(template["seeds"]["attack"]["count"]) != 200:
        raise ValueError("E2 seed counts differ from the frozen 200+200 design")
    if len(events) != 8 or len(ages) != 3 or len(events) * len(ages) != 24:
        raise ValueError("E2 event-age design must contain exactly 24 attack cases per seed")
    template_events = tuple(tuple(map(int, event))
                            for event in template["model_and_attack"]["candidate_events"])
    if template_events != events or tuple(map(int, protocol["main_event"])) not in events:
        raise ValueError("main Replay event differs from the frozen protocol")
    if int(template["model_and_attack"]["nominal_age"]) != int(protocol["nominal_replay_age"]):
        raise ValueError("nominal Replay age differs from the frozen protocol")
    common = template["common_constraints"]
    expected_common = {
        "U": protocol["U_common"], "alpha": protocol["alpha"],
        "normal_R_over_J0": protocol["primary_R_over_J0"],
        "beta": protocol["beta"], "new_communication_bytes": 0,
    }
    if any(float(common[key]) != float(value) for key, value in expected_common.items()):
        raise ValueError("common risk/action constraints differ from the frozen protocol")
    protocol_gate = protocol["e2_gate"]
    template_gate = template["gate"]
    gate_pairs = (("primary_coverage_count_min", "coverage_count_min"),
                  ("coverage_cp_one_sided_95_lower_min", "coverage_cp_one_sided_95_lower_min"),
                  ("primary_nonzero_count_min", "set_attack_nonzero_count_min"),
                  ("nonzero_cp_one_sided_95_lower_min", "nonzero_cp_lower_min"),
                  ("normal_nonzero_cp_one_sided_95_upper_max", "normal_cp_upper_max"))
    for protocol_key, template_key in gate_pairs:
        if float(protocol_gate[protocol_key]) != float(template_gate[template_key]):
            raise ValueError(f"E2 gate threshold mismatch: {protocol_key}")
    if len(schema.get("fields", {})) != 20:
        raise ValueError("E2 row schema does not contain the frozen 20 fields")
    if template["model_and_attack"]["receiver"] != protocol["receiver"]:
        raise ValueError("receiver differs from frozen protocol")
    if (template["model_and_attack"]["decision_time"] != protocol["decision"]
            or template["model_and_attack"]["target_state"] != protocol["target"]
            or template["model_and_attack"]["innovation_times"] != protocol["innovation_times"]):
        raise ValueError("decision/target/innovation window differs from frozen protocol")
    if template["case_counts"]["attack_event_age_cases_per_seed"] != 24:
        raise ValueError("attack per-seed case count differs from the frozen design")
    if (template["case_counts"]["normal_main_seed_rows_per_method"] != 200
            or template["case_counts"]["primary_main_case_rows_per_method"] != 200
            or template["case_counts"]["attack_proposal_rows_all_methods"] != 14400
            or template["case_counts"]["normal_proposal_rows_all_methods"] != 600):
        raise ValueError("E2 row counts differ from the frozen protocol")
    if int(protocol["gap"]) != 8:
        raise ValueError("runner supports only the frozen gap-8 schedule")

    config_without_digest = {
        "protocol_sha256": protocol_sha,
        "thresholds_sha256": thresholds_sha,
        "calibration_manifest_sha256": calibration_sha,
        "matrix_sha256": matrix_sha,
        "schema_sha256": schema_sha,
        "run_template_sha256": run_template_sha,
        "seed_scan_sha256": sha256_file(audit_run / "e2_seed_scan.json"),
        "normal_seeds": list(normal), "attack_seeds": list(attack),
        "events": [list(event) for event in events], "ages": list(ages),
        "methods": list(methods), "thresholds": thresholds,
        "U_common": float(protocol["U_common"]), "batch_size": 20,
    }
    return FrozenConfig(
        root=root, base=base, protocol=protocol, run_template=template, schema=schema,
        thresholds=thresholds, normal_seeds=normal, attack_seeds=attack,
        events=events, ages=ages, methods=methods, batch_size=20,
        attack_seed_scan_sha256=config_without_digest["seed_scan_sha256"],
        protocol_sha256=protocol_sha, thresholds_sha256=thresholds_sha,
        calibration_manifest_sha256=calibration_sha, matrix_sha256=matrix_sha,
        schema_sha256=schema_sha, run_template_sha256=run_template_sha,
        runner_config_sha256=canonical_sha256(config_without_digest),
    )


def freeze_public_model(value: Any) -> Any:
    """Recursively make public estimator inputs immutable."""
    from types import MappingProxyType

    if isinstance(value, dict):
        return MappingProxyType({key: freeze_public_model(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(freeze_public_model(item) for item in value)
    if isinstance(value, np.ndarray):
        result = np.array(value, copy=True)
        result.setflags(write=False)
        return result
    return value


def load_public_model(config: FrozenConfig):
    import sys

    code_path = str(config.base / "code")
    if code_path not in sys.path:
        sys.path.insert(0, code_path)
    import v2_estimators

    model = v2_estimators.public_model_from_npz(config.matrix_path, config.protocol)
    return freeze_public_model(model)
