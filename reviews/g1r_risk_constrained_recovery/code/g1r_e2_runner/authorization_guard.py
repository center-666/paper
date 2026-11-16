from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any

from .config_loader import FrozenConfig, canonical_sha256, sha256_file
from . import RUNNER_VERSION
from .environment_guard import verify_environment


class AuthorizationError(RuntimeError):
    pass


_RECEIPT_SEAL = object()


@dataclass(frozen=True)
class RunAuthorization:
    mode: str
    authorization_id: str | None
    owner: str | None
    bindings: tuple[tuple[str, str], ...]
    authorization_file_sha256: str | None = None
    _seal: object = field(default=None, repr=False, compare=False)


def runner_source_sha256(config: FrozenConfig) -> str:
    files = sorted(path for path in Path(__file__).resolve().parent.rglob("*.py")
                   if "__pycache__" not in path.parts)
    protected = [config.base / "code/e2_status_adapter.py",
                 config.base / "code/v2_estimators.py",
                 config.base / "code/e2_statistics.py",
                 config.base / "model_builder_inputs_addendum.json",
                 config.base / "results/.gitattributes",
                 config.base / "results/g1r_e2_status_resolution_20261115_r01/e2_log_schema.json",
                 config.base / "results/g1r_e2_status_resolution_20261115_r01/e2_run_manifest.template.json",
                 config.base / "results/g1r_pre_e2_readonly_audit_20261115_r04/e2_seed_scan.json",
                 config.base / "results/g1r_task5_debug_20261115_r04/summary.json",
                 config.root / "reviews/g1_retroactive_recovery/code/minimal_recovery_screen.py",
                 config.model_config_path,
                 config.root / "simulation/config.json",
                 config.root / "simulation/reference_exploration_plan.json",
                 config.root / "simulation/engine.py",
                 config.root / "simulation/model.py",
                 Path(__file__).resolve().parent / "authorization_template.json"]
    entries = []
    for path in sorted(set(files + protected), key=lambda p: p.as_posix()):
        entries.append((path.relative_to(config.root).as_posix(), sha256_file(path)))
    return canonical_sha256(entries)


def authorization_bindings(config: FrozenConfig) -> dict[str, str]:
    verify_environment(config)
    seed_manifest = {
        "normal": list(config.normal_seeds),
        "attack": list(config.attack_seeds),
    }
    result = {
        "final_code_sha256": runner_source_sha256(config),
        "protocol_sha256": config.protocol_sha256,
        "calibration_thresholds_sha256": config.thresholds_sha256,
        "seed_list_sha256": canonical_sha256(seed_manifest),
        "experiment_config_sha256": config.runner_config_sha256,
    }
    return result




def authorize(mode: str, config: FrozenConfig, authorization_file: Path | None = None) -> RunAuthorization:
    verify_environment(config)
    if mode == "dry_run":
        return RunAuthorization("dry_run", None, None, (), None, _RECEIPT_SEAL)
    if mode != "formal_e2":
        raise AuthorizationError(f"unsupported execution mode: {mode}")
    if authorization_file is None or not authorization_file.is_file():
        raise AuthorizationError("formal E2 blocked: owner authorization file is required")
    try:
        record = json.loads(authorization_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuthorizationError(f"formal E2 blocked: invalid authorization file: {exc}") from exc
    if record.get("authorized") is not True or record.get("scope") != "E2":
        raise AuthorizationError("formal E2 blocked: authorization must explicitly approve E2")
    if not str(record.get("owner", "")).strip() or not str(record.get("authorization_id", "")).strip():
        raise AuthorizationError("formal E2 blocked: owner and authorization ID are required")
    expected = authorization_bindings(config)
    actual = record.get("bindings")
    if not isinstance(actual, dict) or actual != expected:
        raise AuthorizationError("formal E2 blocked: code/protocol/threshold/seed/config binding mismatch")
    return RunAuthorization("formal_e2", str(record["authorization_id"]),
                            str(record["owner"]), tuple(sorted(expected.items())),
                            sha256_file(authorization_file), _RECEIPT_SEAL)


def require_formal_e2(receipt: RunAuthorization, config: FrozenConfig) -> None:
    verify_environment(config)
    if (type(receipt) is not RunAuthorization or receipt._seal is not _RECEIPT_SEAL
            or receipt.mode != "formal_e2" or not receipt.authorization_id or not receipt.owner
            or not receipt.authorization_file_sha256):
        raise AuthorizationError("formal E2 blocked: invalid authorization receipt")
    if receipt.bindings != tuple(sorted(authorization_bindings(config).items())):
        raise AuthorizationError("formal E2 blocked: authorization bindings are stale")
